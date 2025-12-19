"""MailShieldAI Dashboard API - Single User Architecture."""

from __future__ import annotations

import logging
import os
import sys
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.auth.transport import requests
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session, init_db
from models import EmailEvent, EmailStatus, RiskTier, User

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


def fetch_gmail_messages(access_token: str, limit: int = 10) -> list[dict]:
    """Fetch emails from Gmail API using the provided access token."""
    try:
        creds = Credentials(token=access_token)
        service = build("gmail", "v1", credentials=creds)

        # List messages
        results = service.users().messages().list(userId="me", maxResults=limit).execute()
        messages = results.get("messages", [])

        email_data = []
        for msg in messages:
            # Get full message details
            msg_detail = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
            
            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
            recipient = next((h["value"] for h in headers if h["name"] == "To"), "Unknown")
            snippet = msg_detail.get("snippet", "")

            email_data.append({
                "sender": sender,
                "recipient": recipient,
                "subject": subject,
                "body_preview": snippet,
                "message_id": msg["id"],
                "status": EmailStatus.pending
            })
            
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
        await session.commit()
        await session.refresh(user)
        logger.info(f"Created new user: {email} (id: {user.id})")

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
    status: EmailStatus
    risk_score: Optional[int]
    risk_tier: Optional[RiskTier]
    analysis_result: Optional[dict]


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
        status=EmailStatus.pending,
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
    """Sync emails from Gmail."""
    try:
        # Fetch recent messages
        gmail_emails = fetch_gmail_messages(x_google_token, limit=20)
        
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
                status=EmailStatus.pending,
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
    # Total emails
    total_result = await session.exec(
        select(EmailEvent).where(EmailEvent.user_id == user.id)
    )
    total_emails = len(total_result.all())
    
    # Emails by risk tier
    safe_result = await session.exec(
        select(EmailEvent).where(
            EmailEvent.user_id == user.id,
            EmailEvent.risk_tier == RiskTier.safe
        )
    )
    safe_count = len(safe_result.all())
    
    cautious_result = await session.exec(
        select(EmailEvent).where(
            EmailEvent.user_id == user.id,
            EmailEvent.risk_tier == RiskTier.cautious
        )
    )
    cautious_count = len(cautious_result.all())
    
    threat_result = await session.exec(
        select(EmailEvent).where(
            EmailEvent.user_id == user.id,
            EmailEvent.risk_tier == RiskTier.threat
        )
    )
    threat_count = len(threat_result.all())
    
    return {
        "total_emails": total_emails,
        "safe": safe_count,
        "cautious": cautious_count,
        "threat": threat_count,
        "pending": total_emails - safe_count - cautious_count - threat_count,
    }
