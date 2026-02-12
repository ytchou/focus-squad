"""Unit tests for StreakService (TDD — written before implementation).

Tests:
- get_weekly_streak() - happy path, no data returns defaults, after 3 bonus
- increment_session_count() - first session, crossing 3, crossing 5, no double award
"""

from unittest.mock import MagicMock

import pytest

from app.models.gamification import WeeklyStreakResponse
from app.services.streak_service import StreakService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """StreakService with mocked Supabase."""
    return StreakService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    """Create a chainable table mock."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.upsert.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


def _setup_tables(mock_supabase, table_names):
    """Configure table-specific mock routing."""
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


def _streak_row(
    session_count=1,
    week_start="2026-02-09",
    bonus_3=False,
    bonus_5=False,
    row_id="streak-1",
):
    return {
        "id": row_id,
        "user_id": "user-1",
        "session_count": session_count,
        "week_start": week_start,
        "bonus_3_awarded": bonus_3,
        "bonus_5_awarded": bonus_5,
    }


# =============================================================================
# get_weekly_streak()
# =============================================================================


class TestGetWeeklyStreak:
    def test_returns_streak_data(self, service, mock_supabase):
        """Returns current week's streak data."""
        tables = _setup_tables(mock_supabase, ["weekly_streaks"])
        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=2)]
        )

        result = service.get_weekly_streak("user-1")

        assert isinstance(result, WeeklyStreakResponse)
        assert result.session_count == 2
        assert result.next_bonus_at == 3
        assert result.bonus_3_awarded is False
        assert result.total_bonus_earned == 0

    def test_no_data_returns_defaults(self, service, mock_supabase):
        """When no streak row exists, returns zero defaults."""
        tables = _setup_tables(mock_supabase, ["weekly_streaks"])
        tables["weekly_streaks"].execute.return_value = MagicMock(data=[])

        result = service.get_weekly_streak("user-1")

        assert result.session_count == 0
        assert result.next_bonus_at == 3
        assert result.bonus_3_awarded is False
        assert result.bonus_5_awarded is False

    def test_after_3_bonus_next_is_5(self, service, mock_supabase):
        """After hitting 3-session bonus, next target is 5."""
        tables = _setup_tables(mock_supabase, ["weekly_streaks"])
        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=3, bonus_3=True)]
        )

        result = service.get_weekly_streak("user-1")

        assert result.session_count == 3
        assert result.next_bonus_at == 5
        assert result.total_bonus_earned == 1


# =============================================================================
# increment_session_count()
# =============================================================================


class TestIncrementSessionCount:
    def test_first_session_no_bonus(self, service, mock_supabase):
        """First session inserts new row with count=1, no bonus."""
        tables = _setup_tables(
            mock_supabase,
            ["weekly_streaks", "furniture_essence", "essence_transactions"],
        )

        # First call: fetch returns empty (no existing row)
        # Second call: insert returns new row
        call_count = {"n": 0}

        def streaks_execute(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return MagicMock(data=[])  # fetch: no existing row
            return MagicMock(data=[_streak_row(session_count=1)])  # insert

        tables["weekly_streaks"].execute.side_effect = streaks_execute

        result = service.increment_session_count("user-1")
        assert result is None

    def test_crossing_3_awards_bonus(self, service, mock_supabase):
        """Crossing 3-session threshold awards +1 essence."""
        tables = _setup_tables(
            mock_supabase,
            ["weekly_streaks", "furniture_essence", "essence_transactions"],
        )

        # fetch returns existing row with count=2 (will become 3)
        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=2)]
        )
        tables["furniture_essence"].execute.return_value = MagicMock(data=[{"balance": 6}])

        result = service.increment_session_count("user-1")

        assert result is not None
        assert result.bonus_essence == 1
        assert result.threshold_reached == 3
        assert result.new_balance == 6

    def test_crossing_5_awards_bonus(self, service, mock_supabase):
        """Crossing 5-session threshold awards +2 essence."""
        tables = _setup_tables(
            mock_supabase,
            ["weekly_streaks", "furniture_essence", "essence_transactions"],
        )

        # Existing row with count=4, bonus_3 already awarded
        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=4, bonus_3=True)]
        )
        tables["furniture_essence"].execute.return_value = MagicMock(data=[{"balance": 10}])

        result = service.increment_session_count("user-1")

        assert result is not None
        assert result.bonus_essence == 2
        assert result.threshold_reached == 5
        assert result.new_balance == 10

    def test_no_double_award(self, service, mock_supabase):
        """Already-awarded bonus is not given again."""
        tables = _setup_tables(
            mock_supabase,
            ["weekly_streaks", "furniture_essence", "essence_transactions"],
        )

        # count=3 with bonus_3 already awarded, not at 5 yet
        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=3, bonus_3=True)]
        )

        result = service.increment_session_count("user-1")
        assert result is None

    def test_both_bonuses_already_awarded(self, service, mock_supabase):
        """When both bonuses already awarded, no bonus returned."""
        tables = _setup_tables(
            mock_supabase,
            ["weekly_streaks", "furniture_essence", "essence_transactions"],
        )

        tables["weekly_streaks"].execute.return_value = MagicMock(
            data=[_streak_row(session_count=6, bonus_3=True, bonus_5=True)]
        )

        result = service.increment_session_count("user-1")
        assert result is None
