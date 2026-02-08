"""Unit tests for session router helper functions.

Tests:
- _parse_datetime() ISO string parsing and edge cases
- _build_session_info() dict-to-SessionInfo conversion
- _schedule_livekit_tasks() Celery task scheduling
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.session import (
    ParticipantType,
    QuickMatchRequest,
    QuickMatchResponse,
    SessionInfo,
    SessionPhase,
    TableMode,
    UpcomingSessionsResponse,
)
from app.routers.sessions import (
    _build_session_info,
    _parse_datetime,
    _schedule_livekit_tasks,
    get_session,
    get_upcoming_sessions,
    quick_match,
)
from app.services.credit_service import InsufficientCreditsError
from app.services.session_service import (
    AlreadyInSessionError,
    SessionFullError,
    SessionPhaseError,
)

# =============================================================================
# _parse_datetime() Tests
# =============================================================================


class TestParseDateTime:
    """Tests for the _parse_datetime() helper."""

    @pytest.mark.unit
    def test_returns_none_for_none(self) -> None:
        """Input None returns None."""
        assert _parse_datetime(None) is None

    @pytest.mark.unit
    def test_returns_datetime_unchanged(self) -> None:
        """Input datetime object returns the same object."""
        dt = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = _parse_datetime(dt)
        assert result is dt

    @pytest.mark.unit
    def test_parses_iso_string(self) -> None:
        """Standard ISO string with timezone offset parsed correctly."""
        result = _parse_datetime("2025-06-15T10:30:00+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    @pytest.mark.unit
    def test_handles_z_suffix(self) -> None:
        """String ending with 'Z' is converted and parsed correctly."""
        result = _parse_datetime("2025-06-15T10:30:00.000Z")
        assert isinstance(result, datetime)
        assert result.hour == 10
        assert result.minute == 30


# =============================================================================
# _build_session_info() Tests
# =============================================================================


class TestBuildSessionInfo:
    """Tests for the _build_session_info() helper."""

    @pytest.mark.unit
    def test_builds_info_with_participants(self) -> None:
        """Full session dict with participant records returns correct SessionInfo."""
        now = datetime.now(timezone.utc)
        session_data = {
            "id": "session-1",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(minutes=55)).isoformat(),
            "mode": "forced_audio",
            "topic": "python",
            "language": "en",
            "current_phase": "setup",
            "phase_started_at": now.isoformat(),
            "livekit_room_name": "focus-abc",
            "available_seats": 3,
            "participants": [
                {
                    "id": "p-1",
                    "user_id": "user-1",
                    "participant_type": "human",
                    "seat_number": 1,
                    "joined_at": now.isoformat(),
                    "left_at": None,
                    "ai_companion_name": None,
                    "users": {
                        "id": "user-1",
                        "username": "testuser",
                        "display_name": "Test User",
                        "avatar_config": {"color": "blue"},
                    },
                }
            ],
        }

        result = _build_session_info(session_data)

        assert isinstance(result, SessionInfo)
        assert result.id == "session-1"
        assert result.mode == TableMode.FORCED_AUDIO
        assert result.topic == "python"
        assert result.language == "en"
        assert result.current_phase == SessionPhase.SETUP
        assert result.livekit_room_name == "focus-abc"
        assert result.available_seats == 3
        assert len(result.participants) == 1

        participant = result.participants[0]
        assert participant.id == "p-1"
        assert participant.user_id == "user-1"
        assert participant.participant_type == ParticipantType.HUMAN
        assert participant.seat_number == 1
        assert participant.username == "testuser"
        assert participant.display_name == "Test User"
        assert participant.avatar_config == {"color": "blue"}
        assert participant.is_active is True
        assert participant.ai_companion_name is None

    @pytest.mark.unit
    def test_builds_info_empty_participants(self) -> None:
        """No participants results in available_seats=4 (default calculation)."""
        now = datetime.now(timezone.utc)
        session_data = {
            "id": "session-2",
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(minutes=55)).isoformat(),
            "mode": "quiet",
            "topic": None,
            "language": "zh-TW",
            "current_phase": "work_1",
            "phase_started_at": None,
            "livekit_room_name": "focus-xyz",
            "participants": [],
        }

        result = _build_session_info(session_data)

        assert isinstance(result, SessionInfo)
        assert result.id == "session-2"
        assert result.mode == TableMode.QUIET
        assert result.language == "zh-TW"
        assert result.current_phase == SessionPhase.WORK_1
        assert result.phase_started_at is None
        assert len(result.participants) == 0
        assert result.available_seats == 4


# =============================================================================
# _schedule_livekit_tasks() Tests
# =============================================================================


class TestScheduleLivekitTasks:
    """Tests for the _schedule_livekit_tasks() helper."""

    @pytest.mark.unit
    def test_schedules_all_tasks(self) -> None:
        """Future start time schedules all three Celery tasks."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(minutes=30)
        end_time = start_time + timedelta(minutes=55)
        session_data = {
            "id": "session-1",
            "end_time": end_time.isoformat(),
        }

        mock_create = MagicMock()
        mock_fill = MagicMock()
        mock_cleanup = MagicMock()

        mock_tasks_module = MagicMock()
        mock_tasks_module.create_livekit_room = mock_create
        mock_tasks_module.fill_empty_seats_with_ai = mock_fill
        mock_tasks_module.cleanup_ended_session = mock_cleanup

        with patch.dict("sys.modules", {"app.tasks.livekit_tasks": mock_tasks_module}):
            _schedule_livekit_tasks(session_data, start_time)

        mock_create.apply_async.assert_called_once()
        call_kwargs = mock_create.apply_async.call_args
        assert call_kwargs[1]["args"] == ["session-1"]
        assert call_kwargs[1]["task_id"] == "create-room-session-1"

        mock_fill.apply_async.assert_called_once()
        fill_kwargs = mock_fill.apply_async.call_args
        assert fill_kwargs[1]["args"] == ["session-1"]
        assert fill_kwargs[1]["task_id"] == "fill-ai-session-1"

        mock_cleanup.apply_async.assert_called_once()
        cleanup_kwargs = mock_cleanup.apply_async.call_args
        assert cleanup_kwargs[1]["args"] == ["session-1"]
        assert cleanup_kwargs[1]["task_id"] == "cleanup-session-session-1"

    @pytest.mark.unit
    def test_handles_error_gracefully(self) -> None:
        """Task import failure does not raise an exception (try/except catches it)."""
        now = datetime.now(timezone.utc)
        start_time = now + timedelta(minutes=30)
        session_data = {
            "id": "session-err",
            "end_time": (start_time + timedelta(minutes=55)).isoformat(),
        }

        with patch.dict("sys.modules", {"app.tasks.livekit_tasks": None}):
            # ModuleNotFoundError is caught by the try/except in _schedule_livekit_tasks
            _schedule_livekit_tasks(session_data, start_time)
            # No exception raised - test passes


# =============================================================================
# Endpoint Tests
# =============================================================================


def _make_auth_user(auth_id: str = "auth-123", email: str = "test@example.com") -> AuthUser:
    return AuthUser(auth_id=auth_id, email=email)


def _make_mock_profile(
    user_id: str = "user-123",
    banned_until: Optional[datetime] = None,
    display_name: str = "Test",
    username: str = "testuser",
):
    profile = MagicMock()
    profile.id = user_id
    profile.banned_until = banned_until
    profile.display_name = display_name
    profile.username = username
    return profile


def _make_session_data(
    session_id: str = "session-abc",
    start_minutes_from_now: int = 30,
):
    now = datetime.now(timezone.utc)
    start = now + timedelta(minutes=start_minutes_from_now)
    end = start + timedelta(minutes=55)
    return {
        "id": session_id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "mode": "forced_audio",
        "topic": "python",
        "language": "en",
        "current_phase": "setup",
        "phase_started_at": start.isoformat(),
        "livekit_room_name": f"focus-{session_id}",
        "available_seats": 3,
        "participants": [
            {
                "id": "p-1",
                "user_id": "user-123",
                "participant_type": "human",
                "seat_number": 1,
                "joined_at": start.isoformat(),
                "left_at": None,
                "ai_companion_name": None,
                "users": {
                    "id": "user-123",
                    "username": "testuser",
                    "display_name": "Test",
                    "avatar_config": {},
                },
            }
        ],
    }


# =============================================================================
# quick_match() Tests
# =============================================================================


class TestQuickMatch:
    """Tests for the quick_match() endpoint."""

    def _setup_mocks(self, **overrides):
        """Create default mocks for quick_match dependencies."""
        user_service = MagicMock()
        credit_service = MagicMock()
        session_service = MagicMock()
        analytics_service = MagicMock()
        analytics_service.track_event = AsyncMock(return_value=None)
        rating_service = MagicMock()
        rating_service.has_pending_ratings.return_value = False

        profile = overrides.get("profile", _make_mock_profile())
        user_service.get_user_by_auth_id.return_value = profile

        credit_service.has_sufficient_credits.return_value = overrides.get("has_credits", True)
        credit_service.deduct_credit.return_value = None

        now = datetime.now(timezone.utc)
        next_slot = now + timedelta(minutes=30)
        session_service.calculate_next_slot.return_value = next_slot
        session_service.get_user_session_at_time.return_value = overrides.get(
            "existing_session", None
        )

        session_data = overrides.get("session_data", _make_session_data())
        seat_number = overrides.get("seat_number", 1)
        session_service.find_or_create_session.return_value = (session_data, seat_number)
        session_service.generate_livekit_token.return_value = "mock-token"

        return {
            "request": QuickMatchRequest(filters=None),
            "user": _make_auth_user(),
            "session_service": session_service,
            "credit_service": credit_service,
            "user_service": user_service,
            "analytics_service": analytics_service,
            "rating_service": rating_service,
        }

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_happy_path(self, mock_schedule) -> None:
        """Successful quick match returns QuickMatchResponse with session details."""
        mocks = self._setup_mocks()
        result = await quick_match(**mocks)

        assert isinstance(result, QuickMatchResponse)
        assert result.session.id == "session-abc"
        assert result.livekit_token == "mock-token"
        assert result.seat_number == 1
        assert result.credit_deducted is True
        assert result.wait_minutes >= 0

        mocks["credit_service"].deduct_credit.assert_called_once()
        mocks["session_service"].generate_livekit_token.assert_called_once()
        mocks["analytics_service"].track_event.assert_awaited_once()
        mock_schedule.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_user_not_found_returns_404(self, mock_schedule) -> None:
        """Missing user profile raises 404."""
        mocks = self._setup_mocks()
        mocks["user_service"].get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_banned_user_returns_403(self, mock_schedule) -> None:
        """Banned user (banned_until in the future) raises 403."""
        future = datetime.now(timezone.utc) + timedelta(hours=48)
        profile = _make_mock_profile(banned_until=future)
        mocks = self._setup_mocks(profile=profile)

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 403
        assert "suspended" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_insufficient_credits_returns_402(self, mock_schedule) -> None:
        """No credits raises 402."""
        mocks = self._setup_mocks(has_credits=False)

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 402
        assert "Insufficient credits" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_credit_check_exception_returns_402(self, mock_schedule) -> None:
        """Exception during credit check raises 402."""
        mocks = self._setup_mocks()
        mocks["credit_service"].has_sufficient_credits.side_effect = Exception("DB error")

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 402

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_existing_session_at_slot_returns_409(self, mock_schedule) -> None:
        """User already has a session at the time slot raises 409."""
        existing = {"id": "existing-session", "start_time": "2025-06-15T10:00:00+00:00"}
        mocks = self._setup_mocks(existing_session=existing)

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 409
        assert "already have a session" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_already_in_session_error_returns_409(self, mock_schedule) -> None:
        """AlreadyInSessionError from find_or_create raises 409."""
        mocks = self._setup_mocks()
        mocks["session_service"].find_or_create_session.side_effect = AlreadyInSessionError(
            session_id="sess-1", user_id="user-123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 409
        assert "already in a session" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_session_full_error_returns_409(self, mock_schedule) -> None:
        """SessionFullError from find_or_create raises 409."""
        mocks = self._setup_mocks()
        mocks["session_service"].find_or_create_session.side_effect = SessionFullError(
            session_id="sess-1"
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 409
        assert "No available sessions" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_session_phase_error_returns_409(self, mock_schedule) -> None:
        """SessionPhaseError from find_or_create raises 409."""
        mocks = self._setup_mocks()
        mocks["session_service"].find_or_create_session.side_effect = SessionPhaseError(
            session_id="sess-1", current_phase="work_1"
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)
        assert exc_info.value.status_code == 409
        assert "no longer accepting" in str(exc_info.value.detail).lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch("app.routers.sessions._schedule_livekit_tasks")
    async def test_deduct_credit_fails_triggers_rollback_returns_402(self, mock_schedule) -> None:
        """InsufficientCreditsError during deduct_credit triggers remove_participant and 402."""
        mocks = self._setup_mocks()
        mocks["credit_service"].deduct_credit.side_effect = InsufficientCreditsError(
            user_id="user-123", required=1, available=0
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(**mocks)

        assert exc_info.value.status_code == 402
        assert "Insufficient credits" in str(exc_info.value.detail)
        mocks["session_service"].remove_participant.assert_called_once_with(
            "session-abc", "user-123"
        )


# =============================================================================
# get_upcoming_sessions() Tests
# =============================================================================


class TestGetUpcomingSessions:
    """Tests for the get_upcoming_sessions() endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_returns_sessions(self) -> None:
        """Returns UpcomingSessionsResponse with sessions list."""
        user_service = MagicMock()
        session_service = MagicMock()

        profile = _make_mock_profile()
        user_service.get_user_by_auth_id.return_value = profile

        now = datetime.now(timezone.utc)
        session_service.get_user_sessions.return_value = [
            {
                "id": "s-1",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(minutes=55)).isoformat(),
                "mode": "forced_audio",
                "topic": "study",
                "language": "en",
                "current_phase": "setup",
                "participant_count": 2,
                "my_seat_number": 1,
            }
        ]

        result = await get_upcoming_sessions(
            user=_make_auth_user(),
            session_service=session_service,
            user_service=user_service,
        )

        assert isinstance(result, UpcomingSessionsResponse)
        assert len(result.sessions) == 1
        assert result.sessions[0].id == "s-1"
        assert result.sessions[0].participant_count == 2
        assert result.sessions[0].my_seat_number == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_returns_404(self) -> None:
        """Missing user profile raises 404."""
        user_service = MagicMock()
        session_service = MagicMock()
        user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_upcoming_sessions(
                user=_make_auth_user(),
                session_service=session_service,
                user_service=user_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_sessions_list(self) -> None:
        """No upcoming sessions returns empty list."""
        user_service = MagicMock()
        session_service = MagicMock()

        user_service.get_user_by_auth_id.return_value = _make_mock_profile()
        session_service.get_user_sessions.return_value = []

        result = await get_upcoming_sessions(
            user=_make_auth_user(),
            session_service=session_service,
            user_service=user_service,
        )

        assert isinstance(result, UpcomingSessionsResponse)
        assert len(result.sessions) == 0


# =============================================================================
# get_session() Tests
# =============================================================================


class TestGetSession:
    """Tests for the get_session() endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_returns_session_info(self) -> None:
        """Returns SessionInfo for a valid session and participant."""
        user_service = MagicMock()
        session_service = MagicMock()

        user_service.get_user_by_auth_id.return_value = _make_mock_profile()
        session_data = _make_session_data()
        session_service.get_session_by_id.return_value = session_data
        session_service.is_participant.return_value = True

        result = await get_session(
            session_id="session-abc",
            user=_make_auth_user(),
            session_service=session_service,
            user_service=user_service,
        )

        assert isinstance(result, SessionInfo)
        assert result.id == "session-abc"
        assert result.mode == TableMode.FORCED_AUDIO

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_returns_404(self) -> None:
        """Missing user profile raises 404."""
        user_service = MagicMock()
        session_service = MagicMock()
        user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_session(
                session_id="session-abc",
                user=_make_auth_user(),
                session_service=session_service,
                user_service=user_service,
            )
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_session_not_found_returns_404(self) -> None:
        """Missing session raises 404."""
        user_service = MagicMock()
        session_service = MagicMock()

        user_service.get_user_by_auth_id.return_value = _make_mock_profile()
        session_service.get_session_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_session(
                session_id="nonexistent",
                user=_make_auth_user(),
                session_service=session_service,
                user_service=user_service,
            )
        assert exc_info.value.status_code == 404
        assert "Session not found" in str(exc_info.value.detail)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_participant_returns_403(self) -> None:
        """Non-participant user raises 403."""
        user_service = MagicMock()
        session_service = MagicMock()

        user_service.get_user_by_auth_id.return_value = _make_mock_profile()
        session_service.get_session_by_id.return_value = _make_session_data()
        session_service.is_participant.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await get_session(
                session_id="session-abc",
                user=_make_auth_user(),
                session_service=session_service,
                user_service=user_service,
            )
        assert exc_info.value.status_code == 403
        assert "not a participant" in str(exc_info.value.detail).lower()
