from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import AuthUser, get_current_user

router = APIRouter()


class UserProfile(BaseModel):
    """User profile response model."""
    id: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_config: Optional[Dict] = None
    reliability_score: float = 100.0
    total_focus_hours: float = 0.0
    session_count: int = 0
    current_streak: int = 0


class UserProfileUpdate(BaseModel):
    """User profile update request model."""
    username: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_config: Optional[Dict] = None
    social_links: Optional[Dict] = None
    study_interests: Optional[List[str]] = None


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: AuthUser = Depends(get_current_user)):
    """Get current user's profile."""
    # TODO: Implement database lookup using current_user.auth_id
    raise HTTPException(status_code=501, detail="Not implemented")


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    update: UserProfileUpdate,
    current_user: AuthUser = Depends(get_current_user)
):
    """Update current user's profile."""
    # TODO: Implement database update using current_user.auth_id
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Get a user's public profile."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")
