"""
Action Agent - The Enforcer

This is the final agent in the MailShieldAI security pipeline.
It consumes final verdicts from the Aggregator (via Redis Stream), applies Gmail labels,
and optionally moves malicious emails to Spam.

Flow:
1. Receive Final Report from Redis Stream (FINAL_REPORT_QUEUE)
2. Extract verdict from sandbox results
3. Apply appropriate Gmail label (MailShield/MALICIOUS, CAUTIOUS, or SAFE)
4. For malicious emails, optionally move to Spam folder
5. Log action for audit trail

Author: MailShieldAI Team
"""

import os
import json
import asyncio
import random
from typing import Set, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
import google.auth
from googleapiclient.discovery import build
from dotenv import load_dotenv

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", ".."))
from packages.shared.logger import setup_logging
from packages.shared.queue import get_redis_client, FINAL_REPORT_QUEUE
from gmail_labels import apply_labels, ensure_labels_exist, get_label_for_verdict

load_dotenv()

# --- Configuration ---
PORT = int(os.getenv("PORT", "9001"))
MOVE_MALICIOUS_TO_SPAM = os.getenv("MOVE_MALICIOUS_TO_SPAM", "true").lower() == "true"

# --- Concurrency Control ---
# Limit concurrent Gmail API calls to avoid rate limits
GMAIL_SEMAPHORE = asyncio.Semaphore(5)  # Gmail allows ~5-10 modify/sec

# --- Logging ---
logger = setup_logging("action-worker")

# --- State: In-memory Idempotency ---
# Tracks message_ids that have already been processed
processed_messages: Set[str] = set()


# --- Gmail Service ---
def get_gmail_service():
    """
    Falls back to ADC if available.
    """
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"ADC authentication failed: {e}")
        return None


# --- Core Processing Logic ---
async def process_action(message_id: str, sandbox_data: Optional[dict]) -> bool:
    """
    Main processing logic for applying actions based on security verdict.
    """
    logger.info(f"Starting action processing for message {message_id}")
    
    # STEP 1: Idempotency check
    if message_id in processed_messages:
        logger.info(f"Message {message_id}: Already processed, skipping")
        return True

    processed_messages.add(message_id)

    # STEP 2: Determine verdict from sandbox data
    # If no sandbox data (e.g. only Intent analysis), default to 'clean' regarding threats
    final_verdict = "clean"
    if sandbox_data:
        final_verdict = sandbox_data.get("verdict", "clean")
        # If unknown reached here, treat as suspicious
        if final_verdict == "unknown":
            final_verdict = "suspicious"

    logger.info(
        f"Message {message_id}: Verdict determined - {final_verdict} "
        f"(has_sandbox_data={bool(sandbox_data)})"
    )

    # Determine if we should move to spam
    move_to_spam = MOVE_MALICIOUS_TO_SPAM and final_verdict == "malicious"

    # Apply Gmail labels
    label_applied = get_label_for_verdict(final_verdict)

    # STEP 3: Apply Gmail labels and actions
    try:
        async with GMAIL_SEMAPHORE:
            service = get_gmail_service()
            if not service:
                logger.error(f"Message {message_id}: Failed to initialize Gmail service")
                return False

            success = await apply_labels(
                service=service,
                message_id=message_id,
                verdict=final_verdict,
                move_to_spam=move_to_spam,
            )

            if not success:
                logger.error(
                    f"Message {message_id}: Failed to apply labels - "
                    f"verdict={final_verdict} label={label_applied}"
                )
                return False

    except Exception as e:
        logger.error(
            f"Message {message_id}: Gmail labeling failed - {e}", 
            exc_info=True
        )
        return False

    # STEP 4: Log completion for audit trail
    logger.info(
        f"Message {message_id}: Action completed successfully - "
        f"verdict={final_verdict} label={label_applied} moved_to_spam={move_to_spam}"
    )
    return True


async def run_loop() -> None:
    """Main worker loop using Redis Streams Consumer Groups."""
    redis = await get_redis_client()

    group_name = "action_workers"
    consumer_name = f"worker-{random.randint(1000, 9999)}"

    try:
        await redis.xgroup_create(FINAL_REPORT_QUEUE, group_name, id="0", mkstream=True)
        logger.info(f"Consumer group {group_name} created.")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.warning(f"Error creating consumer group: {e}")

    logger.info(f"Worker {consumer_name} started. Listening on {FINAL_REPORT_QUEUE}...")

    # Pre-create labels
    try:
        service = get_gmail_service()
        if service:
            await ensure_labels_exist(service)
            logger.info("✓ MailShield labels initialized")
    except Exception as e:
        logger.warning(f"Could not pre-create labels: {e}")

    while True:
        try:
            streams = await redis.xreadgroup(
                group_name,
                consumer_name,
                {FINAL_REPORT_QUEUE: ">"},
                count=1,
                block=5000,
            )

            if not streams:
                continue

            for _, messages in streams:
                for msg_id, payload in messages:
                    # Payload from Aggregator: {'job_id': ..., 'message_id': ..., 'intent': ..., 'sandbox': ...}
                    job_id = payload.get("job_id")
                    gmail_message_id = payload.get("message_id")

                    if not gmail_message_id:
                        logger.warning(f"Missing message_id in job {job_id}")
                        await redis.xack(FINAL_REPORT_QUEUE, group_name, msg_id)
                        continue

                    sandbox_str = payload.get("sandbox")
                    sandbox_data = None
                    if sandbox_str:
                        try:
                            sandbox_data = json.loads(sandbox_str)
                        except:
                            pass

                    logger.info(
                        f"Processing action for message {gmail_message_id} (Job: {job_id})"
                    )

                    success = await process_action(gmail_message_id, sandbox_data)

                    if success:
                        await redis.xack(FINAL_REPORT_QUEUE, group_name, msg_id)
                        logger.debug(f"Acknowledged message {msg_id}")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start background tasks."""
    # Startup
    task = asyncio.create_task(run_loop())
    logger.info("Action Agent background task started")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Action Agent",
    description="Applies Gmail labels based on final security verdicts",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "action-agent",
        "processed_count": len(processed_messages),
    }


@app.get("/stats")
async def get_stats():
    """Get processing statistics."""
    return {
        "processed_messages": len(processed_messages),
        "recent_messages": list(processed_messages)[-10:],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
