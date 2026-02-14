"""
Session service for table management and matching.

Handles:
- Quick-match session finding/creation
- Participant management (join/leave)
- Session phase calculation
- LiveKit token generation
- AI companion seat filling
"""

import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from livekit import api
from supabase import Client

from app.core.cache import cache_delete_pattern, cache_get, cache_set
from app.core.config import get_settings
from app.core.constants import (
    AI_COMPANION_NAMES,
    MAX_PARTICIPANTS,
    MODERATE_HOUR_ESTIMATE,
    OFF_PEAK_HOUR_ESTIMATE,
    PEAK_HOUR_ESTIMATE,
    PIXEL_ROOMS,
    SESSION_DURATION_MINUTES,
    SLOT_SKIP_THRESHOLD_MINUTES,
    UPCOMING_SLOTS_COUNT,
)
from app.core.database import get_supabase
from app.models.session import (
    ParticipantType,
    SessionFilters,
    SessionPhase,
    TableMode,
)

logger = logging.getLogger(__name__)

SLOT_COUNTS_CACHE_TTL = 15  # seconds

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

    # Phase timing (derived from constants, specific to session logic)
    PHASE_DURATIONS = {
        SessionPhase.SETUP: 3,  # 0-3 min
        SessionPhase.WORK_1: 25,  # 3-28 min
        SessionPhase.BREAK: 2,  # 28-30 min
        SessionPhase.WORK_2: 20,  # 30-50 min
        SessionPhase.SOCIAL: 5,  # 50-55 min
    }

    PHASE_BOUNDARIES = {
        SessionPhase.SETUP: (0, 3),
        SessionPhase.WORK_1: (3, 28),
        SessionPhase.BREAK: (28, 30),
        SessionPhase.WORK_2: (30, 50),
        SessionPhase.SOCIAL: (50, 55),
    }

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
        if time_until_slot < SLOT_SKIP_THRESHOLD_MINUTES:
            # Skip to next slot (30 minutes later)
            next_slot = next_slot + timedelta(minutes=30)

        return next_slot

    def calculate_upcoming_slots(self, count: int = UPCOMING_SLOTS_COUNT) -> list[datetime]:
        """
        Return the next `count` upcoming :00/:30 slot times.

        Extends calculate_next_slot() forward by 30-minute increments.
        """
        first_slot = self.calculate_next_slot()
        return [first_slot + timedelta(minutes=30 * i) for i in range(count)]

    def get_slot_queue_counts(
        self,
        slot_times: list[datetime],
        mode: Optional[str] = None,
    ) -> dict[str, int]:
        """
        Get total human participants queued for each slot across all tables.

        Args:
            slot_times: List of slot datetimes to check
            mode: Optional table mode filter ("forced_audio" or "quiet")

        Returns:
            Dict mapping ISO time string to participant count
        """
        if not slot_times:
            return {}

        iso_times = [t.isoformat() for t in slot_times]

        # Build cache key from mode + sorted slot times
        slots_hash = hashlib.md5("|".join(sorted(iso_times)).encode()).hexdigest()[:12]
        cache_key = f"slot_counts:{mode or 'all'}:{slots_hash}"
        cached = cache_get(cache_key)
        if cached is not None:
            try:
                return cached
            except Exception:
                logger.debug("Failed to use cached slot counts, fetching from DB")

        # Query sessions at these start times that haven't ended
        query = (
            self.supabase.table("sessions")
            .select("id, start_time, session_participants(count)")
            .in_("start_time", iso_times)
            .neq("current_phase", "ended")
        )
        if mode:
            query = query.eq("mode", mode)

        result = query.execute()

        # Aggregate counts by start_time
        counts: dict[str, int] = dict.fromkeys(iso_times, 0)
        for session in result.data or []:
            start = session.get("start_time")
            # Normalize Z suffix for matching
            if start and start.endswith("+00:00"):
                start_key = start
            elif start and start.endswith("Z"):
                start_key = start[:-1] + "+00:00"
            else:
                start_key = start
            participant_count = (session.get("session_participants") or [{}])[0].get("count", 0)
            if start_key in counts:
                counts[start_key] += participant_count

        cache_set(cache_key, counts, SLOT_COUNTS_CACHE_TTL)
        return counts

    def get_slot_estimates(self, slot_times: list[datetime]) -> dict[str, int]:
        """
        Return estimated popularity for each time slot based on hour-of-day.

        MVP: Static estimates using Taiwan peak hours (UTC+8).
        Future: Replace with rolling 30-day averages from analytics.
        """
        estimates: dict[str, int] = {}
        for slot_time in slot_times:
            # Rough UTC+8 conversion for Taiwan market
            local_hour = (slot_time.hour + 8) % 24
            if 19 <= local_hour <= 23:
                estimates[slot_time.isoformat()] = PEAK_HOUR_ESTIMATE
            elif 9 <= local_hour <= 18:
                estimates[slot_time.isoformat()] = MODERATE_HOUR_ESTIMATE
            else:
                estimates[slot_time.isoformat()] = OFF_PEAK_HOUR_ESTIMATE
        return estimates

    def get_user_sessions_at_slots(self, user_id: str, slot_times: list[datetime]) -> set[str]:
        """
        Return set of ISO time strings where user already has an active session.
        """
        if not slot_times:
            return set()

        iso_times = [t.isoformat() for t in slot_times]

        result = (
            self.supabase.table("session_participants")
            .select("sessions(start_time)")
            .eq("user_id", user_id)
            .is_("left_at", "null")
            .execute()
        )

        user_slot_times: set[str] = set()
        for row in result.data or []:
            session = row.get("sessions")
            if session:
                start = session.get("start_time", "")
                # Normalize
                if start.endswith("Z"):
                    start = start[:-1] + "+00:00"
                if start in iso_times:
                    user_slot_times.add(start)
        return user_slot_times

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
            .select("*, users(id, username, display_name, avatar_config, pixel_avatar_id)")
            .eq("session_id", session_id)
            .is_("left_at", "null")
            .execute()
        )

        session["participants"] = participants_result.data or []
        session["available_seats"] = MAX_PARTICIPANTS - len(session["participants"])

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
        session_ids = []
        for row in result.data or []:
            if row.get("sessions"):
                session = row["sessions"]
                session["my_seat_number"] = row["seat_number"]
                sessions.append(session)
                session_ids.append(session["id"])

        if not session_ids:
            return sessions

        # Batch fetch participant rows for all sessions in ONE query
        counts_result = (
            self.supabase.table("session_participants")
            .select("session_id")
            .in_("session_id", session_ids)
            .is_("left_at", "null")
            .execute()
        )

        # Count occurrences of each session_id
        count_map: dict[str, int] = {}
        for row in counts_result.data or []:
            sid = row["session_id"]
            count_map[sid] = count_map.get(sid, 0) + 1

        for session in sessions:
            session["participant_count"] = count_map.get(session["id"], 0)

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
            .eq("is_private", False)  # Exclude private sessions from public matching
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
            if participant_count < MAX_PARTICIPANTS:
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
        end_time = start_time + timedelta(minutes=SESSION_DURATION_MINUTES)
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
            "room_type": random.choice(PIXEL_ROOMS),
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
        available_seats = [i for i in range(1, MAX_PARTICIPANTS + 1) if i not in taken_seats]

        companions = []
        for i, seat in enumerate(available_seats[:count]):
            name = AI_COMPANION_NAMES[i % len(AI_COMPANION_NAMES)]

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

        # Invalidate slot queue count cache (new participant changes counts)
        cache_delete_pattern("slot_counts:*")

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

    # =========================================================================
    # Private Sessions & Invitations
    # =========================================================================

    def create_private_session(
        self,
        creator_id: str,
        partner_ids: list[str],
        time_slot: datetime,
        mode: str,
        max_seats: int,
        fill_ai: bool,
        topic: Optional[str],
    ) -> dict[str, Any]:
        """
        Create a private session and send invitations to partners.

        Args:
            creator_id: User ID of the table creator
            partner_ids: List of partner user IDs to invite
            time_slot: Session start time (must be :00 or :30)
            mode: Table mode ('forced_audio' or 'quiet')
            max_seats: Maximum seats (2-4)
            fill_ai: Whether to fill empty seats with AI companions
            topic: Optional study topic

        Returns:
            Dict with session_id, invitations_sent count
        """
        end_time = time_slot + timedelta(minutes=SESSION_DURATION_MINUTES)
        room_name = f"private-{uuid.uuid4().hex[:12]}"

        session_data = {
            "start_time": time_slot.isoformat(),
            "end_time": end_time.isoformat(),
            "mode": mode,
            "topic": topic,
            "language": "en",
            "current_phase": SessionPhase.SETUP.value,
            "phase_started_at": time_slot.isoformat(),
            "livekit_room_name": room_name,
            "room_type": random.choice(PIXEL_ROOMS),
            "is_private": True,
            "created_by": creator_id,
            "max_seats": max_seats,
        }

        result = self.supabase.table("sessions").insert(session_data).execute()
        if not result.data:
            raise SessionServiceError("Failed to create private session")

        session = result.data[0]
        session_id = session["id"]

        # Add creator as participant (seat 1)
        self.supabase.table("session_participants").insert(
            {
                "session_id": session_id,
                "user_id": creator_id,
                "participant_type": ParticipantType.HUMAN.value,
                "seat_number": 1,
            }
        ).execute()

        # Create invitations for partners
        invitations = []
        for partner_id in partner_ids:
            invitations.append(
                {
                    "session_id": session_id,
                    "inviter_id": creator_id,
                    "invitee_id": partner_id,
                    "status": "pending",
                }
            )

        invitations_sent = 0
        if invitations:
            inv_result = self.supabase.table("table_invitations").insert(invitations).execute()
            invitations_sent = len(inv_result.data) if inv_result.data else 0

        return {
            "session_id": session_id,
            "invitations_sent": invitations_sent,
        }

    def get_pending_invitations(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get pending table invitations for a user.

        Returns invitations where the user is the invitee and status is pending,
        joined with session info for display.
        """
        now = datetime.now(timezone.utc)

        result = (
            self.supabase.table("table_invitations")
            .select("*, sessions(id, start_time, end_time, mode, topic)")
            .eq("invitee_id", user_id)
            .eq("status", "pending")
            .execute()
        )

        if not result.data:
            return []

        # Filter out expired invitations (session already started)
        active = []
        for inv in result.data:
            session = inv.get("sessions", {})
            if session:
                start_time = datetime.fromisoformat(session["start_time"].replace("Z", "+00:00"))
                if start_time > now:
                    active.append(inv)

        return active

    def respond_to_invitation(
        self,
        invitation_id: str,
        user_id: str,
        accept: bool,
    ) -> dict[str, Any]:
        """
        Accept or decline a table invitation.

        If accepting:
        - Validates the session hasn't started yet
        - Adds user as participant
        - Updates invitation status

        Args:
            invitation_id: Invitation UUID
            user_id: User ID of the invitee
            accept: True to accept, False to decline

        Returns:
            Updated invitation record

        Raises:
            InvitationNotFoundError: If invitation not found
            InvitationExpiredError: If session already started
        """
        from app.models.partner import InvitationExpiredError, InvitationNotFoundError

        # Fetch invitation
        result = (
            self.supabase.table("table_invitations")
            .select("*, sessions(id, start_time, max_seats)")
            .eq("id", invitation_id)
            .eq("invitee_id", user_id)
            .eq("status", "pending")
            .execute()
        )

        if not result.data:
            raise InvitationNotFoundError()

        invitation = result.data[0]
        session = invitation.get("sessions", {})

        if accept:
            # Check session hasn't started
            now = datetime.now(timezone.utc)
            start_time = datetime.fromisoformat(session["start_time"].replace("Z", "+00:00"))
            if start_time <= now:
                raise InvitationExpiredError()

            # Add as participant
            self.add_participant(session["id"], user_id)

        # Update invitation status
        status = "accepted" if accept else "declined"
        update_result = (
            self.supabase.table("table_invitations")
            .update(
                {
                    "status": status,
                    "responded_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", invitation_id)
            .execute()
        )

        return update_result.data[0] if update_result.data else {"status": status}
