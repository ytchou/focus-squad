"""Unit tests for LiveKit tasks (WU1 focus time + cleanup idempotency).

Tests:
- _calculate_focus_minutes() with various scenarios
- cleanup_ended_session idempotency guard
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.livekit_tasks import _calculate_focus_minutes

# =============================================================================
# _calculate_focus_minutes() Tests (WU1 regression)
# =============================================================================


class TestCalculateFocusMinutes:
    """Tests for focus time calculation logic."""

    @pytest.fixture
    def session(self):
        """Session that started 55 minutes ago."""
        start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()
        end = datetime.now(timezone.utc).isoformat()
        return {"start_time": start, "end_time": end}

    @pytest.mark.unit
    def test_uses_total_active_minutes_when_available(self, session):
        """Prefers webhook-tracked total_active_minutes over timestamp calc."""
        participant = {"total_active_minutes": 35, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 35

    @pytest.mark.unit
    def test_caps_active_minutes_at_45(self, session):
        """Caps total_active_minutes at 45 (max work time)."""
        participant = {"total_active_minutes": 60, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 45

    @pytest.mark.unit
    def test_returns_zero_when_no_data(self, session):
        """Returns 0 when no active minutes and no connected_at."""
        participant = {"total_active_minutes": None, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 0

    @pytest.mark.unit
    def test_returns_zero_for_zero_active_minutes(self, session):
        """Returns 0 when total_active_minutes is 0."""
        participant = {"total_active_minutes": 0, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 0

    @pytest.mark.unit
    def test_fallback_calculates_work_phase_overlap(self):
        """When no total_active_minutes, calculates overlap with work phases."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # User connected from minute 0 to minute 55 (full session)
        participant = {
            "total_active_minutes": None,
            "connected_at": start.isoformat(),
            "disconnected_at": end.isoformat(),
        }

        result = _calculate_focus_minutes(participant, session)
        # Work_1: 3-28 min = 25 min, Work_2: 30-50 min = 20 min, Total = 45 min
        assert result == 45

    @pytest.mark.unit
    def test_fallback_partial_session(self):
        """Calculates correct overlap for partial attendance."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # User joined at minute 10 (during work_1) and left at minute 35 (during work_2)
        connected = (start + timedelta(minutes=10)).isoformat()
        disconnected = (start + timedelta(minutes=35)).isoformat()

        participant = {
            "total_active_minutes": None,
            "connected_at": connected,
            "disconnected_at": disconnected,
        }

        result = _calculate_focus_minutes(participant, session)
        # Work_1 overlap: 10-28 min = 18 min
        # Work_2 overlap: 30-35 min = 5 min
        # Total = 23 min
        assert result == 23

    @pytest.mark.unit
    def test_fallback_no_disconnected_uses_end_time(self):
        """Uses session end_time when disconnected_at is None."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # Connected from start, never disconnected
        participant = {
            "total_active_minutes": None,
            "connected_at": start.isoformat(),
            "disconnected_at": None,
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 45  # Full work overlap

    @pytest.mark.unit
    def test_handles_z_suffix_timestamps(self):
        """Handles timestamps with Z suffix correctly."""
        session = {
            "start_time": "2025-02-07T10:00:00.000Z",
            "end_time": "2025-02-07T10:55:00.000Z",
        }

        participant = {
            "total_active_minutes": None,
            "connected_at": "2025-02-07T10:00:00.000Z",
            "disconnected_at": "2025-02-07T10:55:00.000Z",
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 45

    @pytest.mark.unit
    def test_no_overlap_when_connected_only_during_break(self):
        """Returns 0 if user was only connected during break phase."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=55)).isoformat(),
        }

        # Connected only during break (28-30 min)
        connected = (start + timedelta(minutes=28)).isoformat()
        disconnected = (start + timedelta(minutes=30)).isoformat()

        participant = {
            "total_active_minutes": None,
            "connected_at": connected,
            "disconnected_at": disconnected,
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 0


# =============================================================================
# cleanup_ended_session Idempotency Tests (WU2)
# =============================================================================


class TestCleanupIdempotency:
    """Tests for cleanup_ended_session idempotency guard."""

    @pytest.mark.unit
    def test_skips_already_cleaned_session(self):
        """Returns early if livekit_room_deleted_at is already set."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "livekit_room_name": "focus-abc",
            "livekit_room_deleted_at": "2025-02-07T10:00:00+00:00",
            "start_time": "2025-02-07T09:00:00+00:00",
        }

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [session_data]
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase):
            # Import here to avoid Celery task registration issues
            from app.tasks.livekit_tasks import cleanup_ended_session

            result = cleanup_ended_session("session-1")

        assert result["status"] == "already_cleaned_up"
        # Should NOT call update (skip cleanup)
        mock_table.update.assert_not_called()
