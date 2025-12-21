
import logging
import os
import sys

from fastapi import Depends, Header, HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from packages.shared.database import get_session
from packages.shared.models import User

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("AUTH_GOOGLE_ID")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")

if not GOOGLE_CLIENT_ID and not DEV_MODE:
    # This check happens at import time, usually fine for services
    logger.warning("AUTH_GOOGLE_ID environment variable is not set. Service may not function correctly in production.")

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


def _mask_email(email: str) -> str:
    """Mask email address for logging to protect PII."""
    if not email or "@" not in email:
        return "********"
    try:
        local, domain = email.rsplit("@", 1)
        if len(local) > 1:
            return f"{local[0]}****@{domain}"
        return f"****@{domain}"
    except Exception:
        return "********"


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
        logger.info(f"Auto-provisioning new user: {_mask_email(email)} (Google ID: {google_id})")
        
        user = User(
            google_id=google_id,
            email=email,
            name=name,
        )
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
            logger.info(f"Created new user: {_mask_email(email)} (id: {user.id})")
        except IntegrityError:
            await session.rollback()
            # Race condition: user created by another request concurrently
            logger.warning(f"User {_mask_email(email)} already exists (race condition handled), fetching existing user.")
            result = await session.exec(select(User).where(User.google_id == google_id))
            user = result.first()

    return user
