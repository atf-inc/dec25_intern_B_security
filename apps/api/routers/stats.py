import logging

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func

from apps.api.services.auth import get_current_user
from packages.shared.database import get_session
from packages.shared.models import User, EmailEvent

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get email statistics for the current user."""
    
    # Get total count directly from DB
    total_result = await session.exec(
        select(func.count()).select_from(EmailEvent).where(EmailEvent.user_id == user.id)
    )
    total_emails = total_result.one() or 0

    # Get counts by risk tier using aggregation
    tier_counts_result = await session.exec(
        select(EmailEvent.risk_tier, func.count())
        .where(EmailEvent.user_id == user.id)
        .group_by(EmailEvent.risk_tier)
    )
    
    # Initialize counters
    safe_count = 0
    cautious_count = 0
    threat_count = 0
    
    # Map DB results to counters
    for tier, count in tier_counts_result:
        if tier:
            # tier is an Enum member, so we access .value
            if tier.value == "SAFE":
                safe_count = count
            elif tier.value == "CAUTIOUS":
                cautious_count = count
            elif tier.value == "THREAT":
                threat_count = count
    
    logger.info(
        'Stats requested for user %s: total=%d, safe=%d, cautious=%d, threat=%d',
        user.id, total_emails, safe_count, cautious_count, threat_count
    )
    
    return {
        "total_emails": total_emails,
        "safe": safe_count,
        "cautious": cautious_count,
        "threat": threat_count,
        "pending": total_emails - safe_count - cautious_count - threat_count,
    }
