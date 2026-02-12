"""Unit tests for EssenceService.

Tests:
- get_balance() - happy path, no balance row returns zeros
- get_shop_items() - no filter, filter by category, filter by tier, empty result
- buy_item() - successful purchase, insufficient balance, item not found, item unavailable
- get_inventory() - happy path with multiple items, empty inventory
"""

from unittest.mock import MagicMock

import pytest

from app.models.room import (
    EssenceBalance,
    InsufficientEssenceError,
    InventoryItem,
    ItemNotFoundError,
    ShopItem,
)
from app.services.essence_service import EssenceService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """EssenceService with mocked Supabase."""
    return EssenceService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    """Create a chainable table mock that supports select/eq/in_/order/insert/update."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


def _setup_tables(mock_supabase, table_names):
    """Configure table-specific mock routing with pre-populated table mocks.

    Args:
        mock_supabase: The mock supabase client.
        table_names: List of table names to pre-populate.

    Returns:
        Dict mapping table name to its MagicMock.
    """
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


def _sample_item(
    item_id="item-1",
    name="Cozy Lamp",
    category="furniture",
    tier="basic",
    cost=5,
    is_available=True,
    is_purchasable=True,
):
    """Sample item row from the items table."""
    return {
        "id": item_id,
        "name": name,
        "name_zh": None,
        "description": "A warm lamp",
        "description_zh": None,
        "category": category,
        "rarity": "common",
        "image_url": None,
        "essence_cost": cost,
        "tier": tier,
        "size_w": 1,
        "size_h": 1,
        "attraction_tags": ["warm"],
        "is_available": is_available,
        "is_purchasable": is_purchasable,
    }


def _sample_balance(balance=10, total_earned=20, total_spent=10):
    """Sample furniture_essence row."""
    return {
        "balance": balance,
        "total_earned": total_earned,
        "total_spent": total_spent,
    }


def _sample_user_item(inv_id="inv-1", item_id="item-1"):
    """Sample user_items row."""
    return {
        "id": inv_id,
        "item_id": item_id,
        "user_id": "user-123",
        "acquired_at": "2026-02-01T00:00:00Z",
        "acquisition_type": "purchased",
    }


# =============================================================================
# TestGetBalance
# =============================================================================


class TestGetBalance:
    """Tests for get_balance() method."""

    @pytest.mark.unit
    def test_returns_balance(self, service, mock_supabase) -> None:
        """Returns EssenceBalance when record exists."""
        tables = _setup_tables(mock_supabase, ["furniture_essence"])
        tables["furniture_essence"].execute.return_value = MagicMock(
            data=[_sample_balance(balance=15, total_earned=30, total_spent=15)]
        )

        result = service.get_balance("user-123")

        assert isinstance(result, EssenceBalance)
        assert result.balance == 15
        assert result.total_earned == 30
        assert result.total_spent == 15

    @pytest.mark.unit
    def test_no_balance_returns_zeros(self, service, mock_supabase) -> None:
        """Returns zero balance when no row exists for user."""
        tables = _setup_tables(mock_supabase, ["furniture_essence"])
        tables["furniture_essence"].execute.return_value = MagicMock(data=[])

        result = service.get_balance("user-new")

        assert isinstance(result, EssenceBalance)
        assert result.balance == 0
        assert result.total_earned == 0
        assert result.total_spent == 0


# =============================================================================
# TestGetShopItems
# =============================================================================


class TestGetShopItems:
    """Tests for get_shop_items() method."""

    @pytest.mark.unit
    def test_returns_all_available_items(self, service, mock_supabase) -> None:
        """Returns all available purchasable items when no filters given."""
        tables = _setup_tables(mock_supabase, ["items"])
        items = [
            _sample_item(item_id="item-1", tier="basic", cost=3),
            _sample_item(item_id="item-2", tier="standard", cost=8),
        ]
        tables["items"].execute.return_value = MagicMock(data=items)

        result = service.get_shop_items()

        assert len(result) == 2
        assert all(isinstance(i, ShopItem) for i in result)
        assert result[0].tier == "basic"
        assert result[1].tier == "standard"

    @pytest.mark.unit
    def test_filter_by_category(self, service, mock_supabase) -> None:
        """Filters items by category."""
        tables = _setup_tables(mock_supabase, ["items"])
        tables["items"].execute.return_value = MagicMock(data=[_sample_item(category="decor")])

        result = service.get_shop_items(category="decor")

        assert len(result) == 1
        assert result[0].category == "decor"

    @pytest.mark.unit
    def test_filter_by_tier(self, service, mock_supabase) -> None:
        """Filters items by tier."""
        tables = _setup_tables(mock_supabase, ["items"])
        tables["items"].execute.return_value = MagicMock(
            data=[_sample_item(tier="premium", cost=20)]
        )

        result = service.get_shop_items(tier="premium")

        assert len(result) == 1
        assert result[0].tier == "premium"

    @pytest.mark.unit
    def test_empty_result(self, service, mock_supabase) -> None:
        """Returns empty list when no items match."""
        tables = _setup_tables(mock_supabase, ["items"])
        tables["items"].execute.return_value = MagicMock(data=[])

        result = service.get_shop_items(category="nonexistent")

        assert result == []

    @pytest.mark.unit
    def test_sorts_by_tier_then_cost(self, service, mock_supabase) -> None:
        """Items are sorted by tier order (basic < standard < premium) then cost."""
        tables = _setup_tables(mock_supabase, ["items"])
        items = [
            _sample_item(item_id="i-3", tier="premium", cost=15),
            _sample_item(item_id="i-1", tier="basic", cost=5),
            _sample_item(item_id="i-2", tier="basic", cost=3),
            _sample_item(item_id="i-4", tier="standard", cost=10),
        ]
        tables["items"].execute.return_value = MagicMock(data=items)

        result = service.get_shop_items()

        assert [r.id for r in result] == ["i-2", "i-1", "i-4", "i-3"]


# =============================================================================
# TestBuyItem
# =============================================================================


class TestBuyItem:
    """Tests for buy_item() method."""

    @pytest.mark.unit
    def test_successful_purchase(self, service, mock_supabase) -> None:
        """Purchases item: deducts balance, logs transaction, adds to inventory."""
        tables = _setup_tables(
            mock_supabase,
            ["items", "furniture_essence", "essence_transactions", "user_items"],
        )

        item = _sample_item(item_id="item-1", cost=5)
        tables["items"].execute.return_value = MagicMock(data=[item])

        tables["furniture_essence"].execute.return_value = MagicMock(
            data=[{"balance": 10, "total_spent": 5}]
        )

        tables["essence_transactions"].execute.return_value = MagicMock(data=[{}])

        inv_row = {
            "id": "inv-new",
            "item_id": "item-1",
            "acquired_at": "2026-02-12T00:00:00Z",
            "acquisition_type": "purchased",
        }
        tables["user_items"].execute.return_value = MagicMock(data=[inv_row])

        result = service.buy_item("user-123", "item-1")

        assert isinstance(result, InventoryItem)
        assert result.item_id == "item-1"
        assert result.acquisition_type == "purchased"
        assert result.item is not None
        assert result.item.essence_cost == 5

        # Verify balance was updated
        tables["furniture_essence"].update.assert_called_once_with(
            {"balance": 5, "total_spent": 10}
        )

        # Verify transaction was logged
        tables["essence_transactions"].insert.assert_called_once()
        tx_data = tables["essence_transactions"].insert.call_args.args[0]
        assert tx_data["user_id"] == "user-123"
        assert tx_data["amount"] == -5
        assert tx_data["transaction_type"] == "item_purchase"
        assert tx_data["related_item_id"] == "item-1"

    @pytest.mark.unit
    def test_item_not_found(self, service, mock_supabase) -> None:
        """Raises ItemNotFoundError when item does not exist."""
        tables = _setup_tables(mock_supabase, ["items"])
        tables["items"].execute.return_value = MagicMock(data=[])

        with pytest.raises(ItemNotFoundError, match="not found"):
            service.buy_item("user-123", "nonexistent-item")

    @pytest.mark.unit
    def test_item_not_available(self, service, mock_supabase) -> None:
        """Raises ItemNotFoundError when item is not available for purchase."""
        tables = _setup_tables(mock_supabase, ["items"])
        item = _sample_item(is_available=False)
        tables["items"].execute.return_value = MagicMock(data=[item])

        with pytest.raises(ItemNotFoundError, match="not available"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_item_not_purchasable(self, service, mock_supabase) -> None:
        """Raises ItemNotFoundError when item is not purchasable."""
        tables = _setup_tables(mock_supabase, ["items"])
        item = _sample_item(is_purchasable=False)
        tables["items"].execute.return_value = MagicMock(data=[item])

        with pytest.raises(ItemNotFoundError, match="not available"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_insufficient_essence_no_balance_row(self, service, mock_supabase) -> None:
        """Raises InsufficientEssenceError when user has no essence row."""
        tables = _setup_tables(mock_supabase, ["items", "furniture_essence"])
        tables["items"].execute.return_value = MagicMock(data=[_sample_item(cost=5)])
        tables["furniture_essence"].execute.return_value = MagicMock(data=[])

        with pytest.raises(InsufficientEssenceError, match="No essence balance"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_insufficient_essence_low_balance(self, service, mock_supabase) -> None:
        """Raises InsufficientEssenceError when balance is too low."""
        tables = _setup_tables(mock_supabase, ["items", "furniture_essence"])
        tables["items"].execute.return_value = MagicMock(data=[_sample_item(cost=10)])
        tables["furniture_essence"].execute.return_value = MagicMock(
            data=[{"balance": 3, "total_spent": 7}]
        )

        with pytest.raises(InsufficientEssenceError, match="need 10, have 3"):
            service.buy_item("user-123", "item-1")


# =============================================================================
# TestGetInventory
# =============================================================================


class TestGetInventory:
    """Tests for get_inventory() method."""

    @pytest.mark.unit
    def test_returns_inventory_with_items(self, service, mock_supabase) -> None:
        """Returns inventory items joined with catalog data."""
        tables = _setup_tables(mock_supabase, ["user_items", "items"])

        user_items = [
            _sample_user_item(inv_id="inv-1", item_id="item-1"),
            _sample_user_item(inv_id="inv-2", item_id="item-2"),
        ]
        tables["user_items"].execute.return_value = MagicMock(data=user_items)

        catalog_items = [
            _sample_item(item_id="item-1", name="Cozy Lamp"),
            _sample_item(item_id="item-2", name="Wooden Shelf"),
        ]
        tables["items"].execute.return_value = MagicMock(data=catalog_items)

        result = service.get_inventory("user-123")

        assert len(result) == 2
        assert all(isinstance(i, InventoryItem) for i in result)
        assert result[0].item is not None
        assert result[0].item.name == "Cozy Lamp"
        assert result[1].item is not None
        assert result[1].item.name == "Wooden Shelf"

    @pytest.mark.unit
    def test_empty_inventory(self, service, mock_supabase) -> None:
        """Returns empty list when user owns no items."""
        tables = _setup_tables(mock_supabase, ["user_items"])
        tables["user_items"].execute.return_value = MagicMock(data=[])

        result = service.get_inventory("user-123")

        assert result == []

    @pytest.mark.unit
    def test_inventory_deduplicates_catalog_lookup(self, service, mock_supabase) -> None:
        """Multiple copies of the same item result in one catalog lookup."""
        tables = _setup_tables(mock_supabase, ["user_items", "items"])

        # Two copies of the same item
        user_items = [
            _sample_user_item(inv_id="inv-1", item_id="item-1"),
            _sample_user_item(inv_id="inv-2", item_id="item-1"),
        ]
        tables["user_items"].execute.return_value = MagicMock(data=user_items)

        catalog_items = [_sample_item(item_id="item-1")]
        tables["items"].execute.return_value = MagicMock(data=catalog_items)

        result = service.get_inventory("user-123")

        assert len(result) == 2
        assert result[0].item.id == "item-1"
        assert result[1].item.id == "item-1"

        # in_ should have been called with deduplicated list (single item_id)
        tables["items"].in_.assert_called_once()
        args = tables["items"].in_.call_args.args
        assert args[0] == "id"
        assert len(args[1]) == 1
