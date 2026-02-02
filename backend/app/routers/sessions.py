from datetime import datetime
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TableMode(str, Enum):
    FORCED_AUDIO = "forced_audio"
    QUIET = "quiet"


class SessionPhase(str, Enum):
    SETUP = "setup"
    WORK_1 = "work_1"
    BREAK = "break"
    WORK_2 = "work_2"
    SOCIAL = "social"
    ENDED = "ended"


class SessionFilters(BaseModel):
    """Filters for finding a table."""

    topic: Optional[str] = None
    mode: Optional[TableMode] = None
    language: Optional[str] = None  # "en" or "zh-TW"


class SessionInfo(BaseModel):
    """Session information response."""

    id: str
    start_time: datetime
    mode: TableMode
    topic: Optional[str]
    current_phase: SessionPhase
    participants: list[dict]
    livekit_token: Optional[str] = None


class QuickMatchRequest(BaseModel):
    """Request to quick match into a session."""

    filters: Optional[SessionFilters] = None


class QuickMatchResponse(BaseModel):
    """Response from quick match."""

    session_id: str
    start_time: datetime
    livekit_token: str


@router.post("/quick-match", response_model=QuickMatchResponse)
async def quick_match(request: QuickMatchRequest):
    """Quick match into the next available session slot."""
    # TODO: Implement matching logic
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/upcoming")
async def get_upcoming_sessions():
    """Get upcoming session slots the user is matched to."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get session details."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{session_id}/leave")
async def leave_session(session_id: str):
    """Leave a session early."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{session_id}/rate")
async def rate_participant(session_id: str, participant_id: str, rating: str):
    """Rate a session participant (green/red/skip)."""
    # TODO: Implement peer review
    raise HTTPException(status_code=501, detail="Not implemented")
