"""Unit tests for session router endpoints.

Tests:
- get_session_summary() - focus minutes, phases, tablemate count
- leave_session() - happy path, errors
- cancel_session() - refund policy, timing checks
- rate_participant() - 501 not implemented
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.session import LeaveSessionRequest
from app.routers.sessions import (
    cancel_session,
    get_session_summary,
    leave_session,
    rate_participant,
)

# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def auth_user():
    """Standard authenticated user for tests."""
    return AuthUser(auth_id="auth-123", email="test@example.com")


@pytest.fixture
def mock_profile():
    """Mock user profile returned by user_service."""
    profile = MagicMock()
    profile.id = "user-123"
    profile.display_name = "Test User"
    profile.username = "testuser"
    return profile


@pytest.fixture
def mock_user_service(mock_profile):
    """Mock UserService that returns the mock profile."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = mock_profile
    return service


@pytest.fixture
def mock_user_service_no_user():
    """Mock UserService that returns None (user not found)."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = None
    return service


@pytest.fixture
def base_session_data():
    """Base session data dict used across tests."""
    start = datetime.now(timezone.utc) - timedelta(minutes=30)
    end = start + timedelta(minutes=55)
    return {
        "id": "session-abc",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "mode": "forced_audio",
        "current_phase": "work_2",
        "livekit_room_name": "focus-abc",
        "topic": "Deep work",
        "language": "en",
        "participants": [
            {
                "id": "p-1",
                "user_id": "user-123",
                "participant_type": "human",
                "seat_number": 1,
                "joined_at": start.isoformat(),
                "left_at": None,
                "users": {"username": "testuser", "display_name": "Test User", "avatar_config": {}},
            },
            {
                "id": "p-2",
                "user_id": "user-456",
                "participant_type": "human",
                "seat_number": 2,
                "joined_at": start.isoformat(),
                "left_at": None,
                "users": {"username": "other", "display_name": "Other User", "avatar_config": {}},
            },
            {
                "id": "p-3",
                "user_id": None,
                "participant_type": "ai_companion",
                "seat_number": 3,
                "joined_at": start.isoformat(),
                "left_at": None,
                "ai_companion_name": "Mochi",
                "users": None,
            },
        ],
    }


@pytest.fixture
def mock_session_service(base_session_data):
    """Mock SessionService with default session data."""
    service = MagicMock()
    service.get_session_by_id.return_value = base_session_data
    service.is_participant.return_value = True
    service.get_participant.return_value = {"id": "participant-1"}
    return service


def _make_supabase_participant_mock(participant_data):
    """Build a chainable supabase mock that returns participant data.

    Mocks the chain: supabase.table("session_participants")
        .select(...).eq(...).eq(...).execute()
    """
    mock_supabase = MagicMock()
    mock_result = MagicMock()
    mock_result.data = participant_data
    (
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value
    ) = mock_result
    return mock_supabase


# =============================================================================
# get_session_summary() Tests
# =============================================================================


class TestGetSessionSummary:
    """Tests for the get_session_summary() endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_happy_path_with_active_minutes(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Focus minutes = min(total_active_minutes, 45) when total_active > 0."""
        participant_data = [
            {
                "total_active_minutes": 30,
                "essence_earned": True,
                "connected_at": None,
                "disconnected_at": None,
            }
        ]
        mock_supabase = _make_supabase_participant_mock(participant_data)

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service,
            )

        assert result.focus_minutes == 30
        assert result.essence_earned is True
        assert result.mode.value == "forced_audio"
        assert result.topic == "Deep work"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_focus_minutes_capped_at_45(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Focus minutes are capped at 45 even if total_active is higher."""
        participant_data = [
            {
                "total_active_minutes": 60,
                "essence_earned": False,
                "connected_at": None,
                "disconnected_at": None,
            }
        ]
        mock_supabase = _make_supabase_participant_mock(participant_data)

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service,
            )

        assert result.focus_minutes == 45

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_estimates_from_connection_time_when_no_active_minutes(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Estimates focus minutes from connected_at when total_active_minutes = 0."""
        connected_at = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        participant_data = [
            {
                "total_active_minutes": 0,
                "essence_earned": False,
                "connected_at": connected_at,
                "disconnected_at": None,
            }
        ]
        mock_supabase = _make_supabase_participant_mock(participant_data)

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service,
            )

        # Should be approximately 20 (allow slight drift due to test execution time)
        assert 19 <= result.focus_minutes <= 21

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_no_participant_data_returns_zero_focus(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Returns focus_minutes = 0 when no participant record found."""
        mock_supabase = _make_supabase_participant_mock([])

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service,
            )

        assert result.focus_minutes == 0
        assert result.essence_earned is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_not_found_raises_404(
        self, auth_user, mock_user_service_no_user, mock_session_service
    ) -> None:
        """Raises 404 when user profile is not found."""
        with pytest.raises(HTTPException) as exc_info:
            await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_not_found_raises_404(self, auth_user, mock_user_service) -> None:
        """Raises 404 when session does not exist."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_session_summary(
                session_id="nonexistent",
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 404
        assert "Session not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_not_participant_raises_403(
        self, auth_user, mock_user_service, base_session_data
    ) -> None:
        """Raises 403 when user is not a participant in the session."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = base_session_data
        session_service.is_participant.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_phase_ended_gives_5_phases_completed(self, auth_user, mock_user_service) -> None:
        """Phase 'ended' results in phases_completed = 5."""
        session_data = {
            "id": "session-abc",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat(),
            "mode": "quiet",
            "current_phase": "ended",
            "livekit_room_name": "focus-abc",
            "topic": None,
            "language": "en",
            "participants": [],
        }
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = session_data
        session_service.is_participant.return_value = True

        mock_supabase = _make_supabase_participant_mock(
            [
                {
                    "total_active_minutes": 45,
                    "essence_earned": True,
                    "connected_at": None,
                    "disconnected_at": None,
                }
            ]
        )

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )

        assert result.phases_completed == 5
        assert result.total_phases == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_phase_work_1_gives_1_phase_completed(self, auth_user, mock_user_service) -> None:
        """Phase 'work_1' is at index 1 in phase_order, so phases_completed = 1."""
        session_data = {
            "id": "session-abc",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat(),
            "mode": "forced_audio",
            "current_phase": "work_1",
            "livekit_room_name": "focus-abc",
            "topic": None,
            "language": "en",
            "participants": [],
        }
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = session_data
        session_service.is_participant.return_value = True

        mock_supabase = _make_supabase_participant_mock(
            [
                {
                    "total_active_minutes": 5,
                    "essence_earned": False,
                    "connected_at": None,
                    "disconnected_at": None,
                }
            ]
        )

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )

        assert result.phases_completed == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_phase_setup_gives_0_phases_completed(self, auth_user, mock_user_service) -> None:
        """Phase 'setup' is at index 0 in phase_order, so phases_completed = 0."""
        session_data = {
            "id": "session-abc",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(minutes=55)).isoformat(),
            "mode": "forced_audio",
            "current_phase": "setup",
            "livekit_room_name": "focus-abc",
            "topic": None,
            "language": "en",
            "participants": [],
        }
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = session_data
        session_service.is_participant.return_value = True

        mock_supabase = _make_supabase_participant_mock(
            [
                {
                    "total_active_minutes": 0,
                    "essence_earned": False,
                    "connected_at": None,
                    "disconnected_at": None,
                }
            ]
        )

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )

        assert result.phases_completed == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_tablemate_count_excludes_ai_and_self(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Tablemate count excludes AI companions and the requesting user."""
        # base_session_data has: user-123 (self), user-456 (human), ai_companion
        # so tablemate_count should be 1 (only user-456)
        mock_supabase = _make_supabase_participant_mock(
            [
                {
                    "total_active_minutes": 20,
                    "essence_earned": False,
                    "connected_at": None,
                    "disconnected_at": None,
                }
            ]
        )

        with patch("app.core.database.get_supabase", return_value=mock_supabase):
            result = await get_session_summary(
                session_id="session-abc",
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service,
            )

        assert result.tablemate_count == 1


# =============================================================================
# leave_session() Tests
# =============================================================================


class TestLeaveSession:
    """Tests for the leave_session() endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_happy_path(self, auth_user, mock_user_service, mock_session_service) -> None:
        """Returns LeaveSessionResponse with status='left' on success."""
        result = await leave_session(
            session_id="session-abc",
            request=LeaveSessionRequest(),
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        assert result.status == "left"
        assert result.session_id == "session-abc"
        mock_session_service.remove_participant.assert_called_once_with(
            session_id="session-abc",
            user_id="user-123",
            reason=None,
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_with_reason(self, auth_user, mock_user_service, mock_session_service) -> None:
        """Passes reason to remove_participant when provided."""
        request = LeaveSessionRequest(reason="Need to go")
        result = await leave_session(
            session_id="session-abc",
            request=request,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        assert result.status == "left"
        mock_session_service.remove_participant.assert_called_once_with(
            session_id="session-abc",
            user_id="user-123",
            reason="Need to go",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_not_found_raises_404(
        self, auth_user, mock_user_service_no_user, mock_session_service
    ) -> None:
        """Raises 404 when user profile is not found."""
        with pytest.raises(HTTPException) as exc_info:
            await leave_session(
                session_id="session-abc",
                request=LeaveSessionRequest(),
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_not_found_raises_404(self, auth_user, mock_user_service) -> None:
        """Raises 404 when session does not exist."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await leave_session(
                session_id="nonexistent",
                request=LeaveSessionRequest(),
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_not_participant_raises_403(
        self, auth_user, mock_user_service, base_session_data
    ) -> None:
        """Raises 403 when user is not a participant."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = base_session_data
        session_service.is_participant.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await leave_session(
                session_id="session-abc",
                request=LeaveSessionRequest(),
                user=auth_user,
                session_service=session_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 403


# =============================================================================
# cancel_session() Tests
# =============================================================================


class TestCancelSession:
    """Tests for the cancel_session() endpoint."""

    @pytest.fixture
    def future_session_data(self):
        """Session starting 2 hours from now (refund eligible)."""
        start = datetime.now(timezone.utc) + timedelta(hours=2)
        end = start + timedelta(minutes=55)
        return {
            "id": "session-future",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "mode": "forced_audio",
            "current_phase": "setup",
            "livekit_room_name": "focus-future",
            "topic": None,
            "language": "en",
            "participants": [],
        }

    @pytest.fixture
    def soon_session_data(self):
        """Session starting 30 minutes from now (no refund)."""
        start = datetime.now(timezone.utc) + timedelta(minutes=30)
        end = start + timedelta(minutes=55)
        return {
            "id": "session-soon",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "mode": "quiet",
            "current_phase": "setup",
            "livekit_room_name": "focus-soon",
            "topic": None,
            "language": "en",
            "participants": [],
        }

    @pytest.fixture
    def started_session_data(self):
        """Session that already started (10 minutes ago)."""
        start = datetime.now(timezone.utc) - timedelta(minutes=10)
        end = start + timedelta(minutes=55)
        return {
            "id": "session-started",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "mode": "forced_audio",
            "current_phase": "work_1",
            "livekit_room_name": "focus-started",
            "topic": None,
            "language": "en",
            "participants": [],
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_with_refund(
        self, auth_user, mock_user_service, future_session_data
    ) -> None:
        """Cancel >= 1hr before start grants refund."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = future_session_data
        session_service.get_participant.return_value = {"id": "participant-1"}

        credit_service = MagicMock()
        credit_service.refund_credit.return_value = {"id": "txn-refund"}

        result = await cancel_session(
            session_id="session-future",
            user=auth_user,
            session_service=session_service,
            credit_service=credit_service,
            user_service=mock_user_service,
        )

        assert result.status == "cancelled"
        assert result.session_id == "session-future"
        assert result.credit_refunded is True
        assert "refunded" in result.message.lower()
        session_service.remove_participant.assert_called_once_with(
            session_id="session-future",
            user_id="user-123",
            reason="cancelled",
        )
        credit_service.refund_credit.assert_called_once_with(
            user_id="user-123",
            session_id="session-future",
            participant_id="participant-1",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cancel_without_refund(
        self, auth_user, mock_user_service, soon_session_data
    ) -> None:
        """Cancel < 1hr before start does not grant refund."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = soon_session_data
        session_service.get_participant.return_value = {"id": "participant-1"}

        credit_service = MagicMock()

        result = await cancel_session(
            session_id="session-soon",
            user=auth_user,
            session_service=session_service,
            credit_service=credit_service,
            user_service=mock_user_service,
        )

        assert result.status == "cancelled"
        assert result.credit_refunded is False
        assert "minutes" in result.message
        credit_service.refund_credit.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_already_started_raises_400(
        self, auth_user, mock_user_service, started_session_data
    ) -> None:
        """Raises 400 when session has already started."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = started_session_data
        session_service.get_participant.return_value = {"id": "participant-1"}

        credit_service = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await cancel_session(
                session_id="session-started",
                user=auth_user,
                session_service=session_service,
                credit_service=credit_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 400
        assert "already started" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_not_found_raises_404(self, auth_user, mock_user_service_no_user) -> None:
        """Raises 404 when user profile is not found."""
        session_service = MagicMock()
        credit_service = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await cancel_session(
                session_id="session-abc",
                user=auth_user,
                session_service=session_service,
                credit_service=credit_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_session_not_found_raises_404(self, auth_user, mock_user_service) -> None:
        """Raises 404 when session does not exist."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = None
        credit_service = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await cancel_session(
                session_id="nonexistent",
                user=auth_user,
                session_service=session_service,
                credit_service=credit_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_not_participant_raises_403(
        self, auth_user, mock_user_service, future_session_data
    ) -> None:
        """Raises 403 when user is not a participant (get_participant returns None)."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = future_session_data
        session_service.get_participant.return_value = None

        credit_service = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await cancel_session(
                session_id="session-future",
                user=auth_user,
                session_service=session_service,
                credit_service=credit_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_refund_eligible_but_refund_returns_none(
        self, auth_user, mock_user_service, future_session_data
    ) -> None:
        """When refund_credit returns None, credit_refunded=False and message says 'already refunded'."""
        session_service = MagicMock()
        session_service.get_session_by_id.return_value = future_session_data
        session_service.get_participant.return_value = {"id": "participant-1"}

        credit_service = MagicMock()
        credit_service.refund_credit.return_value = None

        result = await cancel_session(
            session_id="session-future",
            user=auth_user,
            session_service=session_service,
            credit_service=credit_service,
            user_service=mock_user_service,
        )

        assert result.credit_refunded is False
        assert "already refunded" in result.message.lower()


# =============================================================================
# rate_participant() Tests
# =============================================================================


class TestRateParticipant:
    """Tests for the rate_participant() endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_raises_501_not_implemented(self) -> None:
        """Always raises 501 Not Implemented."""
        with pytest.raises(HTTPException) as exc_info:
            await rate_participant(
                session_id="session-abc",
                participant_id="p-1",
                rating="green",
            )
        assert exc_info.value.status_code == 501
        assert "Not implemented" in str(exc_info.value.detail)
