import asyncio
import json
import logging
import os
import uuid
from typing import Optional, Iterable

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
from packages.shared.queue import get_redis_client, EMAIL_INTENT_QUEUE, EMAIL_ANALYSIS_QUEUE, JOB_AGGREGATOR_QUEUE
from packages.shared.types import BackgroundSyncRequest


logger = logging.getLogger(__name__)
downstream_tasks = []

# Per-user sync locks to prevent concurrent sync operations
_sync_locks: dict[uuid.UUID, asyncio.Lock] = {}


async def email_exists(session: AsyncSession, message_id: str) -> bool:
    result = await session.exec(select(EmailEvent).where(EmailEvent.message_id == message_id))
    return result.first() is not None


def build_email_event(
    *,
    user_id: uuid.UUID,
    email,
    status: EmailStatus,
) -> tuple[EmailEvent, list[tuple[str, dict]]]:
    """
    Create EmailEvent and downstream queue payloads.
    
    CRITICAL: Control message (JOB_AGGREGATOR_QUEUE) MUST be published FIRST
    to establish job requirements before workers complete.
    """
    from datetime import datetime, timezone
    
    job_id = uuid.uuid4()
    job_id_str = str(job_id)
    downstream_tasks: list[tuple[str, dict]] = []

    email_event = EmailEvent(
        id=job_id,
        user_id=user_id,
        sender=email.sender,
        recipient=email.recipient,
        subject=email.subject,
        body_preview=email.body_preview,
        message_id=email.message_id,
        received_at=email.received_at,
        spf_status=email.auth_status.spf if email.auth_status else None,
        dkim_status=email.auth_status.dkim if email.auth_status else None,
        dmarc_status=email.auth_status.dmarc if email.auth_status else None,
        sender_ip=email.sender_ip,
        status=status,
    )

    # Evaluate if sandbox analysis is needed
    should_sandbox, _, _ = evaluate_static_risk(email)
    if should_sandbox:
        email_event.sandboxed = True
    
    logger.info(
        f"Building email event job_id={job_id_str} message_id={email.message_id} "
        f"requiresB={should_sandbox} sender={email.sender}"
    )

    # CRITICAL: Control stream message FIRST (position 0)
    # This establishes job requirements before workers complete
    control_payload = {
        'job_id': job_id_str,
        'requiresB': str(should_sandbox),
        'created_at': email.received_at.isoformat() if email.received_at else datetime.now(timezone.utc).isoformat(),
    }
    downstream_tasks.append((JOB_AGGREGATOR_QUEUE, control_payload))
    logger.debug(f"Job {job_id_str}: Added control message with requiresB={should_sandbox}")

    # Intent analysis (always runs)
    # FIXED: Changed 'job_id' to 'email_id' to match worker expectations
    intent_payload = {
        'email_id': job_id_str,  # Worker expects 'email_id', not 'job_id'
        'subject': email.subject or '',
        'body': email.body_text or email.body_html or '',
    }
    downstream_tasks.append((EMAIL_INTENT_QUEUE, intent_payload))
    logger.debug(f"Job {job_id_str}: Added intent analysis task")

    # Sandbox analysis (conditional)
    if should_sandbox:
        # FIXED: Changed 'job_id' to 'email_id' to match worker expectations
        sandbox_payload = {
            'email_id': job_id_str,  # Worker expects 'email_id', not 'job_id'
            'message_id': email.message_id,
            'extracted_urls': json.dumps(email.extracted_urls),
            'attachment_metadata': json.dumps([att.model_dump_json() for att in email.attachments]),
        }
        downstream_tasks.append((EMAIL_ANALYSIS_QUEUE, sandbox_payload))
        logger.debug(f"Job {job_id_str}: Added sandbox analysis task (risk evaluation triggered)")
    else:
        logger.debug(f"Job {job_id_str}: Skipping sandbox analysis (low risk)")

    logger.info(
        f"Job {job_id_str}: Created {len(downstream_tasks)} downstream tasks "
        f"(control + intent + {'sandbox' if should_sandbox else 'no-sandbox'})"
    )

    return email_event, downstream_tasks


async def ingest_emails(
    *,
    emails: Iterable,
    user_id: uuid.UUID,
    session: AsyncSession,
    status: EmailStatus,
) -> int:
    """
    Deduplicate, persist emails, and enqueue downstream tasks.
    """
    count = 0
    skipped = 0
    downstream_tasks: list[tuple[str, dict]] = []

    for email in emails:
        if await email_exists(session, email.message_id):
            logger.debug('Email already exists: %s', email.message_id)
            skipped += 1
            continue

        email_event, tasks = build_email_event(
            user_id=user_id,
            email=email,
            status=status,
        )

        session.add(email_event)
        downstream_tasks.extend(tasks)
        count += 1

    if count == 0:
        logger.info('No new emails to ingest (skipped %d duplicate(s))', skipped)
        return 0

    await session.commit()

    redis = await get_redis_client()
    for stream, payload in downstream_tasks:
        await redis.xadd(stream, payload)

    logger.info(
        'Queued %s downstream tasks for %s new email(s) (skipped %d duplicate(s))',
        len(downstream_tasks),
        count,
        skipped,
    )

    return count


router = APIRouter()


@router.get('', response_model=list[EmailRead])
async def list_emails(
    status_filter: Optional[EmailStatus] = None,
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailEvent]:
    """List emails for the current user."""
    query = (
        select(EmailEvent).where(EmailEvent.user_id == user.id).order_by(EmailEvent.created_at.desc())  # type: ignore
    )
    if status_filter:
        query = query.where(EmailEvent.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await session.exec(query)
    return list(result.all())


@router.post('/sync', status_code=status.HTTP_202_ACCEPTED)
async def sync_emails(
    x_google_token: str = Header(..., alias='X-Google-Token'),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Get or create lock for this user
    if user.id not in _sync_locks:
        _sync_locks[user.id] = asyncio.Lock()

    lock = _sync_locks[user.id]

    # Try to acquire lock without blocking
    if lock.locked():
        logger.info('Sync already in progress for user %s', user.id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Sync already in progress',
        )

    async with lock:
        try:
            gmail_emails = await asyncio.wait_for(
                run_in_threadpool(fetch_gmail_messages, x_google_token, 20),
                timeout=30.0,
            )

            logger.info('Starting email ingestion for user %s', user.id)
            count = await ingest_emails(
                emails=gmail_emails,
                user_id=user.id,
                session=session,
                status=EmailStatus.PENDING,
            )
            logger.info('Completed email ingestion: %d new emails processed', count)

            return {
                'status': 'synced',
                'new_messages': count,
            }

        except Exception as e:
            logger.exception('Error syncing Gmail')
            raise HTTPException(
                status_code=500,
                detail='Gmail sync failed',
            ) from e


@router.post('/sync/background', status_code=status.HTTP_202_ACCEPTED)
async def sync_background(
    request: BackgroundSyncRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    logger.info(
        'Background sync requested for %s (history_id=%s)',
        request.email_address,
        request.history_id,
    )

    user = (await session.exec(select(User).where(User.email == request.email_address))).first()

    if not user:
        return {'status': 'skipped', 'reason': 'user_not_found'}

    if not user.refresh_token:
        return {'status': 'skipped', 'reason': 'no_refresh_token'}

    try:
        client_id = os.getenv('AUTH_GOOGLE_ID')
        client_secret = os.getenv('AUTH_GOOGLE_SECRET')

        if not client_id or not client_secret:
            logger.error('Missing Google OAuth credentials')
            return {'status': 'error', 'reason': 'server_config_error'}

        creds = Credentials(
            token=None,
            refresh_token=user.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret,
            scopes=['https://www.googleapis.com/auth/gmail.readonly'],
        )

        service = GmailService(credentials=creds)

        new_emails = await run_in_threadpool(
            service.fetch_by_history,
            request.history_id,
        )

        if not new_emails:
            return {'status': 'synced', 'count': 0}

        count = await ingest_emails(
            emails=new_emails,
            user_id=user.id,
            session=session,
            status=EmailStatus.PROCESSING,
        )

        return {'status': 'synced', 'count': count}

    except Exception:
        logger.exception('Background sync failed')
        raise HTTPException(
            status_code=500,
            detail='Background sync failed',
        )
