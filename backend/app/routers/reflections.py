"""
Session reflection and diary endpoints.

Design docs:
- Session Board: output/plan/2026-02-08-session-board-design.md
- Session Diary: output/plan/2026-02-09-session-diary-design.md

Endpoints (static routes before parameterized):
- GET /diary: Personal reflection diary (paginated, searchable)
- GET /diary/stats: Personal diary statistics
- POST /diary/{session_id}/note: Save post-session note + tags
- POST /{session_id}/reflections: Save/update a reflection
- GET /{session_id}/reflections: Get all reflections for a session
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.gamification import DiaryNoteWithReactionResponse
from app.models.reflection import (
    DiaryResponse,
    DiaryStatsResponse,
    ReflectionResponse,
    SaveDiaryNoteRequest,
    SaveReflectionRequest,
    SessionReflectionsResponse,
)
from app.services.mood_service import MoodService
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


def get_mood_service() -> MoodService:
    """Get MoodService instance."""
    return MoodService()


# =============================================================================
# Endpoints (static routes before parameterized)
# =============================================================================


@router.get("/diary", response_model=DiaryResponse)
async def get_diary(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
    user_service: UserService = Depends(get_user_service),
) -> DiaryResponse:
    """
    Get the current user's personal reflection diary.

    Returns reflections grouped by session, ordered by most recent first.
    Supports full-text search and date range filtering.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    return reflection_service.get_diary(
        user_id=profile.id,
        page=page,
        per_page=per_page,
        search=search,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )


@router.get("/diary/stats", response_model=DiaryStatsResponse)
async def get_diary_stats(
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
    user_service: UserService = Depends(get_user_service),
) -> DiaryStatsResponse:
    """Get personal diary statistics (streak, weekly focus, total sessions)."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    return reflection_service.get_diary_stats(user_id=profile.id)


@router.post(
    "/diary/{session_id}/note",
    response_model=DiaryNoteWithReactionResponse,
    status_code=201,
)
@limiter.limit("30/minute")
async def save_diary_note(
    request: Request,
    session_id: str,
    diary_request: SaveDiaryNoteRequest,
    user: AuthUser = Depends(require_auth_from_state),
    reflection_service: ReflectionService = Depends(get_reflection_service),
    user_service: UserService = Depends(get_user_service),
    mood_service: MoodService = Depends(get_mood_service),
) -> DiaryNoteWithReactionResponse:
    """Save or update a post-session diary note with tags.

    Returns the saved note along with companion reaction data (if the user
    has an active companion and submitted tags that trigger a reaction).
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    note_result = reflection_service.save_diary_note(
        session_id=session_id,
        user_id=profile.id,
        note=diary_request.note,
        tags=diary_request.tags,
    )

    # Compute companion reaction and mood
    companion_reaction = None
    mood = None
    if diary_request.tags:
        companion_reaction = mood_service.get_reaction_for_tags(profile.id, diary_request.tags)
        mood = mood_service.compute_mood(profile.id)

    return DiaryNoteWithReactionResponse(
        session_id=note_result.session_id,
        note=note_result.note,
        tags=note_result.tags,
        created_at=note_result.created_at,
        updated_at=note_result.updated_at,
        companion_reaction=companion_reaction,
        mood=mood,
    )


@router.post("/{session_id}/reflections", response_model=ReflectionResponse, status_code=201)
@limiter.limit("30/minute")
async def save_reflection(
    request: Request,
    session_id: str,
    reflection_request: SaveReflectionRequest,
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

    return reflection_service.save_reflection(
        session_id=session_id,
        user_id=profile.id,
        phase=reflection_request.phase,
        content=reflection_request.content,
        display_name=profile.display_name or profile.username,
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
    reflections = reflection_service.get_session_reflections(session_id)
    return SessionReflectionsResponse(reflections=reflections)
