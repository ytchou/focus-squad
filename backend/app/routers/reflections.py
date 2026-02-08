"""
Session reflection endpoints for the Session Board feature.

Design doc: output/plan/2026-02-08-session-board-design.md

Endpoints:
- POST /{session_id}/reflections: Save/update a reflection
- GET /{session_id}/reflections: Get all reflections for a session
- GET /diary: Get personal reflection diary (paginated)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import AuthUser, require_auth_from_state
from app.models.reflection import (
    DiaryResponse,
    NotSessionParticipantError,
    ReflectionResponse,
    SaveReflectionRequest,
    SessionNotFoundError,
    SessionReflectionsResponse,
)
from app.services.reflection_service import ReflectionService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Dependency Injection
# =============================================================================

def get_reflection_service() -> ReflectionService:
    """Get ReflectionService instance."""
    return ReflectionService()


def get_user_service() -> UserService:
    """Get UserService instance."""
    return UserService()


# =============================================================================
# Endpoints (static routes before parameterized)
# =============================================================================

@router.get("/diary", response_model=DiaryResponse)
async def get_diary(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
    user_service: UserService = Depends(get_user_service),
) -> DiaryResponse:
    """
    Get the current user's personal reflection diary.

    Returns reflections grouped by session, ordered by most recent first.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return reflection_service.get_diary(
        user_id=profile.id,
        page=page,
        per_page=per_page,
    )


@router.post("/{session_id}/reflections", response_model=ReflectionResponse, status_code=201)
async def save_reflection(
    session_id: str,
    request: SaveReflectionRequest,
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
    user_service: UserService = Depends(get_user_service),
) -> ReflectionResponse:
    """
    Save or update a reflection for a session phase.

    Upserts: if the user already has a reflection for this phase,
    the content is updated.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        return reflection_service.save_reflection(
            session_id=session_id,
            user_id=profile.id,
            phase=request.phase,
            content=request.content,
        )
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except NotSessionParticipantError:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this session",
        )


@router.get("/{session_id}/reflections", response_model=SessionReflectionsResponse)
async def get_session_reflections(
    session_id: str,
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
) -> SessionReflectionsResponse:
    """
    Get all reflections for a session (from all participants).

    Used for board hydration when joining a session.
    """
    try:
        reflections = reflection_service.get_session_reflections(session_id)
        return SessionReflectionsResponse(reflections=reflections)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
