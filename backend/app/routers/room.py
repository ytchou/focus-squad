"""
Room API endpoints.

Handles:
- GET / - Get complete room state (auto visitor check)
- PUT /layout - Update room layout
- GET /gifts - Get unseen gift notifications
- POST /gifts/seen - Mark gifts as seen
- GET /partner/{user_id} - Get a partner's room (read-only)

IMPORTANT: Static routes (/gifts, /gifts/seen) are registered BEFORE
the parameterized route (/partner/{user_id}) to avoid FastAPI catch-all.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.room import (
    GiftNotification,
    LayoutUpdate,
    MarkGiftsSeenRequest,
    PartnerRoomResponse,
    RoomResponse,
    RoomState,
)
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
        raise HTTPException(status_code=404, detail="User not found")
    return room_service.get_room_state(profile.id)


@router.put("/layout", response_model=RoomState)
@limiter.limit("15/minute")
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
        raise HTTPException(status_code=404, detail="User not found")
    return room_service.update_layout(user_id=profile.id, placements=layout_update.placements)


# --- Gift notification endpoints (BEFORE parameterized route) ---


@router.get("/gifts", response_model=list[GiftNotification])
async def get_unseen_gifts(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
) -> list[GiftNotification]:
    """Get unseen gift notifications for toast display on room load."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return room_service.get_unseen_gifts(profile.id)


@router.post("/gifts/seen")
async def mark_gifts_seen(
    request: Request,
    body: MarkGiftsSeenRequest,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
) -> dict:
    """Mark gift items as seen (dismisses toast notifications)."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    room_service.mark_gifts_seen(profile.id, body.inventory_ids)
    return {"ok": True}


# --- Partner room endpoint (parameterized - must be LAST) ---


@router.get("/partner/{user_id}", response_model=PartnerRoomResponse)
async def get_partner_room(
    user_id: str,
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    room_service: RoomService = Depends(get_room_service),
) -> PartnerRoomResponse:
    """Get a partner's room in read-only mode."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return room_service.get_partner_room(viewer_id=profile.id, owner_id=user_id)
