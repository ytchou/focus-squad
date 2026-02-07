"""Unit tests for webhook handlers (WU3).

Tests:
- is_session_completed() with various scenarios
- _parse_session_start_time() helper
- _handle_participant_left event processing
- _handle_room_finished event processing
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.routers.webhooks import (
    _handle_participant_left,
    _handle_room_finished,
    _parse_session_start_time,
    is_session_completed,
)

# =============================================================================
# is_session_completed() Tests
# =============================================================================


class TestIsSessionCompleted:
    """Tests for the is_session_completed() helper."""

    @pytest.fixture
    def session_start(self):
        """Session that started 55 minutes ago."""
        return datetime.now(timezone.utc) - timedelta(minutes=55)

    @pytest.mark.unit
    def test_completed_still_present_with_sufficient_time(self, session_start):
        """User still present (left_at=None) with 30 active minutes = completed."""
        participant = {"left_at": None, "total_active_minutes": 30}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_insufficient_active_minutes(self, session_start):
        """User present but only 10 active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": 10}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_not_completed_zero_active_minutes(self, session_start):
        """User with 0 active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": 0}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_not_completed_null_active_minutes(self, session_start):
        """User with null active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": None}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_completed_left_after_minute_50(self, session_start):
        """User left at minute 52 with 25 active minutes = completed."""
        left_at = (session_start + timedelta(minutes=52)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_left_before_minute_50(self, session_start):
        """User left at minute 40 with 30 active minutes = not completed."""
        left_at = (session_start + timedelta(minutes=40)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 30}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_completed_left_exactly_at_minute_50(self, session_start):
        """User left exactly at minute 50 = completed (boundary case)."""
        left_at = (session_start + timedelta(minutes=50)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_left_at_minute_49(self, session_start):
        """User left at minute 49 = not completed (just before boundary)."""
        left_at = (session_start + timedelta(minutes=49)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_handles_z_suffix_in_left_at(self, session_start):
        """Handles ISO timestamps ending with Z."""
        left_at_dt = session_start + timedelta(minutes=52)
        left_at = left_at_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_minimum_active_minutes_boundary(self, session_start):
        """Exactly 20 active minutes = completed (boundary)."""
        participant = {"left_at": None, "total_active_minutes": 20}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_below_minimum_active_minutes(self, session_start):
        """19 active minutes = not completed (just below boundary)."""
        participant = {"left_at": None, "total_active_minutes": 19}
        assert is_session_completed(participant, session_start) is False


# =============================================================================
# _parse_session_start_time() Tests
# =============================================================================


class TestParseSessionStartTime:
    """Tests for the _parse_session_start_time() helper."""

    @pytest.mark.unit
    def test_parses_iso_format(self):
        """Parses standard ISO format with timezone."""
        result = _parse_session_start_time("2025-02-07T10:00:00+00:00")
        assert result.hour == 10
        assert result.tzinfo is not None

    @pytest.mark.unit
    def test_parses_z_suffix(self):
        """Parses ISO format with Z suffix."""
        result = _parse_session_start_time("2025-02-07T10:00:00.000Z")
        assert result.hour == 10

    @pytest.mark.unit
    def test_returns_datetime_unchanged(self):
        """Returns datetime objects unchanged."""
        dt = datetime(2025, 2, 7, 10, 0, tzinfo=timezone.utc)
        result = _parse_session_start_time(dt)
        assert result is dt


# =============================================================================
# _handle_participant_left Tests
# =============================================================================


class TestHandleParticipantLeft:
    """Tests for the _handle_participant_left() handler."""

    @pytest.fixture
    def mock_supabase(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def left_event(self):
        """Standard participant_left event data."""
        return {
            "event": "participant_left",
            "room": {"name": "focus-abc123"},
            "participant": {"identity": "user-123", "sid": "PA_123"},
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculates_active_minutes_from_connection(self, left_event):
        """Calculates active minutes from connected_at to now."""
        mock_supabase = MagicMock()

        # Connected 30 minutes ago
        connected_at = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        # Cache table mocks by name
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]

        participants_mock = MagicMock()
        # select(...).eq(...).eq(...).execute() for participant lookup
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "p-1",
                "connected_at": connected_at,
                "total_active_minutes": 0,
                "disconnect_count": 0,
            }
        ]
        # update(...).eq(...).execute() for updating
        participants_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_left(left_event)

        # Verify update was called on the participants table
        assert participants_mock.update.called
        update_data = participants_mock.update.call_args[0][0]
        assert update_data["is_connected"] is False
        assert update_data["total_active_minutes"] >= 29  # ~30 min connected

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_room_name(self):
        """Returns silently if room name is missing."""
        event = {"event": "participant_left", "room": {}, "participant": {"identity": "u-1"}}
        # Should not raise
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_participant_left(event)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_identity(self):
        """Returns silently if participant identity is missing."""
        event = {"event": "participant_left", "room": {"name": "room-1"}, "participant": {}}
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_participant_left(event)
            mock_get.assert_not_called()


# =============================================================================
# _handle_room_finished Tests
# =============================================================================


class TestHandleRoomFinished:
    """Tests for the _handle_room_finished() handler."""

    @pytest.fixture
    def room_finished_event(self):
        return {
            "event": "room_finished",
            "room": {"name": "focus-abc123", "sid": "RM_123"},
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_marks_session_ended(self, room_finished_event):
        """Sets current_phase to 'ended' when room finishes."""
        mock_supabase = MagicMock()

        session_start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()

        # Cache table mocks
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1", "start_time": session_start, "current_phase": "social"}
        ]
        sessions_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        participants_mock = MagicMock()
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache.get(name, MagicMock())

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(room_finished_event)

        # Verify session was marked as ended
        sessions_mock.update.assert_called()
        update_data = sessions_mock.update.call_args[0][0]
        assert update_data["current_phase"] == "ended"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_awards_essence_to_qualifying_participants(self, room_finished_event):
        """Awards essence to participants who completed the session."""
        mock_supabase = MagicMock()

        session_start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()

        # Cache table mocks
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1", "start_time": session_start, "current_phase": "social"}
        ]
        sessions_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        participants_mock = MagicMock()
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "p-1",
                "user_id": "user-1",
                "left_at": None,
                "total_active_minutes": 30,
                "essence_earned": False,
            },
            {
                "id": "p-2",
                "user_id": "user-2",
                "left_at": None,
                "total_active_minutes": 10,
                "essence_earned": False,
            },
        ]
        participants_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        essence_mock = MagicMock()
        essence_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"balance": 5, "total_earned": 5}
        ]
        essence_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        transactions_mock = MagicMock()
        transactions_mock.insert.return_value.execute.return_value.data = [{}]

        table_cache = {
            "sessions": sessions_mock,
            "session_participants": participants_mock,
            "furniture_essence": essence_mock,
            "essence_transactions": transactions_mock,
        }
        mock_supabase.table.side_effect = lambda name: table_cache.get(name, MagicMock())

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(room_finished_event)

        # Verify essence_transactions.insert was called (for qualifying user-1)
        assert transactions_mock.insert.called
        # Verify participant essence_earned was marked
        assert participants_mock.update.called

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_room_name(self):
        """Returns silently if room name is missing."""
        event = {"event": "room_finished", "room": {}}
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_room_finished(event)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_session_not_found(self):
        """Returns silently if session not found for room."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        event = {"event": "room_finished", "room": {"name": "nonexistent-room"}}

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(event)

        # Should not call update (no session found)
        mock_table.update.assert_not_called()
