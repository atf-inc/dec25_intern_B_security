from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from typing import Optional
import uuid

from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google.auth.transport import requests
from googleapiclient.discovery import build
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session, init_db
from models import EmailEvent, EmailStatus, Organisation, RiskTier, User, UserRole

logger = logging.getLogger(__name__)


def _hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    """Generate an API key and return (plaintext_key, hashed_key, prefix).
    
    The plaintext key is shown to the user once. Only the hash is stored.
    """
    plaintext_key = f"sk_{secrets.token_urlsafe(32)}"
    prefix = plaintext_key[:8]  # First 8 chars of plaintext_key (e.g., "sk_XXXXX")
    hashed_key = _hash_api_key(plaintext_key)
    return plaintext_key, hashed_key, prefix


app = FastAPI(title="PhishGuard Dashboard API", version="0.1.0")

# CORS configuration - validate origins
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
_cors_origins = [o.strip() for o in _cors_origins if o.strip()]
if not _cors_origins:
    raise RuntimeError("CORS_ALLOW_ORIGINS must be set (comma-separated list of allowed origins)")
if "*" in _cors_origins:
    raise RuntimeError("Wildcard '*' in CORS_ALLOW_ORIGINS is not allowed with credentials")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    await init_db()


def _verify_google_token(token: str) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    # DEV_MODE: Allow skipping verification (simulating test users)
    if DEV_MODE:
        # In dev mode, if token starts with "dev_", extract the google_id from the rest
        if token.startswith("dev_"):
            google_id = token[4:]  # Strip "dev_" prefix to get google_id
            return {"sub": google_id, "email": f"{google_id}@example.com"}
        # Fallback to trying to verify, but maybe log warning
        logger.warning("Verifying Google token in DEV_MODE. Production checks apply.")

    try:
        # Verify the token against Google's public keys
        # aud argument checks the Client ID
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            audience=GOOGLE_CLIENT_ID
        )
        return id_info
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc


def _extract_bearer_token(authorization: str | None) -> str:
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


@dataclass
class AuthUserContext:
    user: User
    organisation: Organisation


async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> AuthUserContext:
    token = _extract_bearer_token(authorization)
    payload = _verify_google_token(token)
    google_id: str | None = payload.get("sub")
    if not google_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing subject")

    result = await session.exec(select(User).where(User.google_id == google_id))
    user = result.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    org = await session.get(Organisation, user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organisation not found")

    return AuthUserContext(user=user, organisation=org)


async def require_admin(ctx: AuthUserContext = Depends(get_current_user)) -> AuthUserContext:
    if ctx.user.role not in (UserRole.admin, UserRole.platform_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return ctx


async def require_platform_admin(ctx: AuthUserContext = Depends(get_current_user)) -> AuthUserContext:
    if ctx.user.role != UserRole.platform_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin access required")
    return ctx


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Organisation:
    """Verify API key by hashing and comparing against stored hash."""
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Key")

    # Hash the provided key and look up by hash
    key_hash = _hash_api_key(x_api_key)
    result = await session.exec(select(Organisation).where(Organisation.api_key_hash == key_hash))
    org = result.first()
    if not org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return org


async def resolve_ingest_context(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Organisation:
    api_key = request.headers.get("x-api-key")
    authorization = request.headers.get("authorization")

    if api_key:
        # Hash the provided key and look up by hash
        key_hash = _hash_api_key(api_key)
        result = await session.exec(select(Organisation).where(Organisation.api_key_hash == key_hash))
        org = result.first()
        if not org:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return org

    if authorization:
        ctx = await get_current_user(authorization=authorization, session=session)
        return ctx.organisation

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication")


class EmailCreate(SQLModel):
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str] = None


class EmailRead(SQLModel):
    id: uuid.UUID
    sender: str
    recipient: str
    subject: str
    body_preview: Optional[str]
    status: EmailStatus
    risk_score: Optional[int]
    risk_tier: Optional[RiskTier]
    analysis_result: Optional[dict]


class OrganisationCreate(SQLModel):
    name: str
    domain: str


class OrganisationRead(SQLModel):
    """Organisation data for listing (api_key is never exposed after creation)."""
    id: uuid.UUID
    name: str
    domain: str
    api_key_prefix: str  # Only show prefix for identification


class OrganisationCreateResponse(SQLModel):
    """Response when creating an organisation. Contains the plaintext API key (shown once only)."""
    id: uuid.UUID
    name: str
    domain: str
    api_key: str  # Plaintext key - only shown once at creation time
    api_key_prefix: str


class UserCreate(SQLModel):
    email: str
    google_id: str
    role: UserRole = UserRole.member
    org_id: Optional[uuid.UUID] = None


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    google_id: str
    role: UserRole
    org_id: uuid.UUID


class UserRoleUpdate(SQLModel):
    role: UserRole


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/emails", response_model=EmailRead, status_code=status.HTTP_201_CREATED)
async def ingest_email(
    payload: EmailCreate,
    org: Organisation = Depends(resolve_ingest_context),
    session: AsyncSession = Depends(get_session),
) -> EmailEvent:
    email = EmailEvent(
        org_id=org.id,
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
    x_google_token: Optional[str] = Header(None, alias="X-Google-Token"),
    ctx: AuthUserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailEvent]:
    query = select(EmailEvent).where(EmailEvent.org_id == ctx.organisation.id).order_by(EmailEvent.created_at.desc())
    if status_filter:
        query = query.where(EmailEvent.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await session.exec(query)
    return result.all()


@app.post("/api/emails/sync", status_code=status.HTTP_202_ACCEPTED)
async def sync_emails(
    x_google_token: str = Header(..., alias="X-Google-Token"),
    ctx: AuthUserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Trigger background sync of emails from Gmail."""
    try:
        # Fetch recent messages
        gmail_emails = fetch_gmail_messages(x_google_token, limit=20)
        
        count = 0
        for g_email in gmail_emails:
            # Deduplicate by message_id if available, or fall back to simplistic check
            # Real Gmail API returns an 'id' which is persistent.
            # fetch_gmail_messages currently returns a dict constructed manually.
            # We should update fetch_gmail_messages to include 'id' -> 'message_id'
            
            # Assuming fetch_gmail_messages returns 'message_id' (we need to update it too)
            # For now, let's assume one was added or we use a heuristic
            msg_id = g_email.get("message_id")
            
            if msg_id:
                existing = await session.exec(select(EmailEvent).where(EmailEvent.message_id == msg_id))
                if existing.first():
                    continue

            email = EmailEvent(
                org_id=ctx.organisation.id,
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


@app.post("/api/organizations", response_model=OrganisationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganisationCreate,
    ctx: AuthUserContext = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> OrganisationCreateResponse:
    # Generate API key - plaintext shown once, only hash stored
    plaintext_key, hashed_key, prefix = _generate_api_key()
    
    org = Organisation(
        name=payload.name,
        domain=payload.domain,
        api_key_hash=hashed_key,
        api_key_prefix=prefix,
    )
    session.add(org)
    await session.commit()
    await session.refresh(org)
    
    # Return response with plaintext key (only time it's visible)
    return OrganisationCreateResponse(
        id=org.id,
        name=org.name,
        domain=org.domain,
        api_key=plaintext_key,
        api_key_prefix=prefix,
    )


@app.get("/api/organizations", response_model=list[OrganisationRead])
async def list_organizations(
    ctx: AuthUserContext = Depends(require_platform_admin),
    session: AsyncSession = Depends(get_session),
) -> list[Organisation]:
    result = await session.exec(select(Organisation))
    return result.all()


@app.post("/api/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    ctx: AuthUserContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    if ctx.user.role == UserRole.platform_admin:
        # Platform admin can create users for any org (default to their own)
        org_id = payload.org_id or ctx.organisation.id
    else:
        # Regular admin can only create users for their own org
        if payload.org_id and payload.org_id != ctx.organisation.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Cannot create users for other organisations"
            )
        org_id = ctx.organisation.id

    user = User(
        email=payload.email,
        google_id=payload.google_id,
        role=payload.role,
        org_id=org_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.get("/api/users", response_model=list[UserRead])
async def list_users(
    org_id: Optional[uuid.UUID] = None,
    ctx: AuthUserContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[User]:
    if ctx.user.role == UserRole.platform_admin:
        # Platform admin can filter by org or see all
        if org_id:
            query = select(User).where(User.org_id == org_id)
        else:
            query = select(User)
    else:
        # Regular admin restricted to own org
        if org_id and org_id != ctx.organisation.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Cannot list users of other organisations"
            )
        query = select(User).where(User.org_id == ctx.organisation.id)

    result = await session.exec(query)
    return result.all()


@app.patch("/api/users/{user_id}/role", response_model=UserRead)
async def update_user_role(
    user_id: uuid.UUID,
    payload: UserRoleUpdate,
    ctx: AuthUserContext = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Check permissions: platform_admin can edit anyone; regular admin only their own org
    if ctx.user.role != UserRole.platform_admin and user.org_id != ctx.organisation.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify users outside organisation")

    user.role = payload.role
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
