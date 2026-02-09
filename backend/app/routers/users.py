"""
User profile management endpoints.

Endpoints:
- GET /me: Get current user's profile (creates on first OAuth login)
- PATCH /me: Update current user's profile
- GET /{user_id}: Get a user's public profile
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, require_auth_from_state
from app.models.user import (
    DeleteAccountResponse,
    UserProfile,
    UserProfileUpdate,
    UserPublicProfile,
)
from app.services.user_service import (
    UsernameConflictError,
    UserNotFoundError,
    UserService,
)

router = APIRouter()


def get_user_service() -> UserService:
    """Dependency to get UserService instance."""
    return UserService()


@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
) -> UserProfile:
    """
    Get current user's profile.

    On first OAuth login, creates user with:
    - Auto-generated username from email
    - Associated credits record (Free tier, 2 credits)
    - Associated furniture_essence record (0 balance)
    - Default notification preferences for all event types
    """
    # Upsert: create if not exists
    profile, _ = user_service.create_user_if_not_exists(
        auth_id=current_user.auth_id,
        email=current_user.email,
    )

    return profile


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    update: UserProfileUpdate,
    current_user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
) -> UserProfile:
    """
    Update current user's profile.

    Supports partial updates. Only provided fields are updated.
    Username changes are validated for uniqueness.

    Raises:
        400: If username is already taken
        404: If user not found (shouldn't happen with valid auth)
    """
    try:
        return user_service.update_user_profile(
            auth_id=current_user.auth_id,
            update=update,
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except UsernameConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/me", response_model=DeleteAccountResponse)
async def delete_my_account(
    current_user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
) -> DeleteAccountResponse:
    """
    Soft-delete current user's account.

    Schedules account for deletion in 30 days. User can cancel
    by signing back in before the scheduled date.
    """
    try:
        scheduled = user_service.soft_delete_user(current_user.auth_id)
        return DeleteAccountResponse(
            message="Account scheduled for deletion in 30 days. Sign back in to cancel.",
            deletion_scheduled_at=scheduled,
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )


@router.get("/{user_id}", response_model=UserPublicProfile)
async def get_user_profile(
    user_id: str,
    user_service: UserService = Depends(get_user_service),
) -> UserPublicProfile:
    """
    Get a user's public profile.

    Returns limited information (no email, settings, or private data).
    This endpoint does not require authentication.
    """
    profile = user_service.get_public_profile(user_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return profile
