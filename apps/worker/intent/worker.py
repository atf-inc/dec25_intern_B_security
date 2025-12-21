from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Support both module import (for tests) and direct execution (for Docker)
try:
    from .database import get_session, init_db
    from .models import EmailEvent, EmailStatus, RiskTier
except ImportError:
    from database import get_session, init_db
    from models import EmailEvent, EmailStatus, RiskTier

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "10"))


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


async def fetch_pending(session: AsyncSession) -> list[EmailEvent]:
    result = await session.exec(
        select(EmailEvent).where(EmailEvent.status == EmailStatus.PENDING).limit(BATCH_LIMIT)
    )
    return result.all()


async def process_email(session: AsyncSession, email: EmailEvent) -> None:
    email.status = EmailStatus.PROCESSING
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
    """Main worker loop that polls for pending emails and processes them.
    
    Each iteration acquires a fresh session to avoid stale reads,
    connection timeouts, and identity-map bloat from long-lived sessions.
    """
    await init_db()
    while True:
        try:
            # Acquire a fresh session for each poll iteration
            async for session in get_session():
                pending = await fetch_pending(session)
                if not pending:
                    break  # Exit session context, sleep, then get new session
                
                for email in pending:
                    await process_email(session, email)
                break  # Exit session context after processing batch
        except Exception as e:  # noqa: BLE001
            # Log error but continue running - session will be cleaned up
            print(f"Worker error: {e}")
        
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


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
