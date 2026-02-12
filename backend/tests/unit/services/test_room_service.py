"""Unit tests for RoomService.

Tests:
- ensure_room() - existing room found, new room created
- update_layout() - empty placements, valid placement, not owned, out of bounds, overlaps
- _check_visitors() - no placed items, below threshold, meets threshold, already discovered, past cooldown
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models.room import (
    InvalidPlacementError,
    RoomPlacement,
    RoomServiceError,
    RoomState,
    VisitorResult,
)
from app.services.room_service import RoomService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """RoomService with mocked Supabase."""
    return RoomService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    """Create a chainable table mock."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.is_.return_value = mock
    mock.not_ = MagicMock()
    mock.not_.is_.return_value = mock
    mock.order.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


def _setup_tables(mock_supabase, table_names):
    """Configure table-specific mock routing with pre-populated table mocks."""
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


def _sample_room_row(user_id="user-123", layout=None):
    """Sample user_room row."""
    return {
        "user_id": user_id,
        "room_type": "starter",
        "layout": layout or [],
        "active_companion": None,
        "updated_at": "2026-02-01T00:00:00Z",
    }


def _sample_owned_item(inv_id="inv-1", item_id="item-1", size_w=1, size_h=1):
    """Sample user_items row with joined item size data."""
    return {
        "id": inv_id,
        "item_id": item_id,
        "items": {"size_w": size_w, "size_h": size_h},
    }


# =============================================================================
# TestEnsureRoom
# =============================================================================


class TestEnsureRoom:
    """Tests for ensure_room() method."""

    @pytest.mark.unit
    def test_existing_room_found(self, service, mock_supabase) -> None:
        """Returns existing room when row is found."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        room_row = _sample_room_row()
        tables["user_room"].execute.return_value = MagicMock(data=[room_row])

        result = service.ensure_room("user-123")

        assert isinstance(result, RoomState)
        assert result.user_id == "user-123"
        assert result.room_type == "starter"
        assert result.layout == []

    @pytest.mark.unit
    def test_existing_room_with_layout(self, service, mock_supabase) -> None:
        """Returns existing room with layout placements parsed."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        layout = [{"inventory_id": "inv-1", "grid_x": 0, "grid_y": 0, "rotation": 0}]
        room_row = _sample_room_row(layout=layout)
        tables["user_room"].execute.return_value = MagicMock(data=[room_row])

        result = service.ensure_room("user-123")

        assert len(result.layout) == 1
        assert isinstance(result.layout[0], RoomPlacement)
        assert result.layout[0].inventory_id == "inv-1"

    @pytest.mark.unit
    def test_new_room_created(self, service, mock_supabase) -> None:
        """Creates new room when none exists."""
        tables = _setup_tables(mock_supabase, ["user_room"])

        # First call: select returns empty (no room)
        # Second call: insert returns new row
        execute_results = [
            MagicMock(data=[]),  # select
            MagicMock(data=[_sample_room_row()]),  # insert
        ]
        tables["user_room"].execute.side_effect = execute_results

        result = service.ensure_room("user-123")

        assert isinstance(result, RoomState)
        assert result.user_id == "user-123"
        assert result.room_type == "starter"
        assert result.layout == []

        # Verify insert was called with correct defaults
        tables["user_room"].insert.assert_called_once_with(
            {"user_id": "user-123", "room_type": "starter", "layout": []}
        )

    @pytest.mark.unit
    def test_new_room_insert_fails(self, service, mock_supabase) -> None:
        """Raises RoomServiceError when insert fails."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        execute_results = [
            MagicMock(data=[]),  # select
            MagicMock(data=[]),  # insert fails (empty data)
        ]
        tables["user_room"].execute.side_effect = execute_results

        with pytest.raises(RoomServiceError, match="Failed to create room"):
            service.ensure_room("user-123")


# =============================================================================
# TestUpdateLayout
# =============================================================================


class TestUpdateLayout:
    """Tests for update_layout() method."""

    @pytest.mark.unit
    def test_empty_placements_clears_layout(self, service, mock_supabase) -> None:
        """Empty placements list clears the layout."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        # After clearing, ensure_room returns the cleared room
        tables["user_room"].execute.return_value = MagicMock(data=[_sample_room_row()])

        result = service.update_layout("user-123", [])

        assert isinstance(result, RoomState)
        # Verify update was called with empty layout
        tables["user_room"].update.assert_called_once()
        update_data = tables["user_room"].update.call_args.args[0]
        assert update_data["layout"] == []

    @pytest.mark.unit
    def test_valid_placement(self, service, mock_supabase) -> None:
        """Valid placement within grid bounds and owned items succeeds."""
        tables = _setup_tables(mock_supabase, ["user_items", "user_room"])

        # user_items: item is owned
        owned = _sample_owned_item(inv_id="inv-1", size_w=1, size_h=1)
        tables["user_items"].execute.return_value = MagicMock(data=[owned])

        # After update, ensure_room returns updated room
        layout_data = [{"inventory_id": "inv-1", "grid_x": 2, "grid_y": 1, "rotation": 0}]
        tables["user_room"].execute.return_value = MagicMock(
            data=[_sample_room_row(layout=layout_data)]
        )

        placements = [RoomPlacement(inventory_id="inv-1", grid_x=2, grid_y=1, rotation=0)]
        result = service.update_layout("user-123", placements)

        assert isinstance(result, RoomState)
        assert len(result.layout) == 1

    @pytest.mark.unit
    def test_item_not_owned_raises_error(self, service, mock_supabase) -> None:
        """Raises InvalidPlacementError when item is not owned by user."""
        tables = _setup_tables(mock_supabase, ["user_items"])
        # user_items: no items owned
        tables["user_items"].execute.return_value = MagicMock(data=[])

        placements = [RoomPlacement(inventory_id="inv-999", grid_x=0, grid_y=0)]

        with pytest.raises(InvalidPlacementError, match="not owned"):
            service.update_layout("user-123", placements)

    @pytest.mark.unit
    def test_out_of_bounds_x_raises_error(self, service, mock_supabase) -> None:
        """Raises InvalidPlacementError when item exceeds grid width."""
        tables = _setup_tables(mock_supabase, ["user_items"])
        # 2-wide item placed at x=5 (needs 5+2=7, max is 6)
        owned = _sample_owned_item(inv_id="inv-1", size_w=2, size_h=1)
        tables["user_items"].execute.return_value = MagicMock(data=[owned])

        placements = [RoomPlacement(inventory_id="inv-1", grid_x=5, grid_y=0)]

        with pytest.raises(InvalidPlacementError, match="exceeds grid width"):
            service.update_layout("user-123", placements)

    @pytest.mark.unit
    def test_out_of_bounds_y_raises_error(self, service, mock_supabase) -> None:
        """Raises InvalidPlacementError when item exceeds grid height."""
        tables = _setup_tables(mock_supabase, ["user_items"])
        # 2-tall item placed at y=3 (needs 3+2=5, max is 4)
        owned = _sample_owned_item(inv_id="inv-1", size_w=1, size_h=2)
        tables["user_items"].execute.return_value = MagicMock(data=[owned])

        placements = [RoomPlacement(inventory_id="inv-1", grid_x=0, grid_y=3)]

        with pytest.raises(InvalidPlacementError, match="exceeds grid height"):
            service.update_layout("user-123", placements)

    @pytest.mark.unit
    def test_overlapping_items_raises_error(self, service, mock_supabase) -> None:
        """Raises InvalidPlacementError when two items occupy the same cell."""
        tables = _setup_tables(mock_supabase, ["user_items"])
        owned_items = [
            _sample_owned_item(inv_id="inv-1", item_id="item-1", size_w=2, size_h=1),
            _sample_owned_item(inv_id="inv-2", item_id="item-2", size_w=1, size_h=1),
        ]
        tables["user_items"].execute.return_value = MagicMock(data=owned_items)

        # inv-1 occupies (0,0) and (1,0); inv-2 also at (1,0)
        placements = [
            RoomPlacement(inventory_id="inv-1", grid_x=0, grid_y=0),
            RoomPlacement(inventory_id="inv-2", grid_x=1, grid_y=0),
        ]

        with pytest.raises(InvalidPlacementError, match="Overlapping"):
            service.update_layout("user-123", placements)

    @pytest.mark.unit
    def test_valid_non_overlapping_multi_item(self, service, mock_supabase) -> None:
        """Multiple items placed without overlap succeed."""
        tables = _setup_tables(mock_supabase, ["user_items", "user_room"])
        owned_items = [
            _sample_owned_item(inv_id="inv-1", item_id="item-1", size_w=2, size_h=1),
            _sample_owned_item(inv_id="inv-2", item_id="item-2", size_w=1, size_h=1),
        ]
        tables["user_items"].execute.return_value = MagicMock(data=owned_items)

        # inv-1 at (0,0)-(1,0), inv-2 at (3,0) -- no overlap
        tables["user_room"].execute.return_value = MagicMock(data=[_sample_room_row()])

        placements = [
            RoomPlacement(inventory_id="inv-1", grid_x=0, grid_y=0),
            RoomPlacement(inventory_id="inv-2", grid_x=3, grid_y=0),
        ]

        result = service.update_layout("user-123", placements)
        assert isinstance(result, RoomState)


# =============================================================================
# TestCheckVisitors
# =============================================================================


class TestCheckVisitors:
    """Tests for _check_visitors() method."""

    @pytest.mark.unit
    def test_no_placed_items_returns_empty(self, service, mock_supabase) -> None:
        """Returns empty list when no items are placed."""
        _setup_tables(mock_supabase, ["user_companions"])

        result = service._check_visitors(
            user_id="user-123",
            layout=[],
            inventory_items=[],
        )

        assert result == []

    @pytest.mark.unit
    def test_below_threshold_returns_empty(self, service, mock_supabase) -> None:
        """Returns empty when placed items do not meet companion threshold."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        # Only 1 item with "height" tag -- owl needs 3 matching items
        layout = [{"inventory_id": "inv-1"}]
        inventory_items = [
            {"id": "inv-1", "_shop_item": {"attraction_tags": ["height"]}},
        ]

        # First: existing companions query, second: scheduled visitors query
        execute_results = [
            MagicMock(data=[]),  # existing companions
            MagicMock(data=[]),  # scheduled visitors
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service._check_visitors(
            user_id="user-123",
            layout=layout,
            inventory_items=inventory_items,
        )

        assert result == []

    @pytest.mark.unit
    def test_meets_threshold_creates_visitor(self, service, mock_supabase) -> None:
        """Creates visitor when placed items meet companion threshold."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        # 3 items with "height" or "shiny" tags -- owl threshold is 3
        layout = [
            {"inventory_id": "inv-1"},
            {"inventory_id": "inv-2"},
            {"inventory_id": "inv-3"},
        ]
        inventory_items = [
            {"id": "inv-1", "_shop_item": {"attraction_tags": ["height"]}},
            {"id": "inv-2", "_shop_item": {"attraction_tags": ["shiny"]}},
            {"id": "inv-3", "_shop_item": {"attraction_tags": ["height", "warm"]}},
        ]

        # existing companions: empty
        # insert visitor: succeeds (may be called multiple times for different companions)
        # scheduled visitors: empty
        execute_results = [
            MagicMock(data=[]),  # existing companions check
            MagicMock(data=[]),  # insert owl
            MagicMock(data=[]),  # insert fox (warm tags meet threshold too)
            MagicMock(data=[]),  # scheduled visitors query
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service._check_visitors(
            user_id="user-123",
            layout=layout,
            inventory_items=inventory_items,
        )

        assert len(result) >= 1
        owl_results = [r for r in result if r.companion_type == "owl"]
        assert len(owl_results) == 1
        assert isinstance(owl_results[0], VisitorResult)

        # Verify insert was called for owl
        insert_calls = tables["user_companions"].insert.call_args_list
        owl_inserts = [c for c in insert_calls if c.args[0].get("companion_type") == "owl"]
        assert len(owl_inserts) == 1
        assert owl_inserts[0].args[0]["is_starter"] is False

    @pytest.mark.unit
    def test_already_discovered_companion_skipped(self, service, mock_supabase) -> None:
        """Skips companion type that user already has."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        # 3 items with owl-preferred tags
        layout = [
            {"inventory_id": "inv-1"},
            {"inventory_id": "inv-2"},
            {"inventory_id": "inv-3"},
        ]
        inventory_items = [
            {"id": "inv-1", "_shop_item": {"attraction_tags": ["height"]}},
            {"id": "inv-2", "_shop_item": {"attraction_tags": ["shiny"]}},
            {"id": "inv-3", "_shop_item": {"attraction_tags": ["height"]}},
        ]

        # User already has owl
        execute_results = [
            MagicMock(data=[{"companion_type": "owl"}]),  # already discovered
            MagicMock(data=[]),  # scheduled visitors query
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service._check_visitors(
            user_id="user-123",
            layout=layout,
            inventory_items=inventory_items,
        )

        owl_results = [r for r in result if r.companion_type == "owl"]
        assert len(owl_results) == 0

    @pytest.mark.unit
    def test_scheduled_visitor_past_cooldown_returned(self, service, mock_supabase) -> None:
        """Scheduled visitors past their cooldown time are included in results."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        # No items placed that meet thresholds
        layout = [{"inventory_id": "inv-1"}]
        inventory_items = [
            {"id": "inv-1", "_shop_item": {"attraction_tags": []}},
        ]

        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

        execute_results = [
            MagicMock(data=[]),  # existing companions
            # Scheduled visitors: one past cooldown
            MagicMock(
                data=[
                    {
                        "companion_type": "fox",
                        "visit_scheduled_at": past_time,
                    }
                ]
            ),
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service._check_visitors(
            user_id="user-123",
            layout=layout,
            inventory_items=inventory_items,
        )

        fox_results = [r for r in result if r.companion_type == "fox"]
        assert len(fox_results) == 1

    @pytest.mark.unit
    def test_scheduled_visitor_not_yet_ready_excluded(self, service, mock_supabase) -> None:
        """Scheduled visitors still in cooldown are not included."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        layout = [{"inventory_id": "inv-1"}]
        inventory_items = [
            {"id": "inv-1", "_shop_item": {"attraction_tags": []}},
        ]

        future_time = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()

        execute_results = [
            MagicMock(data=[]),  # existing companions
            MagicMock(
                data=[
                    {
                        "companion_type": "turtle",
                        "visit_scheduled_at": future_time,
                    }
                ]
            ),
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service._check_visitors(
            user_id="user-123",
            layout=layout,
            inventory_items=inventory_items,
        )

        turtle_results = [r for r in result if r.companion_type == "turtle"]
        assert len(turtle_results) == 0
