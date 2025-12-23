import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from apps.api.services.auth import get_current_user
from packages.shared.models import User, UserRead
from packages.shared.database import get_session

logger = logging.getLogger(__name__)

router = APIRouter()

class SaveTokensRequest(BaseModel):
    email: str
    google_id: str
    name: str
    refresh_token: str
    access_token: str  # Not saved, just for validation


@router.post("/save-tokens")
async def save_tokens(
    request: SaveTokensRequest,
    session: AsyncSession = Depends(get_session)
):
    """Save refresh_token to database when user logs in via NextAuth."""
    # Find or create user
    query = select(User).where(User.email == request.email)
    result = await session.exec(query)
    user = result.first()
    
    if not user:
        # Create new user
        logger.info('Creating new user: %s', request.email)
        user = User(
            email=request.email,
            google_id=request.google_id,
            name=request.name,
            refresh_token=request.refresh_token
        )
        session.add(user)
    else:
        # Update existing user's refresh_token
        logger.info('Updating refresh token for user: %s', request.email)
        user.refresh_token = request.refresh_token
        user.google_id = request.google_id
        user.name = request.name
        session.add(user)
    
    await session.commit()
    await session.refresh(user)
    
    logger.info('Successfully saved tokens for user: %s (id=%s)', request.email, user.id)
    return {"status": "success", "user_id": str(user.id)}


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return user
