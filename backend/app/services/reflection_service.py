"""
Service for session board reflections and diary.

Design docs:
- Session Board: output/plan/2026-02-08-session-board-design.md
- Session Diary: output/plan/2026-02-09-session-diary-design.md

Handles:
- Saving reflections (upsert per user/session/phase)
- Loading all reflections for a session (board hydration)
- Loading personal reflection diary (paginated, searchable)
- Saving post-session diary notes and tags
- Diary statistics (streak, weekly focus, total sessions)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from app.core.constants import REFLECTION_MAX_LENGTH
from app.core.database import get_supabase
from app.models.reflection import (
    DiaryEntry,
    DiaryNoteResponse,
    DiaryReflection,
    DiaryResponse,
    DiaryStatsResponse,
    NotSessionParticipantError,
    ReflectionPhase,
    ReflectionResponse,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)


class ReflectionService:
    """Service for session reflection CRUD and diary queries."""

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        """Lazy-load Supabase client on first access."""
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Public API
    # =========================================================================

    def save_reflection(
        self,
        session_id: str,
        user_id: str,
        phase: ReflectionPhase,
        content: str,
        display_name: Optional[str] = None,
    ) -> ReflectionResponse:
        """
        Save or update a reflection for a session phase.

        Uses upsert (INSERT ... ON CONFLICT UPDATE) so users can edit
        their reflection for a given phase.

        Validates:
        - Session exists
        - User is a participant in the session

        Args:
            display_name: If provided, used directly instead of querying the DB.
        """
        self._verify_session_exists(session_id)
        self._verify_user_is_participant(session_id, user_id)

        row = {
            "session_id": session_id,
            "user_id": user_id,
            "phase": phase.value,
            "content": content[:REFLECTION_MAX_LENGTH],
            "updated_at": "now()",
        }

        result = (
            self.supabase.table("session_reflections")
            .upsert(row, on_conflict="session_id,user_id,phase")
            .execute()
        )

        record = result.data[0]
        if not display_name:
            display_name = self._get_display_name(user_id)

        return ReflectionResponse(
            id=record["id"],
            session_id=record["session_id"],
            user_id=record["user_id"],
            display_name=display_name,
            phase=ReflectionPhase(record["phase"]),
            content=record["content"],
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def get_session_reflections(self, session_id: str) -> list[ReflectionResponse]:
        """
        Get all reflections for a session (all users, all phases).

        Used for:
        - Board hydration when a late joiner connects
        - Loading existing reflections on page mount
        """
        self._verify_session_exists(session_id)

        result = (
            self.supabase.table("session_reflections")
            .select("*, users(display_name, username)")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .execute()
        )

        reflections = []
        for row in result.data:
            user_data = row.get("users") or {}
            display_name = user_data.get("display_name") or user_data.get("username")

            reflections.append(
                ReflectionResponse(
                    id=row["id"],
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    display_name=display_name,
                    phase=ReflectionPhase(row["phase"]),
                    content=row["content"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )

        return reflections

    def get_diary(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> DiaryResponse:
        """
        Get paginated diary entries for a user.

        Groups reflections by session, ordered by most recent first.
        Each diary entry contains session date/topic, focus minutes,
        up to 3 reflections (setup, break, social), and optional
        post-session note/tags.

        Supports full-text search across reflection content and diary
        notes, plus date range filtering.
        """
        offset = (page - 1) * per_page

        # Get reflections joined with session info
        result = (
            self.supabase.table("session_reflections")
            .select("*, sessions(start_time, topic)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        # Get diary notes for this user
        notes_result = (
            self.supabase.table("diary_notes")
            .select("session_id, note, tags")
            .eq("user_id", user_id)
            .execute()
        )
        notes_map: dict[str, dict] = {}
        for row in notes_result.data:
            notes_map[row["session_id"]] = {
                "note": row.get("note"),
                "tags": row.get("tags", []),
            }

        # Get focus minutes for this user's sessions
        participants_result = (
            self.supabase.table("session_participants")
            .select("session_id, total_active_minutes")
            .eq("user_id", user_id)
            .execute()
        )
        focus_map: dict[str, int] = {}
        for row in participants_result.data:
            focus_map[row["session_id"]] = row.get("total_active_minutes") or 0

        # Group by session
        sessions_map: dict[str, dict] = {}
        for row in result.data:
            sid = row["session_id"]
            if sid not in sessions_map:
                session_data = row.get("sessions") or {}
                note_data = notes_map.get(sid, {})
                sessions_map[sid] = {
                    "session_id": sid,
                    "session_date": session_data.get("start_time"),
                    "session_topic": session_data.get("topic"),
                    "focus_minutes": focus_map.get(sid, 0),
                    "reflections": [],
                    "note": note_data.get("note"),
                    "tags": note_data.get("tags", []),
                }
            sessions_map[sid]["reflections"].append(
                DiaryReflection(
                    phase=ReflectionPhase(row["phase"]),
                    content=row["content"],
                    created_at=row["created_at"],
                )
            )

        # Apply date range filter
        filtered = list(sessions_map.values())
        if date_from:
            filtered = [
                s
                for s in filtered
                if s["session_date"] and s["session_date"] >= date_from.isoformat()
            ]
        if date_to:
            filtered = [
                s
                for s in filtered
                if s["session_date"] and s["session_date"] <= date_to.isoformat()
            ]

        # Apply search filter (case-insensitive across reflections + notes)
        if search:
            search_lower = search.lower()

            def matches_search(session: dict) -> bool:
                for r in session["reflections"]:
                    if search_lower in r.content.lower():
                        return True
                if session.get("note") and search_lower in session["note"].lower():
                    return True
                return False

            filtered = [s for s in filtered if matches_search(s)]

        # Sort sessions by date descending and paginate
        sorted_sessions = sorted(
            filtered,
            key=lambda s: s["session_date"] or "",
            reverse=True,
        )
        total = len(sorted_sessions)
        paginated = sorted_sessions[offset : offset + per_page]

        # Sort reflections within each session by phase order
        phase_order = {"setup": 0, "break": 1, "social": 2}
        items = []
        for s in paginated:
            s["reflections"].sort(key=lambda r: phase_order.get(r.phase.value, 99))
            items.append(
                DiaryEntry(
                    session_id=s["session_id"],
                    session_date=s["session_date"],
                    session_topic=s["session_topic"],
                    focus_minutes=s["focus_minutes"],
                    reflections=s["reflections"],
                    note=s["note"],
                    tags=s["tags"],
                )
            )

        return DiaryResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )

    def save_diary_note(
        self,
        session_id: str,
        user_id: str,
        note: Optional[str],
        tags: list[str],
    ) -> DiaryNoteResponse:
        """
        Save or update a post-session diary note with tags.

        Uses upsert (one note per user per session).
        Validates session exists and user was a participant.
        """
        self._verify_session_exists(session_id)
        self._verify_user_is_participant(session_id, user_id)

        from app.core.constants import DIARY_TAGS

        invalid = [tag for tag in tags if tag not in DIARY_TAGS]
        if invalid:
            raise ValueError(f"Invalid tags: {invalid}")

        row = {
            "session_id": session_id,
            "user_id": user_id,
            "note": note,
            "tags": tags,
            "updated_at": "now()",
        }

        result = (
            self.supabase.table("diary_notes")
            .upsert(row, on_conflict="session_id,user_id")
            .execute()
        )

        record = result.data[0]
        return DiaryNoteResponse(
            session_id=record["session_id"],
            note=record.get("note"),
            tags=record.get("tags", []),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
        )

    def get_diary_stats(self, user_id: str) -> DiaryStatsResponse:
        """
        Get personal diary statistics.

        Returns current streak (consecutive days with sessions),
        weekly focus minutes, and total session count.
        """
        user_result = (
            self.supabase.table("users")
            .select("current_streak, total_focus_minutes, session_count")
            .eq("id", user_id)
            .execute()
        )

        if not user_result.data:
            return DiaryStatsResponse(
                current_streak=0,
                weekly_focus_minutes=0,
                total_sessions=0,
            )

        user_data = user_result.data[0]

        # Calculate weekly focus minutes (Monday-based week)
        now = datetime.now(timezone.utc)
        week_start = now - timedelta(days=now.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        weekly_result = (
            self.supabase.table("session_participants")
            .select("total_active_minutes")
            .eq("user_id", user_id)
            .gte("joined_at", week_start.isoformat())
            .execute()
        )

        weekly_minutes = sum(row.get("total_active_minutes") or 0 for row in weekly_result.data)

        return DiaryStatsResponse(
            current_streak=user_data.get("current_streak") or 0,
            weekly_focus_minutes=weekly_minutes,
            total_sessions=user_data.get("session_count") or 0,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _verify_session_exists(self, session_id: str) -> None:
        """Check that the session exists."""
        result = self.supabase.table("sessions").select("id").eq("id", session_id).execute()
        if not result.data:
            raise SessionNotFoundError(f"Session {session_id} not found")

    def _verify_user_is_participant(self, session_id: str, user_id: str) -> None:
        """Check that the user is a participant in this session."""
        result = (
            self.supabase.table("session_participants")
            .select("id")
            .eq("session_id", session_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise NotSessionParticipantError(
                f"User {user_id} is not a participant in session {session_id}"
            )

    def _get_display_name(self, user_id: str) -> Optional[str]:
        """Fetch display name for a user."""
        result = (
            self.supabase.table("users")
            .select("display_name, username")
            .eq("id", user_id)
            .execute()
        )
        if not result.data:
            return None
        user = result.data[0]
        return user.get("display_name") or user.get("username")
