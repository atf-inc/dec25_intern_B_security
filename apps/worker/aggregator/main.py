"""
Job Aggregator Service - Coordinates Worker Outputs

This service aggregates results from Worker A (Intent) and Worker B (Sandbox Analysis)
into a single unified payload before delivering to the final report queue.

Architecture:
- Consumes from 3 Redis Streams: emails:job, emails:intent:done, emails:analysis:done
- Maintains job state in Redis Hash with TTL
- Applies deterministic completion logic based on requiresB flag
- Publishes to job:completed when all required workers finish
- Handles TTL cleanup for expired jobs

Flow:
1. Control message arrives → Initialize job state
2. Worker A done → Update state, check completion
3. Worker B done (if required) → Update state, check completion
4. Job complete → Update database, publish final result, cleanup state
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus
from packages.shared.models import EmailEvent
from packages.shared.queue import (
    get_redis_client,
    JOB_AGGREGATOR_QUEUE,
    EMAIL_INTENT_DONE_QUEUE,
    EMAIL_ANALYSIS_DONE_QUEUE,
    FINAL_REPORT_QUEUE,
)
from packages.shared.logger import setup_logging

# Configure logging
logger = setup_logging("aggregator-worker")

# Configuration
STATE_PREFIX = "job_state:"
STATE_TTL = 600  # 10 minutes in seconds
CLEANUP_INTERVAL = 60  # Run cleanup every 60 seconds


# --- State Management ---


async def save_state(redis, job_id: str, state: dict) -> None:
    """Save job state to Redis Hash with TTL."""
    key = f"{STATE_PREFIX}{job_id}"

    # Convert all values to strings for Redis Hash
    string_state = {k: str(v) for k, v in state.items()}

    await redis.hset(key, mapping=string_state)
    await redis.expire(key, STATE_TTL)

    logger.debug(f"Job {job_id}: State saved to Redis (TTL={STATE_TTL}s)")


async def load_state(redis, job_id: str) -> dict | None:
    """Load job state from Redis Hash."""
    key = f"{STATE_PREFIX}{job_id}"
    state = await redis.hgetall(key)

    if not state:
        logger.warning(f"Job {job_id}: No state found in Redis")
        return None

    logger.debug(f"Job {job_id}: State loaded from Redis")
    return state


async def delete_state(redis, job_id: str) -> None:
    """Delete job state from Redis."""
    key = f"{STATE_PREFIX}{job_id}"
    await redis.delete(key)
    logger.debug(f"Job {job_id}: State deleted from Redis")


def is_job_complete(state: dict) -> bool:
    """Deterministic completion check based on job requirements."""
    requires_b = state.get("requiresB", "false").lower() == "true"
    has_intent = state.get("intent_received", "false").lower() == "true"
    has_sandbox = state.get("sandbox_received", "false").lower() == "true"

    if requires_b:
        complete = has_intent and has_sandbox
        logger.debug(
            f"Job {state.get('job_id')}: Completion check (requiresB=true) - "
            f"intent={has_intent} sandbox={has_sandbox} → {complete}"
        )
        return complete
    else:
        complete = has_intent
        logger.debug(
            f"Job {state.get('job_id')}: Completion check (requiresB=false) - "
            f"intent={has_intent} → {complete}"
        )
        return complete


# --- Message Handlers ---


async def handle_control(redis, payload: dict) -> None:
    """Handle control stream message - initializes job state."""
    job_id = payload.get("job_id")
    if not job_id:
        logger.error("Control message missing job_id field")
        return

    requires_b = payload.get("requiresB", False)
    created_at = payload.get("created_at", datetime.now(timezone.utc).isoformat())

    logger.info(
        f"Job {job_id}: Control message received - requiresB={requires_b} created_at={created_at}"
    )

    state = {
        "job_id": job_id,
        "requiresB": str(requires_b).lower(),
        "created_at": created_at,
        "intent_received": "false",
        "sandbox_received": "false",
    }

    await save_state(redis, job_id, state)
    logger.info(f"Job {job_id}: Initialized state")


async def handle_intent_done(redis, payload: dict) -> None:
    """Handle intent DONE message - updates state and checks completion."""
    job_id = payload.get("job_id")
    if not job_id:
        logger.error("Intent DONE message missing job_id field")
        return

    logger.info(
        f"Job {job_id}: Intent DONE received - "
        f"intent={payload.get('intent')} risk_score={payload.get('risk_score')}"
    )

    state = await load_state(redis, job_id)
    if not state:
        # Control message hasn't arrived yet - buffer this result
        logger.warning(
            f"Job {job_id}: Intent DONE arrived before control message, "
            f"initializing state with defaults"
        )
        state = {
            "job_id": job_id,
            "requiresB": "false",  # Default to false if control missing
            "created_at": datetime.now(timezone.utc).isoformat(),
            "intent_received": "false",
            "sandbox_received": "false",
        }

    # Store intent results
    state["intent"] = json.dumps(payload)
    state["intent_received"] = "true"

    await save_state(redis, job_id, state)
    logger.info(f"Job {job_id}: Intent results stored in state")

    # Check if job is complete
    if is_job_complete(state):
        await finalize_job(redis, job_id, state)


async def handle_sandbox_done(redis, payload: dict) -> None:
    """Handle sandbox DONE message - updates state and checks completion."""
    job_id = payload.get("job_id")
    if not job_id:
        logger.error("Sandbox DONE message missing job_id field")
        return

    logger.info(
        f"Job {job_id}: Sandbox DONE received - "
        f"verdict={payload.get('verdict')} score={payload.get('sandbox_score')}"
    )

    state = await load_state(redis, job_id)
    if not state:
        logger.warning(
            f"Job {job_id}: Sandbox DONE arrived before control message, "
            f"initializing state with defaults"
        )
        state = {
            "job_id": job_id,
            "requiresB": "true",  # If sandbox ran, it was required
            "created_at": datetime.now(timezone.utc).isoformat(),
            "intent_received": "false",
            "sandbox_received": "false",
        }

    # Store sandbox results
    state["sandbox"] = json.dumps(payload)
    state["sandbox_received"] = "true"

    await save_state(redis, job_id, state)
    logger.info(f"Job {job_id}: Sandbox results stored in state")

    # Check if job is complete
    if is_job_complete(state):
        await finalize_job(redis, job_id, state)


async def finalize_job(redis, job_id: str, state: dict) -> None:
    """Finalize job - update database, publish final result, cleanup state."""
    logger.info(f"Job {job_id}: Starting finalization (all required workers completed)")

    try:
        # STEP 1: Parse results from state
        # Parse results from state
        intent_data = json.loads(state.get("intent", "{}"))
        sandbox_data = (
            json.loads(state.get("sandbox", "{}")) if state.get("sandbox") else None
        )

        logger.debug(
            f"Job {job_id}: Parsed results - "
            f"has_intent={bool(intent_data)} has_sandbox={bool(sandbox_data)}"
        )

        # STEP 2: Update database with COMPLETED status
        gmail_message_id = None

        @asynccontextmanager
        async def session_scope():
            async for s in get_session():
                yield s
                break

        async with session_scope() as session:
            try:
                import uuid

                email_id = uuid.UUID(job_id)
                query = select(EmailEvent).where(EmailEvent.id == email_id)
                result = await session.exec(query)
                email = result.first()

                if not email:
                    logger.error(f"Job {job_id}: Email not found in database")
                    return

                # Capture message_id for final payload
                gmail_message_id = email.message_id

                # Set final status
                email.status = EmailStatus.COMPLETED
                email.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

                session.add(email)
                await session.commit()
                await session.refresh(email)

                logger.info(
                    f"Job {job_id}: Database updated - status=COMPLETED "
                    f"intent={email.intent} risk_score={email.risk_score}"
                )

            except Exception as db_error:
                logger.error(
                    f"Job {job_id}: Database update failed: {db_error}", exc_info=True
                )
                await session.rollback()
                raise

        # STEP 3: Publish to final report queue
        final_payload = {
            "job_id": job_id,
            "message_id": gmail_message_id,  # Added for Action Agent
            "intent": state.get("intent", "{}"),
        }

        # Include sandbox results only if they exist
        if state.get("requiresB", "false").lower() == "true" and sandbox_data:
            final_payload["sandbox"] = state.get("sandbox", "{}")
        else:
            final_payload["sandbox"] = json.dumps(None)

        await redis.xadd(FINAL_REPORT_QUEUE, final_payload)

        logger.info(
            f"Job {job_id}: Published to final report queue "
            f"(has_sandbox={bool(sandbox_data)})"
        )

        # STEP 4: Cleanup state
        await delete_state(redis, job_id)

        logger.info(f"Job {job_id}: Finalization complete ✓")

    except Exception as e:
        logger.error(f"Job {job_id}: Finalization failed: {e}", exc_info=True)
        # Don't delete state on failure - allow retry


# --- Background Cleanup Task ---


async def cleanup_expired_jobs() -> None:
    """Background task to cleanup expired jobs based on TTL."""
    logger.info("Starting TTL cleanup background task")
    redis = await get_redis_client()

    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)

            # Scan for job state keys
            pattern = f"{STATE_PREFIX}*"
            expired_count = 0

            async for key in redis.scan_iter(match=pattern, count=100):
                state = await redis.hgetall(key)
                if not state:
                    continue

                job_id = state.get("job_id")
                created_at_str = state.get("created_at")

                if not created_at_str:
                    logger.warning(
                        f"Job {job_id}: Missing created_at, skipping cleanup check"
                    )
                    continue

                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)

                    age = datetime.now(timezone.utc) - created_at
                    age_seconds = age.total_seconds()

                    if age_seconds > STATE_TTL:
                        logger.warning(
                            f"Job {job_id}: Expired after {age_seconds:.0f}s "
                            f"(TTL={STATE_TTL}s) - cleaning up"
                        )

                        # TODO: Emit to DLQ or mark as failed in database
                        # For now, just delete the state
                        await delete_state(redis, job_id)
                        expired_count += 1

                except Exception as parse_error:
                    logger.error(
                        f"Job {job_id}: Failed to parse created_at={created_at_str}: {parse_error}"
                    )

            if expired_count > 0:
                logger.info(f"Cleanup complete: removed {expired_count} expired job(s)")

        except Exception as e:
            logger.error(f"Cleanup task error: {e}", exc_info=True)
            await asyncio.sleep(5)  # Brief pause before retry


# --- Main Worker Loop ---


async def run_loop() -> None:
    """Main aggregator loop - consumes from 3 streams."""
    await init_db()
    redis = await get_redis_client()

    group_name = "aggregator_workers"
    consumer_name = f"aggregator-{random.randint(1000, 9999)}"

    # Create consumer groups for all 3 streams
    for stream in [
        JOB_AGGREGATOR_QUEUE,
        EMAIL_INTENT_DONE_QUEUE,
        EMAIL_ANALYSIS_DONE_QUEUE,
    ]:
        try:
            await redis.xgroup_create(stream, group_name, id="0", mkstream=True)
            logger.info(f"Consumer group {group_name} created for {stream}")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.warning(f"Error creating consumer group for {stream}: {e}")

    logger.info(
        f"Aggregator {consumer_name} started. Listening on "
        f"{JOB_AGGREGATOR_QUEUE}, {EMAIL_INTENT_DONE_QUEUE}, {EMAIL_ANALYSIS_DONE_QUEUE}"
    )

    while True:
        try:
            # Read from all 3 streams simultaneously
            streams = await redis.xreadgroup(
                group_name,
                consumer_name,
                {
                    JOB_AGGREGATOR_QUEUE: ">",
                    EMAIL_INTENT_DONE_QUEUE: ">",
                    EMAIL_ANALYSIS_DONE_QUEUE: ">",
                },
                count=10,
                block=5000,
            )

            if not streams:
                continue

            # Process messages from each stream
            for stream_name, messages in streams:
                for message_id, payload in messages:
                    try:
                        logger.debug(
                            f"Received message {message_id} from {stream_name}: {payload}"
                        )

                        # Route to appropriate handler
                        if stream_name == JOB_AGGREGATOR_QUEUE:
                            await handle_control(redis, payload)
                        elif stream_name == EMAIL_INTENT_DONE_QUEUE:
                            await handle_intent_done(redis, payload)
                        elif stream_name == EMAIL_ANALYSIS_DONE_QUEUE:
                            await handle_sandbox_done(redis, payload)
                        else:
                            logger.warning(f"Unknown stream: {stream_name}")

                        # Acknowledge message after successful processing
                        await redis.xack(stream_name, group_name, message_id)
                        logger.debug(f"Acknowledged {message_id} from {stream_name}")

                    except Exception as msg_error:
                        logger.error(
                            f"Error processing message {message_id} from {stream_name}: {msg_error}",
                            exc_info=True,
                        )
                        # Don't ack on error - message will be redelivered

        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            await asyncio.sleep(1)


# --- FastAPI App ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start background tasks."""
    # Startup
    worker_task = asyncio.create_task(run_loop())
    cleanup_task = asyncio.create_task(cleanup_expired_jobs())
    logger.info("Aggregator worker and cleanup tasks started")

    yield

    # Shutdown
    worker_task.cancel()
    cleanup_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Aggregator worker shut down gracefully")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok", "service": "aggregator-worker"}


def main() -> None:
    """Entry point for the aggregator service."""
    port = int(os.getenv("PORT", "8080"))
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
