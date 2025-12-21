"""MailShieldAI Dashboard API - Single User Architecture."""

from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.auth.transport import requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool

from database import get_session, init_db
from models import EmailEvent, EmailStatus, RiskTier, ThreatCategory, User

load_dotenv()

logger = logging.getLogger(__name__)


def _validate_cors_config() -> list[str]:
    """Validate CORS configuration and return parsed origins list.
    
    Fails fast if credentials are enabled with wildcard origins (insecure).
    """
    cors_origins_raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    allow_credentials = True  # We always use credentials for auth
    
    if not cors_origins_raw:
        logger.error(
            "CORS_ALLOW_ORIGINS environment variable is not set. "
            "Please set it to a comma-separated list of allowed origins."
        )
        sys.exit(1)
    
    # Parse comma-separated origins, trim whitespace
    origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
    
    if not origins:
        logger.error("CORS_ALLOW_ORIGINS is empty after parsing.")
        sys.exit(1)
    
    # Check for wildcard with credentials - this is invalid per CORS spec
    if "*" in origins and allow_credentials:
        logger.error(
            "SECURITY ERROR: CORS_ALLOW_ORIGINS='*' with allow_credentials=True is invalid. "
            "Browsers will reject this configuration. "
            "Please specify explicit origins (e.g., 'http://localhost:3000,https://app.example.com')."
        )
        sys.exit(1)
    
    logger.info(f"CORS configured for origins: {origins}")
    return origins


# Validate CORS configuration before app creation
_cors_origins = _validate_cors_config()

app = FastAPI(title="MailShieldAI Dashboard API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with CORS headers."""
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
    )


GOOGLE_CLIENT_ID = os.getenv("AUTH_GOOGLE_ID")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

if DEV_MODE:
    logger.warning(
        "DEV_MODE is enabled. Auth verification may be skipped. "
        "DO NOT use this setting in production!"
    )
elif not GOOGLE_CLIENT_ID:
    raise RuntimeError("AUTH_GOOGLE_ID environment variable is not set. Service cannot start in production mode.")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database on startup."""
    await init_db()


def _verify_google_token(token: str) -> dict:
    """Verify Google OAuth token and return payload."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    # DEV_MODE: Allow skipping verification
    if DEV_MODE:
        if token.startswith("dev_"):
            return {"sub": "dev-user-123", "email": "dev@example.com", "name": "Dev User"}
        logger.warning("Verifying Google token in DEV_MODE. Production checks apply.")

    try:
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            audience=GOOGLE_CLIENT_ID
        )
        return id_info
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc
    except Exception as exc:
        logger.error(f"Unexpected error verifying token: {exc}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed") from exc


def _extract_bearer_token(authorization: str | None) -> str:
    """Extract token from Authorization header."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing Bearer token")
    return authorization.split(" ", 1)[1]


def _parse_auth_results(auth_results: str) -> dict[str, str]:
    """Parse Authentication-Results header to extract SPF, DKIM, DMARC status."""
    result = {"spf": None, "dkim": None, "dmarc": None}
    
    if not auth_results:
        return result
    
    auth_lower = auth_results.lower()
    
    # Parse SPF
    if "spf=pass" in auth_lower:
        result["spf"] = "PASS"
    elif "spf=fail" in auth_lower or "spf=softfail" in auth_lower:
        result["spf"] = "FAIL"
    elif "spf=neutral" in auth_lower:
        result["spf"] = "NEUTRAL"
    elif "spf=none" in auth_lower:
        result["spf"] = "NONE"
    
    # Parse DKIM
    if "dkim=pass" in auth_lower:
        result["dkim"] = "PASS"
    elif "dkim=fail" in auth_lower:
        result["dkim"] = "FAIL"
    elif "dkim=neutral" in auth_lower:
        result["dkim"] = "NEUTRAL"
    elif "dkim=none" in auth_lower:
        result["dkim"] = "NONE"
    
    # Parse DMARC
    if "dmarc=pass" in auth_lower:
        result["dmarc"] = "PASS"
    elif "dmarc=fail" in auth_lower:
        result["dmarc"] = "FAIL"
    elif "dmarc=none" in auth_lower:
        result["dmarc"] = "NONE"
    
    return result


def _extract_sender_ip(received_headers: list[str]) -> str | None:
    """Extract originating sender IP from Received headers.
    
    Iterates headers in reverse (bottom-to-top) to find the originating IP,
    as the bottommost Received header is added by the first server to receive
    the email and is most likely to contain the actual sender's IP.
    """
    import re
    
    for received in reversed(received_headers):
        # Look for IP patterns in square brackets
        ip_match = re.search(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]', received)
        if ip_match:
            return ip_match.group(1)
    return None


def _extract_attachments(payload: dict) -> str | None:
    """Extract attachment filenames from email payload."""
    attachments = []
    
    def walk_parts(parts):
        for part in parts:
            filename = part.get("filename")
            if filename:
                attachments.append(filename)
            if "parts" in part:
                walk_parts(part["parts"])
    
    if "parts" in payload:
        walk_parts(payload["parts"])
    
    return ", ".join(attachments) if attachments else None


def _parse_email_date(date_str: str) -> datetime | None:
    """Parse email Date header to datetime."""
    from email.utils import parsedate_to_datetime
    
    if not date_str:
        return None
    
    try:
        dt = parsedate_to_datetime(date_str)
        # Convert to naive UTC datetime for PostgreSQL
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def fetch_gmail_messages(access_token: str, limit: int = 20) -> list[dict]:
    """Fetch emails from Gmail API using batch requests for better performance."""
    try:
        creds = Credentials(token=access_token)
        service = build("gmail", "v1", credentials=creds)

        # List messages (include spam/trash for complete view)
        results = service.users().messages().list(userId="me", maxResults=limit, includeSpamTrash=True).execute()
        messages = results.get("messages", [])

        if not messages:
            return []

        email_data = []

        def callback(request_id, response, exception):
            """Callback for batch request processing."""
            if exception:
                logger.error(f"Error fetching message {request_id}: {exception}")
                return
            
            try:
                payload = response.get("payload", {})
                headers = payload.get("headers", [])
                
                # Create a dict for easier header lookup
                headers_dict = {h["name"].lower(): h["value"] for h in headers}
                
                # Essential fields
                subject = headers_dict.get("subject", "(No Subject)")
                sender = headers_dict.get("from", "Unknown")
                recipient = headers_dict.get("to", "Unknown")
                snippet = response.get("snippet", "")
                
                # Timestamp
                date_str = headers_dict.get("date")
                received_at = _parse_email_date(date_str)
                
                # Authentication status
                auth_results = headers_dict.get("authentication-results", "")
                auth_status = _parse_auth_results(auth_results)
                
                # Sender IP from Received headers
                received_headers = [h["value"] for h in headers if h["name"].lower() == "received"]
                sender_ip = _extract_sender_ip(received_headers)
                
                # Attachments
                attachment_info = _extract_attachments(payload)
                
                # Check if email is in SPAM folder
                status = EmailStatus.PENDING
                if "SPAM" in response.get("labelIds", []):
                    status = EmailStatus.SPAM

                email_data.append({
                    "sender": sender,
                    "recipient": recipient,
                    "subject": subject,
                    "body_preview": snippet,
                    "message_id": response["id"],
                    "received_at": received_at,
                    "spf_status": auth_status["spf"],
                    "dkim_status": auth_status["dkim"],
                    "dmarc_status": auth_status["dmarc"],
                    "sender_ip": sender_ip,
                    "attachment_info": attachment_info,
                    "status": status,
                })
            except Exception as e:
                logger.warning(f"Failed to parse message in batch callback: {e}")

        # Process in smaller batches to avoid rate limits (429 Too Many Concurrent Requests)
        # Gmail free tier often limits concurrent requests.
        batch_size = 5
        for i in range(0, len(messages), batch_size):
            batch = service.new_batch_http_request(callback=callback)
            chunk = messages[i : i + batch_size]
            
            for msg in chunk:
                batch.add(service.users().messages().get(userId="me", id=msg["id"], format="full"))
            
            try:
                batch.execute()
            except Exception as e:
                logger.warning(f"Batch execution failed for chunk {i}: {e}")
                continue
            
        return email_data
    except Exception as e:
        logger.error(f"Failed to fetch Gmail messages: {e}")
        return []


async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get or create the current user from Google OAuth token."""
    token = _extract_bearer_token(authorization)
    payload = _verify_google_token(token)
    google_id: str | None = payload.get("sub")
    if not google_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing subject")

    result = await session.exec(select(User).where(User.google_id == google_id))
    user = result.first()
    
    if not user:
        # Auto-provision new user on first login
        email = payload.get("email", "unknown")
        name = payload.get("name")
        logger.info(f"Auto-provisioning new user: {email} (Google ID: {google_id})")
        
        user = User(
            google_id=google_id,
            email=email,
            name=name,
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {email} (id: {user.id})")
        except IntegrityError:
            await session.rollback()
            # Race condition: user created by another request concurrently
            logger.warning(f"User {email} already exists (race condition handled), fetching existing user.")
            result = await session.exec(select(User).where(User.google_id == google_id))
            user = result.first()

    return user


# ============================================================================
# Pydantic Models for API
# ============================================================================

class EmailCreate(SQLModel):
    """Schema for creating an email event."""
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str] = None


class EmailRead(SQLModel):
    """Schema for reading an email event."""
    id: uuid.UUID
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str]
    received_at: Optional[datetime] = None
    
    # Threat Intelligence
    threat_category: Optional[ThreatCategory] = None
    detection_reason: Optional[str] = None
    
    # Security Metadata
    spf_status: Optional[str] = None
    dkim_status: Optional[str] = None
    dmarc_status: Optional[str] = None
    sender_ip: Optional[str] = None
    attachment_info: Optional[str] = None
    
    # Processing
    status: EmailStatus
    risk_score: Optional[int] = None
    risk_tier: Optional[RiskTier] = None
    analysis_result: Optional[dict] = None


class UserRead(SQLModel):
    """Schema for reading user info."""
    id: uuid.UUID
    email: str
    name: Optional[str]


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return user


@app.post("/api/emails", response_model=EmailRead, status_code=status.HTTP_201_CREATED)
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
        body_preview=payload.body_preview,
        status=EmailStatus.PENDING,
    )
    session.add(email)
    await session.commit()
    await session.refresh(email)
    return email


@app.get("/api/emails", response_model=list[EmailRead])
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


@app.post("/api/emails/sync", status_code=status.HTTP_202_ACCEPTED)
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
        for g_email in gmail_emails:
            msg_id = g_email.get("message_id")
            
            # Deduplicate by message_id
            if msg_id:
                existing = await session.exec(select(EmailEvent).where(EmailEvent.message_id == msg_id))
                if existing.first():
                    continue

            email = EmailEvent(
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
            count += 1
            
        if count > 0:
            await session.commit()
            
        return {"status": "synced", "new_messages": count}

    except Exception as e:
        logger.error(f"Error syncing Gmail: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Sync failed")


@app.get("/api/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get email statistics for the current user."""
    from sqlalchemy import func, text
    
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
