import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool

from apps.api.services.auth import get_current_user
from apps.api.services.gmail import fetch_gmail_messages
from packages.shared.constants import EmailStatus
from packages.shared.database import get_session
from packages.shared.models import User, EmailEvent, EmailCreate, EmailRead
from packages.shared.queue import get_redis_client, EMAIL_INTENT_QUEUE, EMAIL_ANALYSIS_QUEUE

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("", response_model=EmailRead, status_code=status.HTTP_201_CREATED)
async def ingest_email(
    payload: EmailCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EmailEvent:
    """Ingest a new email for analysis."""
    email = EmailEvent(
        user_id=user.id,
        sender=payload.sender,
        recipient=payload.recipient,
        subject=payload.subject,
        # body_preview=payload.body_preview, body preview by agent later
    )
    session.add(email)
    await session.commit()
    await session.refresh(email)

    # Push to processing queue
    redis = await get_redis_client()
    await redis.rpush(EMAIL_INTENT_QUEUE, str(email.id))

    return email


@router.get("", response_model=list[EmailRead])
async def list_emails(
    status_filter: Optional[EmailStatus] = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailEvent]:
    """List emails for the current user."""
    query = select(EmailEvent).where(EmailEvent.user_id == user.id).order_by(EmailEvent.created_at.desc())
    if status_filter:
        query = query.where(EmailEvent.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await session.exec(query)
    return result.all()


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_emails(
    x_google_token: str = Header(..., alias="X-Google-Token"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Sync emails from Gmail with full metadata."""
    try:
        # Fetch recent messages in a thread pool to avoid blocking the event loop
        gmail_emails = await run_in_threadpool(fetch_gmail_messages, x_google_token, 20)
        
        count = 0
        new_email_ids = []
        for g_email in gmail_emails:
            msg_id = g_email.get("message_id")
            
            # Deduplicate by message_id
            if msg_id:
                existing = await session.exec(select(EmailEvent).where(EmailEvent.message_id == msg_id))
                if existing.first():
                    continue

            new_id = uuid.uuid4()
            email = EmailEvent(
                id=new_id,
                user_id=user.id,
                sender=g_email["sender"],
                recipient=g_email["recipient"],
                subject=g_email["subject"],
                body_preview=g_email["body_preview"],
                message_id=msg_id,
                received_at=g_email.get("received_at"),
                spf_status=g_email.get("spf_status"),
                dkim_status=g_email.get("dkim_status"),
                dmarc_status=g_email.get("dmarc_status"),
                sender_ip=g_email.get("sender_ip"),
                attachment_info=g_email.get("attachment_info"),
                status=g_email.get("status", EmailStatus.PENDING),
            )
            session.add(email)
            new_email_ids.append(str(new_id))
            count += 1
            
        if count > 0:
            await session.commit()
            
            # Push new emails to queue
            if new_email_ids:
                redis = await get_redis_client()
                await redis.rpush(EMAIL_PROCESSING_QUEUE, *new_email_ids)
            
        return {"status": "synced", "new_messages": count}

    except Exception as e:
        logger.error(f"Error syncing Gmail: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sync failed")
