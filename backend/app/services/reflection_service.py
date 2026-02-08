"""
Service for session board reflections.

Design doc: output/plan/2026-02-08-session-board-design.md

Handles:
- Saving reflections (upsert per user/session/phase)
- Loading all reflections for a session (board hydration)
- Loading personal reflection diary (paginated)
"""

import logging
from typing import Optional

from supabase import Client

from app.core.database import get_supabase
from app.models.reflection import (
    DiaryEntry,
    DiaryReflection,
    DiaryResponse,
    NotSessionParticipantError,
    ReflectionPhase,
    ReflectionResponse,
    SessionNotFoundError,
)

logger = logging.getLogger(__name__)

REFLECTION_MAX_LENGTH = 500


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
    ) -> ReflectionResponse:
        """
        Save or update a reflection for a session phase.

        Uses upsert (INSERT ... ON CONFLICT UPDATE) so users can edit
        their reflection for a given phase.

        Validates:
        - Session exists
        - User is a participant in the session
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
    ) -> DiaryResponse:
        """
        Get paginated diary entries for a user.

        Groups reflections by session, ordered by most recent first.
        Each diary entry contains the session date/topic and up to 3
        reflections (setup, break, social).
        """
        offset = (page - 1) * per_page

        # Get distinct sessions that have reflections for this user
        count_result = (
            self.supabase.table("session_reflections")
            .select("session_id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )

        # Deduplicate session count (count returns row count, not distinct sessions)
        session_ids_for_count = list({r["session_id"] for r in count_result.data})
        total_sessions = len(session_ids_for_count)

        # Get reflections joined with session info, paginated by session
        result = (
            self.supabase.table("session_reflections")
            .select("*, sessions(start_time, topic)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        # Group by session
        sessions_map: dict[str, dict] = {}
        for row in result.data:
            sid = row["session_id"]
            if sid not in sessions_map:
                session_data = row.get("sessions") or {}
                sessions_map[sid] = {
                    "session_id": sid,
                    "session_date": session_data.get("start_time"),
                    "session_topic": session_data.get("topic"),
                    "reflections": [],
                }
            sessions_map[sid]["reflections"].append(
                DiaryReflection(
                    phase=ReflectionPhase(row["phase"]),
                    content=row["content"],
                    created_at=row["created_at"],
                )
            )

        # Sort sessions by date descending and paginate
        sorted_sessions = sorted(
            sessions_map.values(),
            key=lambda s: s["session_date"] or "",
            reverse=True,
        )
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
                    reflections=s["reflections"],
                )
            )

        return DiaryResponse(
            items=items,
            total=total_sessions,
            page=page,
            per_page=per_page,
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
