"""
Companion API endpoints.

Handles:
- GET / - List user's companions
- POST /choose-starter - Choose first companion
- POST /adopt - Adopt a visiting companion
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.room import AdoptRequest, CompanionInfo, StarterChoice
from app.services.companion_service import CompanionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_companion_service() -> CompanionService:
    return CompanionService()


def get_user_service() -> UserService:
    return UserService()


@router.get("/", response_model=list[CompanionInfo])
async def get_companions(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    companion_service: CompanionService = Depends(get_companion_service),
) -> list[CompanionInfo]:
    """Get all companions for the current user."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        return []
    return companion_service.get_companions(profile.id)


@router.post("/choose-starter", response_model=CompanionInfo)
@limiter.limit("5/minute")
async def choose_starter_companion(
    request: Request,
    starter_choice: StarterChoice,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    companion_service: CompanionService = Depends(get_companion_service),
) -> CompanionInfo:
    """Choose a starter companion (first-time only)."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return companion_service.choose_starter(
        user_id=profile.id,
        companion_type=starter_choice.companion_type.value,
    )


@router.post("/adopt", response_model=CompanionInfo)
@limiter.limit("5/minute")
async def adopt_visitor(
    request: Request,
    adopt_request: AdoptRequest,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    companion_service: CompanionService = Depends(get_companion_service),
) -> CompanionInfo:
    """Adopt a visiting companion."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return companion_service.adopt_visitor(
        user_id=profile.id,
        companion_type=adopt_request.companion_type.value,
    )
