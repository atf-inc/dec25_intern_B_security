from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session, init_db
from packages.shared.constants import EmailStatus, RiskTier
from packages.shared.models import EmailEvent
from packages.shared.queue import get_redis_client, EMAIL_INTENT_QUEUE


def classify_risk(score: int) -> RiskTier:
    if score < 30:
        return RiskTier.SAFE
    if score < 80:
        return RiskTier.CAUTIOUS
    return RiskTier.THREAT


def build_dummy_analysis(score: int) -> dict:
    return {
        "indicators": ["suspicious_link", "urgency_language"],
        "confidence": round(min(1.0, max(0.0, score / 100)), 2),
        "threat_type": "phishing" if score >= 50 else "info",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


async def process_email(session: AsyncSession, email: EmailEvent) -> None:
    session.add(email)
    await session.commit()
    await session.refresh(email)

    try:
        risk_score = random.randint(0, 100)
        risk_tier = classify_risk(risk_score)
        analysis_result = build_dummy_analysis(risk_score)

        email.risk_score = risk_score
        email.risk_tier = risk_tier
        email.analysis_result = analysis_result
        email.status = EmailStatus.COMPLETED
    except Exception:  # noqa: BLE001
        email.status = EmailStatus.FAILED
        email.analysis_result = {"error": "processing_failed"}

    session.add(email)
    await session.commit()
    await session.refresh(email)


async def run_loop() -> None:
    """Main worker loop that pops emails from Redis queue and processes them.
    
    Uses BLPOP to block until an email ID is available.
    """
    await init_db()
    redis = await get_redis_client()
    print(f"Worker started. Listening on {EMAIL_INTENT_QUEUE}...")

    while True:
        try:
            # Block until an item is available
            # blpop returns (queue_name, element) or None if timeout
            result = await redis.blpop(EMAIL_INTENT_QUEUE, timeout=5)
            
            if not result:
                continue
                
            queue_name, email_id_str = result
            
            # Process the email in a fresh session
            async for session in get_session():
                try:
                    # Find the email
                    query = select(EmailEvent).where(EmailEvent.id == email_id_str)
                    result = await session.exec(query)
                    email = result.first()
                    
                    if not email:
                        print(f"Email {email_id_str} not found in DB.")
                        break # Exit session
                    
                    if email.status != EmailStatus.PENDING:
                        print(f"Email {email_id_str} is not PENDING (status={email.status}). Skipping.")
                        break
                        
                    print(f"Processing email ID: {email_id_str}")
                    await process_email(session, email)
                    
                except Exception as inner_e:
                    print(f"Error processing email {email_id_str}: {inner_e}")
                
                break # Exit session context manager
                    
        except Exception as e:  # noqa: BLE001
            # Log error but continue running
            print(f"Worker loop error: {e}")
            await asyncio.sleep(1)


app = FastAPI()


@app.get("/")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok", "service": "agent-worker"}


@app.on_event("startup")
async def on_startup():
    """Start the worker loop in the background."""
    # Run the worker loop as a background task
    asyncio.create_task(run_loop())


def main() -> None:
    """Entry point for the worker service."""
    port = int(os.getenv("PORT", "8080"))
    # Run uvicorn server
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
