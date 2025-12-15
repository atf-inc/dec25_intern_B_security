from __future__ import annotations

import asyncio
import os
import random
from datetime import datetime, timezone

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session, init_db
from models import EmailEvent, EmailStatus, RiskTier

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "5"))
BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "10"))


def classify_risk(score: int) -> RiskTier:
    if score < 30:
        return RiskTier.safe
    if score < 80:
        return RiskTier.cautious
    return RiskTier.threat


def build_dummy_analysis(score: int) -> dict:
    return {
        "indicators": ["suspicious_link", "urgency_language"],
        "confidence": round(min(1.0, max(0.0, score / 100)), 2),
        "threat_type": "phishing" if score >= 50 else "info",
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_pending(session: AsyncSession) -> list[EmailEvent]:
    result = await session.exec(
        select(EmailEvent).where(EmailEvent.status == EmailStatus.pending).limit(BATCH_LIMIT)
    )
    return result.all()


async def process_email(session: AsyncSession, email: EmailEvent) -> None:
    email.status = EmailStatus.processing
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
        email.status = EmailStatus.completed
    except Exception:  # noqa: BLE001
        email.status = EmailStatus.failed
        email.analysis_result = {"error": "processing_failed"}

    session.add(email)
    await session.commit()
    await session.refresh(email)


async def run_loop() -> None:
    await init_db()
    async for session in get_session():
        while True:
            pending = await fetch_pending(session)
            if not pending:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue

            for email in pending:
                await process_email(session, email)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    asyncio.run(run_loop())


if __name__ == "__main__":
    main()
