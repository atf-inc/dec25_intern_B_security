from __future__ import annotations

import hashlib
import logging
import os
import secrets
import sys
from dataclasses import dataclass
from typing import Optional
import uuid

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .database import get_session, init_db
from .models import EmailEvent, EmailStatus, Organisation, RiskTier, User
from .models import UserRole  # noqa: F401 (used in Enum creation)

logger = logging.getLogger(__name__)


def _hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for secure storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    """Generate an API key and return (plaintext_key, hashed_key, prefix).
    
    The plaintext key is shown to the user once. Only the hash is stored.
    """
    plaintext_key = f"pg_{secrets.token_urlsafe(32)}"
    prefix = plaintext_key[:8]  # "pg_" + first 5 chars of token
    hashed_key = _hash_api_key(plaintext_key)
    return plaintext_key, hashed_key, prefix


def _verify_api_key_hash(plaintext_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash."""
    return secrets.compare_digest(_hash_api_key(plaintext_key), stored_hash)


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

app = FastAPI(title="PhishGuard Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_AUDIENCE = os.getenv("CLERK_AUDIENCE")
_jwks_client: Optional[PyJWKClient] = PyJWKClient(CLERK_JWKS_URL) if CLERK_JWKS_URL else None


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


def _decode_clerk_token(token: str) -> dict:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    if _jwks_client:
        try:
            signing_key = _jwks_client.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=CLERK_AUDIENCE if CLERK_AUDIENCE else None,
                options={"verify_aud": bool(CLERK_AUDIENCE)},
            )
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Clerk token") from exc

    # Fallback: decode without signature verification (development only)
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing Bearer token")
    return authorization.split(" ", 1)[1]


@dataclass
class AuthUserContext:
    user: User
    organisation: Organisation


async def get_current_user(
    authorization: str = Header(None),
    session: AsyncSession = Depends(get_session),
) -> AuthUserContext:
    token = _extract_bearer_token(authorization)
    payload = _decode_clerk_token(token)
    clerk_id: str | None = payload.get("sub")
    if not clerk_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clerk token missing subject")

    result = await session.exec(select(User).where(User.clerk_id == clerk_id))
    user = result.first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    org = await session.get(Organisation, user.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organisation not found")

    return AuthUserContext(user=user, organisation=org)


async def require_admin(ctx: AuthUserContext = Depends(get_current_user)) -> AuthUserContext:
    if ctx.user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
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
    id: str
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
    clerk_id: str
    role: UserRole = UserRole.member
    org_id: Optional[uuid.UUID] = None


class UserRead(SQLModel):
    id: uuid.UUID
    email: str
    clerk_id: str
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
    ctx: AuthUserContext = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EmailEvent]:
    query = select(EmailEvent).where(EmailEvent.org_id == ctx.organisation.id).order_by(EmailEvent.created_at.desc())
    if status_filter:
        query = query.where(EmailEvent.status == status_filter)
    query = query.limit(limit).offset(offset)

    result = await session.exec(query)
    return result.all()


@app.post("/api/organizations", response_model=OrganisationCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganisationCreate,
    ctx: AuthUserContext = Depends(require_admin),
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
    ctx: AuthUserContext = Depends(require_admin),
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
    org_id = payload.org_id or ctx.organisation.id
    user = User(
        email=payload.email,
        clerk_id=payload.clerk_id,
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
    target_org = org_id or ctx.organisation.id
    result = await session.exec(select(User).where(User.org_id == target_org))
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
    if user.org_id != ctx.organisation.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify users outside organisation")

    user.role = payload.role
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
