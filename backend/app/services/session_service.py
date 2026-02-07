"""
Session service for table management and matching.

Handles:
- Quick-match session finding/creation
- Participant management (join/leave)
- Session phase calculation
- LiveKit token generation
- AI companion seat filling
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from livekit import api
from supabase import Client

from app.core.config import get_settings
from app.core.database import get_supabase
from app.models.session import (
    ParticipantType,
    SessionFilters,
    SessionPhase,
    TableMode,
)

# =============================================================================
# Exceptions
# =============================================================================


class SessionServiceError(Exception):
    """Base exception for session service errors."""

    pass


class SessionNotFoundError(SessionServiceError):
    """Session not found."""

    pass


class SessionFullError(SessionServiceError):
    """Session has no available seats."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session {session_id} is full (4/4 seats taken)")


class AlreadyInSessionError(SessionServiceError):
    """User is already in this session."""

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is already in session {session_id}")


class SessionPhaseError(SessionServiceError):
    """Operation not allowed in current session phase."""

    def __init__(self, session_id: str, current_phase: str, required_phase: str = "setup"):
        self.session_id = session_id
        self.current_phase = current_phase
        self.required_phase = required_phase
        super().__init__(
            f"Session {session_id} is in {current_phase} phase, requires {required_phase}"
        )


# =============================================================================
# Session Service
# =============================================================================


class SessionService:
    """Service for session matching and management."""

    # Session timing constants (in minutes)
    SESSION_DURATION = 55
    PHASE_DURATIONS = {
        SessionPhase.SETUP: 3,  # 0-3 min
        SessionPhase.WORK_1: 25,  # 3-28 min
        SessionPhase.BREAK: 2,  # 28-30 min
        SessionPhase.WORK_2: 20,  # 30-50 min
        SessionPhase.SOCIAL: 5,  # 50-55 min
    }

    # Phase boundaries (cumulative minutes from start)
    PHASE_BOUNDARIES = {
        SessionPhase.SETUP: (0, 3),
        SessionPhase.WORK_1: (3, 28),
        SessionPhase.BREAK: (28, 30),
        SessionPhase.WORK_2: (30, 50),
        SessionPhase.SOCIAL: (50, 55),
    }

    MAX_PARTICIPANTS = 4
    MIN_PARTICIPANTS_TO_START = 2
    SLOT_SKIP_THRESHOLD_MINUTES = 3  # Skip slot if less than 3 min away

    # AI companion names
    AI_COMPANION_NAMES = ["Focus Fox", "Study Owl", "Calm Cat", "Zen Panda"]

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Time Slot Calculation
    # =========================================================================

    def calculate_next_slot(self) -> datetime:
        """
        Calculate the next available :00 or :30 time slot.

        Rules:
        - Sessions start at :00 or :30 only
        - If within 3 minutes of the next slot, skip to the following slot

        Returns:
            datetime: Next available slot time (UTC)
        """
        now = datetime.now(timezone.utc)

        # Determine the next :00 or :30 boundary
        if now.minute < 30:
            next_slot = now.replace(minute=30, second=0, microsecond=0)
        else:
            next_slot = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

        # If within threshold of next slot, skip to the following slot
        time_until_slot = (next_slot - now).total_seconds() / 60
        if time_until_slot < self.SLOT_SKIP_THRESHOLD_MINUTES:
            # Skip to next slot (30 minutes later)
            next_slot = next_slot + timedelta(minutes=30)

        return next_slot

    # =========================================================================
    # Session Retrieval
    # =========================================================================

    def get_session_by_id(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch session by ID with participants.

        Args:
            session_id: Session UUID

        Returns:
            Session data dict or None if not found
        """
        result = self.supabase.table("sessions").select("*").eq("id", session_id).execute()

        if not result.data:
            return None

        session = result.data[0]

        # Fetch participants
        participants_result = (
            self.supabase.table("session_participants")
            .select("*, users(id, username, display_name, avatar_config)")
            .eq("session_id", session_id)
            .is_("left_at", "null")
            .execute()
        )

        session["participants"] = participants_result.data or []
        session["available_seats"] = self.MAX_PARTICIPANTS - len(session["participants"])

        return session

    def get_user_sessions(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get upcoming sessions the user is participating in.

        Args:
            user_id: Internal user UUID

        Returns:
            List of session data dicts
        """
        # Find sessions where user is an active participant
        result = (
            self.supabase.table("session_participants")
            .select("seat_number, sessions(*)")
            .eq("user_id", user_id)
            .is_("left_at", "null")
            .neq("sessions.current_phase", "ended")
            .execute()
        )

        sessions = []
        for row in result.data or []:
            if row.get("sessions"):
                session = row["sessions"]
                session["my_seat_number"] = row["seat_number"]

                # Count participants
                count_result = (
                    self.supabase.table("session_participants")
                    .select("id", count="exact")
                    .eq("session_id", session["id"])
                    .is_("left_at", "null")
                    .execute()
                )
                session["participant_count"] = count_result.count or 0
                sessions.append(session)

        return sessions

    def get_user_session_at_time(
        self,
        user_id: str,
        start_time: datetime,
    ) -> Optional[dict[str, Any]]:
        """
        Check if user already has a session at a specific time slot.

        Args:
            user_id: User UUID
            start_time: Session start time to check

        Returns:
            Session data dict if user has a session, None otherwise
        """
        result = (
            self.supabase.table("session_participants")
            .select("sessions(*)")
            .eq("user_id", user_id)
            .eq("sessions.start_time", start_time.isoformat())
            .is_("left_at", "null")
            .execute()
        )

        if result.data:
            for row in result.data:
                session = row.get("sessions")
                if session:
                    return session

        return None

    # =========================================================================
    # Session Matching
    # =========================================================================

    def find_matching_session(
        self,
        filters: SessionFilters,
        start_time: datetime,
    ) -> Optional[dict[str, Any]]:
        """
        Find an existing session matching the filters with available seats.

        Args:
            filters: Session filters (mode, topic, language)
            start_time: Target start time

        Returns:
            Session data dict or None if no match
        """
        query = (
            self.supabase.table("sessions")
            .select("*, session_participants(count)")
            .eq("start_time", start_time.isoformat())
            .eq("current_phase", "setup")  # Only match sessions in setup phase
        )

        # Apply filters
        if filters.mode:
            query = query.eq("mode", filters.mode.value)

        if filters.topic:
            query = query.eq("topic", filters.topic)

        if filters.language:
            query = query.eq("language", filters.language)

        result = query.execute()

        if not result.data:
            return None

        # Filter for sessions with available seats (< 4 participants)
        # Note: PostgREST doesn't support WHERE on embedded aggregates
        for session in result.data:
            participant_count = session.get("session_participants", [{}])[0].get("count", 0)
            if participant_count < self.MAX_PARTICIPANTS:
                return session

        return None

    def create_session(
        self,
        mode: TableMode,
        topic: Optional[str],
        language: str,
        start_time: datetime,
    ) -> dict[str, Any]:
        """
        Create a new session.

        Args:
            mode: Table audio mode
            topic: Optional study topic
            language: Language preference (en, zh-TW)
            start_time: Session start time

        Returns:
            Created session data dict
        """
        end_time = start_time + timedelta(minutes=self.SESSION_DURATION)
        room_name = f"focus-{uuid.uuid4().hex[:12]}"

        session_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "mode": mode.value,
            "topic": topic,
            "language": language,
            "current_phase": SessionPhase.SETUP.value,
            "phase_started_at": start_time.isoformat(),
            "livekit_room_name": room_name,
        }

        result = self.supabase.table("sessions").insert(session_data).execute()

        if not result.data:
            raise SessionServiceError("Failed to create session")

        return result.data[0]

    # =========================================================================
    # Participant Management
    # =========================================================================

    def add_participant(
        self,
        session_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Add a human participant to a session atomically (idempotent).

        Uses PostgreSQL RPC for atomic operation with:
        - Phase lock (only during setup phase)
        - Row-level locking to prevent race conditions
        - Idempotent handling for already-active users

        Args:
            session_id: Session UUID
            user_id: User UUID

        Returns:
            Participant data dict with participant_id, seat_number, already_active

        Raises:
            SessionFullError: If session has 4 active participants
            SessionPhaseError: If session is not in setup phase
            SessionNotFoundError: If session does not exist
        """
        try:
            result = self.supabase.rpc(
                "atomic_add_participant",
                {"p_session_id": session_id, "p_user_id": user_id},
            ).execute()
        except Exception as e:
            error_msg = str(e)
            if "SESSION_FULL" in error_msg:
                raise SessionFullError(session_id)
            elif "SESSION_PHASE_ERROR" in error_msg:
                # Extract phase from error message
                phase = "unknown"
                if "in " in error_msg and " phase" in error_msg:
                    phase = error_msg.split("in ")[1].split(" phase")[0]
                raise SessionPhaseError(session_id, phase)
            elif "SESSION_NOT_FOUND" in error_msg:
                raise SessionNotFoundError(f"Session {session_id} not found")
            raise SessionServiceError(f"Failed to add participant: {error_msg}")

        if not result.data:
            raise SessionServiceError("Failed to add participant: no data returned")

        row = result.data[0]
        return {
            "id": row["participant_id"],
            "seat_number": row["seat_number"],
            "already_active": row["already_active"],
            "session_id": session_id,
            "user_id": user_id,
            "participant_type": ParticipantType.HUMAN.value,
        }

    def remove_participant(
        self,
        session_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Remove a participant from a session (mark as left).

        Args:
            session_id: Session UUID
            user_id: User UUID
            reason: Optional reason for leaving
        """
        now = datetime.now(timezone.utc)

        self.supabase.table("session_participants").update({"left_at": now.isoformat()}).eq(
            "session_id", session_id
        ).eq("user_id", user_id).execute()

    # =========================================================================
    # AI Companions
    # =========================================================================

    def add_ai_companions(
        self,
        session_id: str,
        count: int,
    ) -> list[dict[str, Any]]:
        """
        Add AI companions to fill empty seats.

        Args:
            session_id: Session UUID
            count: Number of AI companions to add

        Returns:
            List of created AI companion participant records
        """
        # Get taken seats
        participants = (
            self.supabase.table("session_participants")
            .select("seat_number")
            .eq("session_id", session_id)
            .is_("left_at", "null")
            .execute()
        )

        taken_seats = {p["seat_number"] for p in (participants.data or [])}
        available_seats = [i for i in range(1, 5) if i not in taken_seats]

        companions = []
        for i, seat in enumerate(available_seats[:count]):
            name = self.AI_COMPANION_NAMES[i % len(self.AI_COMPANION_NAMES)]

            companion_data = {
                "session_id": session_id,
                "user_id": None,
                "participant_type": ParticipantType.AI_COMPANION.value,
                "seat_number": seat,
                "ai_companion_name": name,
                "ai_companion_avatar": {"type": "ai", "style": name.lower().replace(" ", "_")},
            }

            result = self.supabase.table("session_participants").insert(companion_data).execute()

            if result.data:
                companions.append(result.data[0])

        return companions

    # =========================================================================
    # Phase Calculation
    # =========================================================================

    def calculate_current_phase(self, session: dict[str, Any]) -> SessionPhase:
        """
        Calculate the current phase based on elapsed time.

        Args:
            session: Session data dict with start_time

        Returns:
            Current SessionPhase
        """
        start_time_str = session["start_time"]
        if isinstance(start_time_str, str):
            # Parse ISO format
            if start_time_str.endswith("Z"):
                start_time_str = start_time_str[:-1] + "+00:00"
            start_time = datetime.fromisoformat(start_time_str)
        else:
            start_time = start_time_str

        now = datetime.now(timezone.utc)
        elapsed_minutes = (now - start_time).total_seconds() / 60

        # Determine phase based on elapsed time
        for phase, (start, end) in self.PHASE_BOUNDARIES.items():
            if start <= elapsed_minutes < end:
                return phase

        # Session has ended
        return SessionPhase.ENDED

    # =========================================================================
    # LiveKit Integration
    # =========================================================================

    def generate_livekit_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
    ) -> str:
        """
        Generate a LiveKit access token for a participant.

        Args:
            room_name: LiveKit room name
            participant_identity: Unique participant identifier (user_id)
            participant_name: Display name for the participant

        Returns:
            JWT access token string (or placeholder in dev mode)
        """
        settings = get_settings()

        # Return placeholder token if LiveKit not configured (dev mode)
        if not settings.livekit_api_key or settings.livekit_api_key == "your-livekit-api-key":
            return "dev-placeholder-token"

        token = api.AccessToken(
            settings.livekit_api_key,
            settings.livekit_api_secret,
        )

        token.with_identity(participant_identity)
        token.with_name(participant_name)

        # Grant room access
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )

        # Set token expiry (2 hours)
        token.with_ttl(timedelta(hours=2))

        return token.to_jwt()

    # =========================================================================
    # High-Level Operations
    # =========================================================================

    def find_or_create_session(
        self,
        filters: SessionFilters,
        start_time: datetime,
        user_id: str,
    ) -> tuple[dict[str, Any], int]:
        """
        Find a matching session or create a new one, and add the user.

        Args:
            filters: Session filters
            start_time: Target start time
            user_id: User to add as participant

        Returns:
            Tuple of (session_data, seat_number)
        """
        # Try to find existing session
        session = self.find_matching_session(filters, start_time)

        if not session:
            # Create new session
            session = self.create_session(
                mode=filters.mode or TableMode.FORCED_AUDIO,
                topic=filters.topic,
                language=filters.language or "en",
                start_time=start_time,
            )

        # Add user as participant
        participant = self.add_participant(session["id"], user_id)

        # Refresh session data
        session = self.get_session_by_id(session["id"])

        return session, participant["seat_number"]

    def is_participant(self, session: dict[str, Any], user_id: str) -> bool:
        """Check if user is a participant in the session."""
        participants = session.get("participants", [])
        for p in participants:
            if p.get("user_id") == user_id:
                return True
        return False

    def get_participant(self, session: dict[str, Any], user_id: str) -> Optional[dict[str, Any]]:
        """Get participant record for a user in the session."""
        participants = session.get("participants", [])
        for p in participants:
            if p.get("user_id") == user_id:
                return p
        return None
