"""Unit tests for RatingService.get_rating_history (TDD)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models.rating import RatingHistoryResponse


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def rating_service(mock_supabase):
    """RatingService with mocked Supabase."""
    from app.services.rating_service import RatingService

    return RatingService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_history_row(
    rating: str = "green",
    days_ago: int = 0,
    row_id: str = "rating-1",
    session_id: str = "session-1",
) -> dict:
    """Create a rating row as returned from DB for history queries."""
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "id": row_id,
        "session_id": session_id,
        "rating": rating,
        "created_at": created_at.isoformat(),
    }


def _setup_history_mock(mock_supabase, aggregate_data, items_data):
    """Set up mock for get_rating_history which makes 2 queries on 'ratings' table.

    Query 1 (aggregate): .select("rating").eq().neq().execute()
    Query 2 (items):     .select("id, session_id, rating, created_at").eq().neq().order().range().execute()
    """
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    aggregate_chain = MagicMock()
    aggregate_chain.eq.return_value.neq.return_value.execute.return_value.data = aggregate_data

    items_chain = MagicMock()
    items_chain.eq.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.data = items_data
    items_chain.eq.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.count = len(
        items_data
    )

    call_count = {"n": 0}

    def route_select(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return aggregate_chain
        return items_chain

    mock_table.select.side_effect = route_select


# =============================================================================
# Tests
# =============================================================================


class TestGetRatingHistory:
    """Tests for get_rating_history() — paginated received rating history."""

    @pytest.mark.unit
    def test_empty_history_returns_zero_summary(self, rating_service, mock_supabase):
        """User with no ratings gets empty response with zero counts."""
        _setup_history_mock(mock_supabase, aggregate_data=[], items_data=[])

        result = rating_service.get_rating_history("user-1")

        assert isinstance(result, RatingHistoryResponse)
        assert result.summary.total_received == 0
        assert result.summary.green_count == 0
        assert result.summary.red_count == 0
        assert result.summary.green_percentage == 0.0
        assert result.items == []
        assert result.total == 0

    @pytest.mark.unit
    def test_all_green_history(self, rating_service, mock_supabase):
        """User with only green ratings shows 100% green."""
        greens = [{"rating": "green"} for _ in range(5)]
        items = [_make_history_row("green", days_ago=i, row_id=f"r-{i}") for i in range(5)]

        _setup_history_mock(mock_supabase, aggregate_data=greens, items_data=items)

        result = rating_service.get_rating_history("user-1")

        assert result.summary.total_received == 5
        assert result.summary.green_count == 5
        assert result.summary.red_count == 0
        assert result.summary.green_percentage == 100.0
        assert len(result.items) == 5

    @pytest.mark.unit
    def test_mixed_ratings_summary(self, rating_service, mock_supabase):
        """Mixed green/red ratings produce correct percentages."""
        agg = [{"rating": "green"}] * 3 + [{"rating": "red"}] * 2
        items = [_make_history_row("green", days_ago=i, row_id=f"g-{i}") for i in range(3)] + [
            _make_history_row("red", days_ago=i + 3, row_id=f"r-{i}") for i in range(2)
        ]

        _setup_history_mock(mock_supabase, aggregate_data=agg, items_data=items)

        result = rating_service.get_rating_history("user-1")

        assert result.summary.total_received == 5
        assert result.summary.green_count == 3
        assert result.summary.red_count == 2
        assert result.summary.green_percentage == 60.0

    @pytest.mark.unit
    def test_pagination_metadata(self, rating_service, mock_supabase):
        """Pagination metadata is returned correctly."""
        agg = [{"rating": "green"}] * 5
        items = [_make_history_row("green", days_ago=0, row_id=f"r-{i}") for i in range(2)]

        _setup_history_mock(mock_supabase, aggregate_data=agg, items_data=items)

        result = rating_service.get_rating_history("user-1", page=1, per_page=2)

        assert result.page == 1
        assert result.per_page == 2
        assert result.total == 5  # total from aggregate, not items len

    @pytest.mark.unit
    def test_items_have_no_rater_id(self, rating_service, mock_supabase):
        """Response items do not contain rater_id field (privacy)."""
        agg = [{"rating": "green"}]
        items = [_make_history_row("green", days_ago=0)]

        _setup_history_mock(mock_supabase, aggregate_data=agg, items_data=items)

        result = rating_service.get_rating_history("user-1")

        item = result.items[0]
        assert not hasattr(item, "rater_id")
        item_dict = item.model_dump()
        assert "rater_id" not in item_dict

    @pytest.mark.unit
    def test_items_contain_expected_fields(self, rating_service, mock_supabase):
        """Each item has id, session_id, rating, and created_at."""
        agg = [{"rating": "red"}]
        items = [_make_history_row("red", days_ago=1, row_id="r-1", session_id="s-1")]

        _setup_history_mock(mock_supabase, aggregate_data=agg, items_data=items)

        result = rating_service.get_rating_history("user-1")

        item = result.items[0]
        assert item.id == "r-1"
        assert item.session_id == "s-1"
        assert item.rating.value == "red"
        assert item.created_at is not None

    @pytest.mark.unit
    def test_default_pagination(self, rating_service, mock_supabase):
        """Default page=1, per_page=20 when not specified."""
        _setup_history_mock(mock_supabase, aggregate_data=[], items_data=[])

        result = rating_service.get_rating_history("user-1")

        assert result.page == 1
        assert result.per_page == 20
