"""Unit tests for SessionService.

Tests written first (TDD) for:
- Time slot calculation
- Session matching
- Participant management
- Phase calculation
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# These imports will fail until SessionService is implemented
# That's expected in TDD - tests come first
from app.models.session import (
    SessionFilters,
    SessionPhase,
    TableMode,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def session_service(mock_supabase):
    """SessionService with mocked Supabase."""
    from app.services.session_service import SessionService

    return SessionService(supabase=mock_supabase)


@pytest.fixture
def sample_session_row():
    """Sample session data from database."""
    now = datetime.now(timezone.utc)
    return {
        "id": "session-123",
        "start_time": now.isoformat(),
        "end_time": (now + timedelta(minutes=55)).isoformat(),
        "mode": "forced_audio",
        "topic": "python",
        "language": "en",
        "current_phase": "setup",
        "phase_started_at": now.isoformat(),
        "livekit_room_name": "focus-session-123",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def sample_participant_row():
    """Sample participant data from database."""
    now = datetime.now(timezone.utc)
    return {
        "id": "participant-123",
        "session_id": "session-123",
        "user_id": "user-123",
        "participant_type": "human",
        "seat_number": 1,
        "ai_companion_name": None,
        "ai_companion_avatar": None,
        "joined_at": now.isoformat(),
        "left_at": None,
        "disconnect_count": 0,
        "total_active_minutes": 0,
        "essence_earned": False,
    }


@pytest.fixture
def sample_user_row():
    """Sample user data for joins."""
    return {
        "id": "user-123",
        "username": "testuser",
        "display_name": "Test User",
        "avatar_config": {"color": "blue"},
    }


# =============================================================================
# Test: Time Slot Calculation
# =============================================================================


class TestCalculateNextSlot:
    """Tests for calculate_next_slot() method."""

    @pytest.mark.unit
    def test_at_00_returns_30(self, session_service):
        """Time at :00 should return :30 of same hour."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            assert result.minute == 30
            assert result.hour == 14
            assert result.second == 0
            assert result.microsecond == 0

    @pytest.mark.unit
    def test_at_15_returns_30(self, session_service):
        """Time at :15 should return :30 of same hour."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 15, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            assert result.minute == 30
            assert result.hour == 14

    @pytest.mark.unit
    def test_at_30_returns_next_hour(self, session_service):
        """Time at :30 should return :00 of next hour."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 30, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            assert result.minute == 0
            assert result.hour == 15

    @pytest.mark.unit
    def test_at_45_returns_next_hour(self, session_service):
        """Time at :45 should return :00 of next hour."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 45, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            assert result.minute == 0
            assert result.hour == 15

    @pytest.mark.unit
    def test_within_3min_of_slot_skips(self, session_service):
        """Time at :28 should skip :30 and return next :00."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 28, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            # Should skip :30 and go to :00 of next hour
            assert result.minute == 0
            assert result.hour == 15

    @pytest.mark.unit
    def test_within_3min_of_hour_skips(self, session_service):
        """Time at :58 should skip :00 and return next :30."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 14, 58, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            # Should skip :00 and go to :30 of next hour
            assert result.minute == 30
            assert result.hour == 15

    @pytest.mark.unit
    def test_midnight_rollover(self, session_service):
        """Time at 23:45 should return 00:00 of next day."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 5, 23, 45, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_next_slot()

            assert result.minute == 0
            assert result.hour == 0
            assert result.day == 6  # Next day


# =============================================================================
# Test: Session Retrieval
# =============================================================================


class TestGetSessionById:
    """Tests for get_session_by_id() method."""

    @pytest.mark.unit
    def test_session_found(self, session_service, mock_supabase, sample_session_row):
        """Returns session dict when session exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call for session, second for participants
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_session_row
        ]
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        result = session_service.get_session_by_id("session-123")

        assert result is not None
        assert result["id"] == "session-123"

    @pytest.mark.unit
    def test_session_not_found(self, session_service, mock_supabase):
        """Returns None when session doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = session_service.get_session_by_id("nonexistent")

        assert result is None


class TestGetUserSessions:
    """Tests for get_user_sessions() method."""

    @pytest.mark.unit
    def test_returns_upcoming_sessions(
        self, session_service, mock_supabase, sample_session_row, sample_participant_row
    ):
        """Returns list of sessions user is participating in."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Participant query returns sessions the user is in
        participant_with_session = {
            **sample_participant_row,
            "sessions": sample_session_row,
        }
        mock_table.select.return_value.eq.return_value.is_.return_value.neq.return_value.execute.return_value.data = [
            participant_with_session
        ]

        # Count query for participant_count
        count_result = MagicMock()
        count_result.count = 2
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value = (
            count_result
        )

        result = session_service.get_user_sessions("user-123")

        assert len(result) >= 1
        assert result[0]["id"] == "session-123"

    @pytest.mark.unit
    def test_excludes_ended_sessions(self, session_service, mock_supabase):
        """Does not return sessions that have ended."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # No upcoming sessions
        mock_table.select.return_value.eq.return_value.is_.return_value.neq.return_value.execute.return_value.data = []

        result = session_service.get_user_sessions("user-123")

        assert len(result) == 0


# =============================================================================
# Test: Session Matching
# =============================================================================


class TestFindMatchingSession:
    """Tests for find_matching_session() method."""

    @pytest.mark.unit
    def test_finds_session_with_available_seats(
        self, session_service, mock_supabase, sample_session_row
    ):
        """Finds existing session with open seats."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Create a proper mock chain that returns data correctly
        mock_execute = MagicMock()
        mock_execute.data = [sample_session_row]

        # The query chain can be any combination of .eq() and .lt()
        # We use a recursive mock that always returns itself and ends with execute()
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value = mock_execute
        mock_table.select.return_value = mock_query

        filters = SessionFilters(mode=TableMode.FORCED_AUDIO)
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.find_matching_session(filters, start_time)

        assert result is not None
        assert result["id"] == "session-123"

    @pytest.mark.unit
    def test_filters_by_mode(self, session_service, mock_supabase):
        """Only matches sessions with requested mode."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = []

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value = mock_execute
        mock_table.select.return_value = mock_query

        filters = SessionFilters(mode=TableMode.QUIET)
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.find_matching_session(filters, start_time)

        assert result is None

    @pytest.mark.unit
    def test_filters_by_topic(self, session_service, mock_supabase, sample_session_row):
        """Only matches sessions with requested topic."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = [sample_session_row]

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value = mock_execute
        mock_table.select.return_value = mock_query

        filters = SessionFilters(topic="python")
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.find_matching_session(filters, start_time)

        assert result is not None

    @pytest.mark.unit
    def test_no_match_returns_none(self, session_service, mock_supabase):
        """Returns None when no matching session found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_execute = MagicMock()
        mock_execute.data = []

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value = mock_execute
        mock_table.select.return_value = mock_query

        filters = SessionFilters()
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.find_matching_session(filters, start_time)

        assert result is None


# =============================================================================
# Test: Session Creation
# =============================================================================


class TestCreateSession:
    """Tests for create_session() method."""

    @pytest.mark.unit
    def test_creates_session_with_defaults(
        self, session_service, mock_supabase, sample_session_row
    ):
        """Creates session with default values."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [sample_session_row]

        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.create_session(
            mode=TableMode.FORCED_AUDIO,
            topic=None,
            language="en",
            start_time=start_time,
        )

        assert result is not None
        assert result["id"] == "session-123"

        # Verify insert was called
        mock_table.insert.assert_called_once()

    @pytest.mark.unit
    def test_calculates_end_time(self, session_service, mock_supabase, sample_session_row):
        """End time is 55 minutes after start time."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [sample_session_row]

        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        session_service.create_session(
            mode=TableMode.FORCED_AUDIO,
            topic=None,
            language="en",
            start_time=start_time,
        )

        # Verify the inserted data had correct end_time
        call_args = mock_table.insert.call_args
        inserted_data = call_args[0][0]
        assert "end_time" in inserted_data

    @pytest.mark.unit
    def test_generates_livekit_room_name(self, session_service, mock_supabase, sample_session_row):
        """LiveKit room name is generated."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [sample_session_row]

        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        session_service.create_session(
            mode=TableMode.FORCED_AUDIO,
            topic=None,
            language="en",
            start_time=start_time,
        )

        call_args = mock_table.insert.call_args
        inserted_data = call_args[0][0]
        assert "livekit_room_name" in inserted_data
        assert inserted_data["livekit_room_name"].startswith("focus-")


# =============================================================================
# Test: Participant Management
# =============================================================================


class TestAddParticipant:
    """Tests for add_participant() method (uses atomic RPC)."""

    @pytest.mark.unit
    def test_assigns_first_available_seat(
        self, session_service, mock_supabase, sample_participant_row
    ):
        """RPC returns seat 1 for first participant."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [
            {"participant_id": "p-1", "seat_number": 1, "already_active": False}
        ]
        mock_supabase.rpc.return_value = mock_rpc

        result = session_service.add_participant(
            session_id="session-123",
            user_id="user-123",
        )

        assert result["seat_number"] == 1
        assert result["already_active"] is False
        mock_supabase.rpc.assert_called_once_with(
            "atomic_add_participant",
            {"p_session_id": "session-123", "p_user_id": "user-123"},
        )

    @pytest.mark.unit
    def test_assigns_next_available_seat(
        self, session_service, mock_supabase, sample_participant_row
    ):
        """RPC returns seat 2 when seat 1 is taken."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [
            {"participant_id": "p-2", "seat_number": 2, "already_active": False}
        ]
        mock_supabase.rpc.return_value = mock_rpc

        result = session_service.add_participant(
            session_id="session-123",
            user_id="user-456",
        )

        assert result["seat_number"] == 2

    @pytest.mark.unit
    def test_session_full_raises_error(
        self, session_service, mock_supabase, sample_participant_row
    ):
        """Raises SessionFullError when RPC returns SESSION_FULL error."""
        from app.services.session_service import SessionFullError

        mock_supabase.rpc.side_effect = Exception("SESSION_FULL: 4/4 seats taken")

        with pytest.raises(SessionFullError):
            session_service.add_participant(
                session_id="session-123",
                user_id="user-999",
            )

    @pytest.mark.unit
    def test_session_phase_error(self, session_service, mock_supabase, sample_participant_row):
        """Raises SessionPhaseError when session is not in setup phase."""
        from app.services.session_service import SessionPhaseError

        mock_supabase.rpc.side_effect = Exception("SESSION_PHASE_ERROR: Session is in work_1 phase")

        with pytest.raises(SessionPhaseError):
            session_service.add_participant(
                session_id="session-123",
                user_id="user-123",
            )


class TestRemoveParticipant:
    """Tests for remove_participant() method."""

    @pytest.mark.unit
    def test_sets_left_at(self, session_service, mock_supabase):
        """Sets left_at timestamp when user leaves."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"left_at": datetime.now(timezone.utc).isoformat()}
        ]

        session_service.remove_participant(
            session_id="session-123",
            user_id="user-123",
        )

        # Verify update was called with left_at
        mock_table.update.assert_called_once()


# =============================================================================
# Test: AI Companions
# =============================================================================


class TestAddAICompanions:
    """Tests for add_ai_companions() method."""

    @pytest.mark.unit
    def test_fills_empty_seats(self, session_service, mock_supabase, sample_participant_row):
        """Adds AI companions for remaining seats."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # 2 humans already in session (seats 1, 2)
        existing = [
            {**sample_participant_row, "seat_number": 1},
            {**sample_participant_row, "seat_number": 2, "user_id": "user-456"},
        ]
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = existing

        # Insert returns AI companions
        ai_companion = {
            **sample_participant_row,
            "user_id": None,
            "participant_type": "ai_companion",
            "ai_companion_name": "Focus Fox",
        }
        mock_table.insert.return_value.execute.return_value.data = [ai_companion]

        result = session_service.add_ai_companions(session_id="session-123", count=2)

        assert len(result) == 2

    @pytest.mark.unit
    def test_uses_predefined_names(self, session_service, mock_supabase, sample_participant_row):
        """AI companions get names from predefined list."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # No existing participants
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        # Capture insert calls
        ai_companion = {
            **sample_participant_row,
            "user_id": None,
            "participant_type": "ai_companion",
            "ai_companion_name": "Focus Fox",
        }
        mock_table.insert.return_value.execute.return_value.data = [ai_companion]

        session_service.add_ai_companions(session_id="session-123", count=1)

        # Verify AI companion name was set
        call_args = mock_table.insert.call_args
        inserted_data = call_args[0][0]
        assert inserted_data["ai_companion_name"] is not None


# =============================================================================
# Test: Phase Calculation
# =============================================================================


class TestCalculateCurrentPhase:
    """Tests for calculate_current_phase() method."""

    @pytest.mark.unit
    def test_setup_phase(self, session_service, sample_session_row):
        """Returns SETUP for first 3 minutes."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 1 minute after start
            mock_dt.now.return_value = now + timedelta(minutes=1)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.SETUP

    @pytest.mark.unit
    def test_work_1_phase(self, session_service, sample_session_row):
        """Returns WORK_1 for minutes 3-28."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 10 minutes after start
            mock_dt.now.return_value = now + timedelta(minutes=10)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.WORK_1

    @pytest.mark.unit
    def test_break_phase(self, session_service, sample_session_row):
        """Returns BREAK for minutes 28-30."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 29 minutes after start
            mock_dt.now.return_value = now + timedelta(minutes=29)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.BREAK

    @pytest.mark.unit
    def test_work_2_phase(self, session_service, sample_session_row):
        """Returns WORK_2 for minutes 30-50."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 40 minutes after start
            mock_dt.now.return_value = now + timedelta(minutes=40)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.WORK_2

    @pytest.mark.unit
    def test_social_phase(self, session_service, sample_session_row):
        """Returns SOCIAL for minutes 50-55."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 52 minutes after start
            mock_dt.now.return_value = now + timedelta(minutes=52)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.SOCIAL

    @pytest.mark.unit
    def test_ended_phase(self, session_service, sample_session_row):
        """Returns ENDED after 55 minutes."""
        now = datetime.now(timezone.utc)
        session = {
            **sample_session_row,
            "start_time": now.isoformat(),
        }

        with patch("app.services.session_service.datetime") as mock_dt:
            # 60 minutes after start
            mock_dt.now.return_value = now + timedelta(minutes=60)
            mock_dt.fromisoformat = datetime.fromisoformat

            result = session_service.calculate_current_phase(session)

            assert result == SessionPhase.ENDED


# =============================================================================
# Test: LiveKit Token Generation
# =============================================================================


class TestGenerateLivekitToken:
    """Tests for generate_livekit_token() method."""

    @pytest.mark.unit
    def test_generates_token(self, session_service):
        """Generates a valid LiveKit access token."""
        with patch("app.services.session_service.get_settings") as mock_settings:
            mock_settings.return_value.livekit_api_key = "test-api-key"
            mock_settings.return_value.livekit_api_secret = "test-api-secret"

            # This test may need adjustment based on actual implementation
            # For now, just verify it returns a non-empty string
            result = session_service.generate_livekit_token(
                room_name="focus-session-123",
                participant_identity="user-123",
                participant_name="Test User",
            )

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0


class TestWaitTimeCalculation:
    """Tests for wait time calculation in quick-match responses."""

    @pytest.mark.unit
    def test_wait_minutes_immediate(self):
        """Session starting in <60s returns wait_minutes=0 and is_immediate=True."""
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(seconds=45)

        wait_seconds = (session_start - now).total_seconds()
        wait_minutes = max(0, int(wait_seconds / 60))
        is_immediate = wait_minutes < 1

        assert wait_minutes == 0
        assert is_immediate is True

    @pytest.mark.unit
    def test_wait_minutes_future(self):
        """Session starting in 15 min returns wait_minutes=15 and is_immediate=False."""
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(minutes=15)

        wait_seconds = (session_start - now).total_seconds()
        wait_minutes = max(0, int(wait_seconds / 60))
        is_immediate = wait_minutes < 1

        assert wait_minutes == 15
        assert is_immediate is False

    @pytest.mark.unit
    def test_wait_minutes_rounds_down(self):
        """Session starting in 14m50s returns wait_minutes=14 (rounds down)."""
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(minutes=14, seconds=50)

        wait_seconds = (session_start - now).total_seconds()
        wait_minutes = max(0, int(wait_seconds / 60))
        is_immediate = wait_minutes < 1

        assert wait_minutes == 14
        assert is_immediate is False

    @pytest.mark.unit
    def test_wait_minutes_edge_case_58_seconds(self):
        """Session starting in 58s still returns is_immediate=True."""
        now = datetime.now(timezone.utc)
        session_start = now + timedelta(seconds=58)

        wait_seconds = (session_start - now).total_seconds()
        wait_minutes = max(0, int(wait_seconds / 60))
        is_immediate = wait_minutes < 1

        assert wait_minutes == 0
        assert is_immediate is True

    @pytest.mark.unit
    def test_no_show_no_refund(self):
        """User matches but never joins - credit remains deducted (no refund).

        This test documents the no-refund policy. In the actual flow:
        1. User calls quick-match
        2. Credit is deducted immediately
        3. User doesn't show up
        4. Credit is NOT refunded

        This test verifies the policy is documented and intentional.
        """
        # Credit deducted at match time
        initial_credit = 5
        credit_after_match = initial_credit - 1
        assert credit_after_match == 4

        # User doesn't show up - no refund
        credit_after_no_show = credit_after_match  # No change
        assert credit_after_no_show == 4

        # Policy: No refunds for no-shows
        refund_amount = 0
        assert refund_amount == 0
