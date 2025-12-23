from __future__ import annotations

import asyncio
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus, RiskTier
from packages.shared.models import EmailEvent
from packages.shared.queue import get_redis_client, EMAIL_INTENT_QUEUE
from packages.shared.logger import setup_logging
from apps.worker.intent.taxonomy import Intent

# Configure logging
logger = setup_logging("intent-worker")

# Map intent types to base risk scores (0-100)
RISK_MAPPING = {
    # High risk security threats
    Intent.PHISHING: 95,
    Intent.MALWARE: 98,
    Intent.SOCIAL_ENGINEERING: 90,
    Intent.BEC_FRAUD: 95,
    Intent.RECONNAISSANCE: 75,
    Intent.SPAM: 60,
    
    # Medium risk business emails
    Intent.INVOICE: 40,
    Intent.PAYMENT: 45,
    Intent.SALES: 30,
    
    # Low risk legitimate emails
    Intent.MEETING_REQUEST: 15,
    Intent.TASK_REQUEST: 15,
    Intent.FOLLOW_UP: 10,
    Intent.SUPPORT: 20,
    Intent.NEWSLETTER: 25,
    Intent.PERSONAL: 10,
    Intent.UNKNOWN: 50,
}


def classify_risk(score: int) -> RiskTier:
    if score < 30:
        return RiskTier.SAFE
    if score < 80:
        return RiskTier.CAUTIOUS
    return RiskTier.THREAT





async def process_email(session: AsyncSession, email: EmailEvent, payload_subject: str = None, payload_body: str = None) -> bool:
    session.add(email)
    await session.commit()
    await session.refresh(email)

    try:
        from apps.worker.intent.graph import intent_agent
        from apps.worker.intent.schemas import EmailIntentState

        state = EmailIntentState(
            subject=payload_subject or email.subject or "",
            body=payload_body or email.body_preview or "",
        )

        # Invoke LangGraph
        result = await intent_agent.ainvoke(state.dict())

        final_intent = result.get("final_intent")
        final_confidence = result.get("final_confidence")
        final_indicators = result.get("final_indicators")

        # Save to DB (convert Enum to string)
        email.intent = final_intent.value if final_intent else None
        email.intent_confidence = final_confidence
        email.intent_indicators = final_indicators
        email.intent_processed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        # Use the Enum object for logic lookup
        if final_intent and final_intent in RISK_MAPPING:
            base_score = RISK_MAPPING[final_intent]
            # Adjust score based on confidence
            # If low confidence, pull towards neutral (50), if high confidence, stay at base
            confidence = final_confidence or 0.5
            risk_score = int(base_score * confidence + (50 * (1 - confidence)))

            email.risk_score = risk_score
            email.risk_tier = (
                RiskTier.SAFE
                if risk_score < 30
                else (RiskTier.CAUTIOUS if risk_score < 80 else RiskTier.THREAT)
            )

        email.status = EmailStatus.COMPLETED
        
        # Commit changes to database
        session.add(email)
        await session.commit()
        await session.refresh(email)  # Refresh prevents 'greenlet_spawn' error on attribute access
        

        
        return True
        
    except Exception as e:
        logger.error(f"Error in process_email: {e}")
        try:
            await session.rollback()  # Rollback the failed transaction so we can use the session again
            email.status = EmailStatus.FAILED
            session.add(email)
            await session.commit()
        except Exception as commit_err:
            logger.error(f"Failed to persist FAILED status: {commit_err}")
        return False


async def run_loop() -> None:
    """Main worker loop using Redis Streams Consumer Groups."""
    await init_db()
    redis = await get_redis_client()

    group_name = "intent_workers"
    consumer_name = f"worker-{random.randint(1000, 9999)}"

    # Create consumer group if it doesn't exist
    try:
        await redis.xgroup_create(EMAIL_INTENT_QUEUE, group_name, id="0", mkstream=True)
        logger.info(f"Consumer group {group_name} created.")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.warning(f"Error creating consumer group: {e}")

    logger.info(f"Worker {consumer_name} started. Listening on {EMAIL_INTENT_QUEUE}...")

    while True:
        try:
            # Read from group
            # Count=1, block=5000ms
            streams = await redis.xreadgroup(
                group_name,
                consumer_name,
                {EMAIL_INTENT_QUEUE: ">"},
                count=1,
                block=5000,
            )

            if not streams:
                continue

            for stream_name, messages in streams:
                for message_id, payload in messages:
                    email_id_str = payload.get("email_id")
                    payload_subject = payload.get("subject")
                    payload_body = payload.get("body")

                    if not email_id_str:
                        logger.warning(f"Invalid payload in message {message_id}")
                        await redis.xack(EMAIL_INTENT_QUEUE, group_name, message_id)
                        continue

                    logger.info(
                        f"Processing message {message_id} (Email ID: {email_id_str})"
                    )

                    processed_successfully = False
                    # Use async context manager for session to avoid leaks and handle errors better
                    from contextlib import asynccontextmanager

                    @asynccontextmanager
                    async def session_scope():
                        async for s in get_session():
                            yield s
                            break

                    async with session_scope() as session:
                        try:
                            query = select(EmailEvent).where(
                                EmailEvent.id == email_id_str
                            )
                            result = await session.exec(query)
                            email = result.first()

                            if not email:
                                logger.warning(f"Email {email_id_str} not found.")
                                # Acknowledge message if email is not found to prevent redelivery
                                await redis.xack(
                                    EMAIL_INTENT_QUEUE, group_name, message_id
                                )
                                continue

                            processed_successfully = await process_email(
                                session, email, payload_subject, payload_body
                            )
                        except Exception as inner_e:
                            logger.error(f"Error processing {email_id_str}: {inner_e}")

                    if processed_successfully:
                        await redis.xack(EMAIL_INTENT_QUEUE, group_name, message_id)
                        logger.info(f"Acknowledged message {message_id}")

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)


# Create lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to start background tasks."""
    # Startup
    task = asyncio.create_task(run_loop())
    print("Intent worker background task started")
    yield
    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok", "service": "intent-worker"}


def main() -> None:
    """Entry point for the worker service."""
    port = int(os.getenv("PORT", "8080"))
    # Run uvicorn server
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
