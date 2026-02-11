"""Unit tests for SessionService slot-related methods.

Tests:
- calculate_upcoming_slots() — returns 6 consecutive :00/:30 slots
- get_slot_estimates() — returns peak/moderate/off-peak estimates
- get_slot_queue_counts() — aggregates participant counts from DB
- get_user_sessions_at_slots() — returns slots user already joined
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import (
    MODERATE_HOUR_ESTIMATE,
    OFF_PEAK_HOUR_ESTIMATE,
    PEAK_HOUR_ESTIMATE,
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


# =============================================================================
# Test: calculate_upcoming_slots()
# =============================================================================


class TestCalculateUpcomingSlots:
    """Tests for calculate_upcoming_slots() method."""

    @pytest.mark.unit
    def test_returns_6_slots_by_default(self, session_service) -> None:
        """Returns exactly 6 slot times."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_upcoming_slots()

            assert len(result) == 6

    @pytest.mark.unit
    def test_slots_are_30min_apart(self, session_service) -> None:
        """Each slot is 30 minutes after the previous one."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 10, 5, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_upcoming_slots()

            for i in range(1, len(result)):
                diff = result[i] - result[i - 1]
                assert diff == timedelta(minutes=30)

    @pytest.mark.unit
    def test_all_slots_on_00_or_30(self, session_service) -> None:
        """Every slot time should be at :00 or :30."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 14, 12, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_upcoming_slots()

            for slot in result:
                assert slot.minute in (0, 30), f"Slot {slot} not on :00 or :30"
                assert slot.second == 0
                assert slot.microsecond == 0

    @pytest.mark.unit
    def test_custom_count(self, session_service) -> None:
        """Requesting count=3 returns 3 slots."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_upcoming_slots(count=3)

            assert len(result) == 3

    @pytest.mark.unit
    def test_first_slot_matches_calculate_next_slot(self, session_service) -> None:
        """First slot should be the same as calculate_next_slot()."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 10, 15, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            upcoming = session_service.calculate_upcoming_slots()
            next_slot = session_service.calculate_next_slot()

            assert upcoming[0] == next_slot

    @pytest.mark.unit
    def test_midnight_rollover(self, session_service) -> None:
        """Slots crossing midnight roll to next day."""
        with patch("app.services.session_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 11, 23, 5, 0, tzinfo=timezone.utc)
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = session_service.calculate_upcoming_slots()

            # First slot should be 23:30
            assert result[0].hour == 23
            assert result[0].minute == 30
            # Some later slots should be on day 12
            assert any(slot.day == 12 for slot in result)


# =============================================================================
# Test: get_slot_estimates()
# =============================================================================


class TestGetSlotEstimates:
    """Tests for get_slot_estimates() method."""

    @pytest.mark.unit
    def test_peak_hours_taiwan(self, session_service) -> None:
        """UTC hour 11 = Taiwan 19:00 (peak), should return PEAK_HOUR_ESTIMATE."""
        # Taiwan peak: 19:00-23:00 local = UTC 11:00-15:00
        slot_time = datetime(2026, 2, 11, 11, 0, 0, tzinfo=timezone.utc)
        result = session_service.get_slot_estimates([slot_time])

        assert result[slot_time.isoformat()] == PEAK_HOUR_ESTIMATE

    @pytest.mark.unit
    def test_moderate_hours_taiwan(self, session_service) -> None:
        """UTC hour 3 = Taiwan 11:00 (moderate), should return MODERATE_HOUR_ESTIMATE."""
        # Taiwan moderate: 09:00-18:00 local = UTC 01:00-10:00
        slot_time = datetime(2026, 2, 11, 3, 0, 0, tzinfo=timezone.utc)
        result = session_service.get_slot_estimates([slot_time])

        assert result[slot_time.isoformat()] == MODERATE_HOUR_ESTIMATE

    @pytest.mark.unit
    def test_off_peak_hours_taiwan(self, session_service) -> None:
        """UTC hour 18 = Taiwan 02:00 (off-peak), should return OFF_PEAK_HOUR_ESTIMATE."""
        # Taiwan off-peak: 00:00-08:00 local = UTC 16:00-24:00
        slot_time = datetime(2026, 2, 11, 18, 0, 0, tzinfo=timezone.utc)
        result = session_service.get_slot_estimates([slot_time])

        assert result[slot_time.isoformat()] == OFF_PEAK_HOUR_ESTIMATE

    @pytest.mark.unit
    def test_returns_estimate_for_each_slot(self, session_service) -> None:
        """Returns one estimate per slot time."""
        slot_times = [
            datetime(2026, 2, 11, 11, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 11, 11, 30, 0, tzinfo=timezone.utc),
            datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc),
        ]
        result = session_service.get_slot_estimates(slot_times)

        assert len(result) == 3

    @pytest.mark.unit
    def test_empty_input_returns_empty(self, session_service) -> None:
        """Empty slot list returns empty dict."""
        result = session_service.get_slot_estimates([])

        assert result == {}


# =============================================================================
# Test: get_slot_queue_counts()
# =============================================================================


class TestGetSlotQueueCounts:
    """Tests for get_slot_queue_counts() method."""

    @pytest.mark.unit
    def test_aggregates_participant_counts(self, session_service, mock_supabase) -> None:
        """Sums participants across multiple sessions for the same slot."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)
        iso = slot_time.isoformat()

        mock_query = MagicMock()
        mock_query.in_.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value.data = [
            {"id": "s-1", "start_time": iso, "session_participants": [{"count": 3}]},
            {"id": "s-2", "start_time": iso, "session_participants": [{"count": 2}]},
        ]
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_slot_queue_counts([slot_time])

        assert result[iso] == 5

    @pytest.mark.unit
    def test_empty_slots_returns_empty(self, session_service) -> None:
        """Empty slot list returns empty dict."""
        result = session_service.get_slot_queue_counts([])

        assert result == {}

    @pytest.mark.unit
    def test_zero_counts_when_no_sessions(self, session_service, mock_supabase) -> None:
        """Returns 0 for slots with no matching sessions."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)

        mock_query = MagicMock()
        mock_query.in_.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.execute.return_value.data = []
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_slot_queue_counts([slot_time])

        assert result[slot_time.isoformat()] == 0

    @pytest.mark.unit
    def test_normalizes_z_suffix(self, session_service, mock_supabase) -> None:
        """Handles Supabase returning Z suffix instead of +00:00."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)
        iso = slot_time.isoformat()

        mock_query = MagicMock()
        mock_query.in_.return_value = mock_query
        mock_query.neq.return_value = mock_query
        mock_query.eq.return_value = mock_query
        # Supabase returns Z suffix
        mock_query.execute.return_value.data = [
            {
                "id": "s-1",
                "start_time": "2026-02-11T14:00:00Z",
                "session_participants": [{"count": 2}],
            },
        ]
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_slot_queue_counts([slot_time])

        # Should still match despite Z vs +00:00 difference
        assert result[iso] == 2


# =============================================================================
# Test: get_user_sessions_at_slots()
# =============================================================================


class TestGetUserSessionsAtSlots:
    """Tests for get_user_sessions_at_slots() method."""

    @pytest.mark.unit
    def test_returns_matching_slots(self, session_service, mock_supabase) -> None:
        """Returns set of ISO times where user has sessions."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)
        iso = slot_time.isoformat()

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.is_.return_value = mock_query
        mock_query.execute.return_value.data = [
            {"sessions": {"start_time": iso}},
        ]
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_user_sessions_at_slots("user-123", [slot_time])

        assert iso in result

    @pytest.mark.unit
    def test_empty_slots_returns_empty(self, session_service) -> None:
        """Empty slot list returns empty set."""
        result = session_service.get_user_sessions_at_slots("user-123", [])

        assert result == set()

    @pytest.mark.unit
    def test_no_sessions_returns_empty(self, session_service, mock_supabase) -> None:
        """Returns empty set when user has no sessions."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.is_.return_value = mock_query
        mock_query.execute.return_value.data = []
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_user_sessions_at_slots("user-123", [slot_time])

        assert len(result) == 0

    @pytest.mark.unit
    def test_normalizes_z_suffix(self, session_service, mock_supabase) -> None:
        """Handles Z suffix from Supabase responses."""
        slot_time = datetime(2026, 2, 11, 14, 0, 0, tzinfo=timezone.utc)
        iso = slot_time.isoformat()

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.is_.return_value = mock_query
        mock_query.execute.return_value.data = [
            {"sessions": {"start_time": "2026-02-11T14:00:00Z"}},
        ]
        mock_supabase.table.return_value.select.return_value = mock_query

        result = session_service.get_user_sessions_at_slots("user-123", [slot_time])

        assert iso in result
