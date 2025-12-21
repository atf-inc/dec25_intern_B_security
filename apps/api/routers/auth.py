from fastapi import APIRouter, Depends
from apps.api.services.auth import get_current_user
from packages.shared.models import User, UserRead

router = APIRouter()

@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return user
