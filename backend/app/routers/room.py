"""
Room API endpoints.

Handles:
- GET / - Get complete room state (auto visitor check)
- PUT /layout - Update room layout
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.models.room import LayoutUpdate, RoomResponse, RoomState
from app.services.room_service import RoomService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_room_service() -> RoomService:
    return RoomService()


def get_user_service() -> UserService:
    return UserService()


@router.get("/", response_model=RoomResponse)
async def get_room_state(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
) -> RoomResponse:
    """Get complete room state including inventory, companions, and visitors."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return room_service.get_room_state(profile.id)


@router.put("/layout", response_model=RoomState)
async def update_room_layout(
    request: Request,
    layout_update: LayoutUpdate,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
) -> RoomState:
    """Update the room layout with item placements."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="User not found")
    return room_service.update_layout(user_id=profile.id, placements=layout_update.placements)
