from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from apps.api.services.auth import get_current_user
from packages.shared.database import get_session
from packages.shared.models import User, EmailEvent

router = APIRouter()

@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get email statistics for the current user."""
    
    # Get all emails for user
    all_emails = await session.exec(
        select(EmailEvent).where(EmailEvent.user_id == user.id)
    )
    emails = all_emails.all()
    
    # Count by risk tier in Python to avoid enum issues
    total_emails = len(emails)
    safe_count = sum(1 for e in emails if e.risk_tier and e.risk_tier.value == "SAFE")
    cautious_count = sum(1 for e in emails if e.risk_tier and e.risk_tier.value == "CAUTIOUS")
    threat_count = sum(1 for e in emails if e.risk_tier and e.risk_tier.value == "THREAT")
    
    return {
        "total_emails": total_emails,
        "safe": safe_count,
        "cautious": cautious_count,
        "threat": threat_count,
        "pending": total_emails - safe_count - cautious_count - threat_count,
    }
