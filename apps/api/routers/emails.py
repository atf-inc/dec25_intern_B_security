import asyncio
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool
from google.oauth2.credentials import Credentials

from apps.api.services.auth import get_current_user
from apps.api.services.gmail import fetch_gmail_messages, GmailService
from apps.api.services.risk import evaluate_static_risk
from packages.shared.constants import EmailStatus
from packages.shared.database import get_session
from packages.shared.models import User, EmailEvent, EmailRead
from packages.shared.queue import (
    get_redis_client,
    EMAIL_INTENT_QUEUE,
)
from packages.shared.types import BackgroundSyncRequest


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list[EmailRead])
async def list_emails(
    status_filter: Optional[EmailStatus] = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailEvent]:
    """List emails for the current user."""
    query = (
        select(EmailEvent)
        .where(EmailEvent.user_id == user.id)
        .order_by(EmailEvent.created_at.desc())  # type: ignore
    )
    if status_filter:
        query = query.where(EmailEvent.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await session.exec(query)
    return list(result.all())


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_emails(
    x_google_token: str = Header(..., alias="X-Google-Token"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Sync emails from Gmail using the new StructuredEmail pipeline.
    """
    try:
        # Fetch emails in a threadpool (Gmail SDK is blocking)
        gmail_emails = await asyncio.wait_for(
            run_in_threadpool(fetch_gmail_messages, x_google_token, 20), timeout=30.0
        )

        count = 0
        downstream_tasks = []

        for email in gmail_emails:
            # Deduplicate by Gmail message ID
            existing = await session.exec(
                select(EmailEvent).where(EmailEvent.message_id == email.message_id)
            )
            if existing.first():
                continue

            new_id = uuid.uuid4()

            email_event = EmailEvent(
                id=new_id,
                user_id=user.id,
                # Envelope
                sender=email.sender,
                recipient=email.recipient,
                subject=email.subject,
                # Content
                body_preview=email.body_preview,
                message_id=email.message_id,
                received_at=email.received_at,
                # Auth / Security
                spf_status=email.auth_status.spf if email.auth_status else None,
                dkim_status=email.auth_status.dkim if email.auth_status else None,
                dmarc_status=email.auth_status.dmarc if email.auth_status else None,
                sender_ip=email.sender_ip,
                # Status
                status=email.status,
            )

            # Always queue for intent analysis
            intent_payload = {
                "email_id": str(new_id),
                "subject": email.subject or "",
                "body": email.body_text or email.body_html or "",
            }
            downstream_tasks.append((EMAIL_INTENT_QUEUE, intent_payload))

            # Check if sandbox analysis is needed
            should_sandbox, reason, score = evaluate_static_risk(email)
            if should_sandbox:
                email_event.sandboxed = True
                analysis_payload = {
                    "email_id": str(new_id),
                    "message_id": email.message_id,
                    "extracted_urls": email.extracted_urls,
                    "attachment_metadata": [
                        att.model_dump_json() for att in email.attachments
                    ],
                }
                downstream_tasks.append((EMAIL_ANALYSIS_QUEUE, analysis_payload))

            session.add(email_event)
            count += 1

        if count > 0:
            await session.commit()

            # Push new emails to Intent worker queue for analysis
            redis = await get_redis_client()
            await redis.rpush(EMAIL_INTENT_QUEUE, *new_email_ids)
            logger.info(f"Pushed {count} new emails to Intent worker queue")

        return {
            "status": "synced",
            "new_messages": count,
        }

    except Exception as e:
        logger.exception("Error syncing Gmail: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gmail sync failed",
        ) from e


@router.post("/sync/background", status_code=status.HTTP_202_ACCEPTED)
async def sync_background(
    request: BackgroundSyncRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Handle background sync triggered by Pub/Sub worker.
    Uses stored refresh token to fetch new emails.
    """
    logger.info(
        f"Background sync requested for {request.email_address}, history_id={request.history_id}"
    )

    # 1. Find User
    user_query = select(User).where(User.email == request.email_address)
    result = await session.exec(user_query)
    user = result.first()

    if not user:
        logger.warning(f"User not found for background sync: {request.email_address}")
        # Return 202 to acknowledge receipt even if we can't process
        return {"status": "skipped", "reason": "user_not_found"}

    if not user.refresh_token:
        logger.warning(f"No refresh token for user {user.id} ({request.email_address})")
        return {"status": "skipped", "reason": "no_refresh_token"}

    try:
        # 2. Reconstruct Credentials
        # We need client ID/secret to refresh tokens
        client_id = os.getenv("AUTH_GOOGLE_ID")
        client_secret = os.getenv("AUTH_GOOGLE_SECRET")

        if not client_id or not client_secret:
            logger.error("Missing Google Auth credentials (ID/Secret) in env")
            return {"status": "error", "reason": "server_config_error"}

        creds = Credentials(
            token=None,  # Access token is likely expired, let refresh happen
            refresh_token=user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # 3. Fetch Changes using GmailService
        # Run in threadpool as it's blocking I/O
        service = GmailService(credentials=creds)

        # Note: fetch_by_history is synchronous, so wrap in run_in_threadpool
        # But constructing service might also do I/O if it refreshes token immediately?
        # Usually it refreshes on first request.

        new_emails = await run_in_threadpool(
            service.fetch_by_history, request.history_id
        )

        if not new_emails:
            logger.info("No new emails found in history sync")
            return {"status": "synced", "count": 0}

        # 4. Save to DB (Deduplicate & Store)
        count = 0
        downstream_tasks = []

        for g_email in new_emails:
            msg_id = g_email.message_id

            # Deduplicate
            existing = await session.exec(
                select(EmailEvent).where(EmailEvent.message_id == msg_id)
            )
            if existing.first():
                continue

            new_id = uuid.uuid4()
            email_event = EmailEvent(
                id=new_id,
                user_id=user.id,
                sender=g_email.sender,
                recipient=g_email.recipient,
                subject=g_email.subject,
                body_preview=g_email.body_preview,
                message_id=msg_id,
                received_at=g_email.received_at,
                spf_status=g_email.auth_status.spf if g_email.auth_status else None,
                dkim_status=g_email.auth_status.dkim if g_email.auth_status else None,
                dmarc_status=g_email.auth_status.dmarc if g_email.auth_status else None,
                sender_ip=g_email.sender_ip,
                status=EmailStatus.PROCESSING,
            )

            # Always queue for intent analysis
            intent_payload = {
                "email_id": str(new_id),
                "subject": g_email.subject or "",
                "body": g_email.body_text or g_email.body_html or "",
            }
            downstream_tasks.append((EMAIL_INTENT_QUEUE, intent_payload))

            # Check if sandbox analysis is needed
            should_sandbox, reason, score = evaluate_static_risk(g_email)
            if should_sandbox:
                email_event.sandboxed = True
                analysis_payload = {
                    "email_id": str(new_id),
                    "message_id": g_email.message_id,
                    "extracted_urls": g_email.extracted_urls,
                    "attachment_metadata": [
                        att.model_dump_json() for att in g_email.attachments
                    ],
                }
                downstream_tasks.append((EMAIL_ANALYSIS_QUEUE, analysis_payload))

            session.add(email_event)
            count += 1

        if count > 0:
            await session.commit()

            # Push to downstream queues
            if downstream_tasks:
                redis = await get_redis_client()
                for stream, payload in downstream_tasks:
                    await redis.xadd(stream, payload)
                logger.info(
                    f"Queued {len(downstream_tasks)} tasks for analysis across multiple streams"
                )

        return {"status": "synced", "count": count}

    except Exception as e:
        logger.exception("Background sync failed")
        # Return success to worker so it doesn't retry indefinitely on logical errors?
        # Or 500 to invoke Pub/Sub retry?
        # Strategy: Log error, return 500 to allow retry for transient issues.
        # But for logic errors (parsing), maybe we should catch specific exceptions.
        # strict retry logic is better for robustness.
        raise HTTPException(status_code=500, detail="Background sync failed") from e
