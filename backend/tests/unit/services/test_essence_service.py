"""Unit tests for EssenceService.

Tests:
- get_balance() - happy path, no balance row returns zeros
- get_shop_items() - no filter, filter by category, filter by tier, empty result
- buy_item() - successful purchase, insufficient balance, item not found, item unavailable
- get_inventory() - happy path with multiple items, empty inventory
- gift_item() - happy path, self-gift, non-partner, insufficient essence, item not found
"""

from unittest.mock import MagicMock

import pytest

from app.models.partner import NotPartnerError
from app.models.room import (
    EssenceBalance,
    GiftPurchaseResponse,
    InsufficientEssenceError,
    InventoryItem,
    ItemNotFoundError,
    PurchaseResponse,
    SelfGiftError,
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
    """Create a chainable table mock that supports select/eq/in_/order/insert/update/or_/limit/not_/is_."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.order.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.or_.return_value = mock
    mock.limit.return_value = mock
    mock.not_.is_.return_value = mock
    mock.is_.return_value = mock
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
# TestBuyItem (uses atomic purchase_item_atomic RPC)
# =============================================================================


class TestBuyItem:
    """Tests for buy_item() method using atomic RPC."""

    @pytest.mark.unit
    def test_successful_purchase(self, service, mock_supabase) -> None:
        """Purchases item via atomic RPC and returns enriched PurchaseResponse."""
        # Mock atomic RPC success first (called before table access)
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={
                "success": True,
                "inventory_id": "inv-new",
                "new_balance": 95,
                "item_name": "Cozy Lamp",
                "cost": 5,
            }
        )
        mock_supabase.rpc.return_value = rpc_mock

        # Setup table mocks for item fetch, balance fetch, and inventory count
        tables = _setup_tables(mock_supabase, ["items", "furniture_essence", "user_items"])
        item = _sample_item(item_id="item-1", cost=5)
        tables["items"].execute.return_value = MagicMock(data=[item])
        tables["furniture_essence"].execute.return_value = MagicMock(
            data=[_sample_balance(balance=95, total_earned=100, total_spent=5)]
        )
        tables["user_items"].execute.return_value = MagicMock(data=[], count=3)
        tables["user_items"].execute.return_value.count = 3

        result = service.buy_item("user-123", "item-1")

        assert isinstance(result, PurchaseResponse)
        assert result.item.id == "inv-new"
        assert result.item.item_id == "item-1"
        assert result.item.acquisition_type == "purchased"
        assert result.item.item is not None
        assert result.item.item.essence_cost == 5
        assert result.balance.balance == 95
        assert result.inventory_count == 3

        # Verify atomic RPC was called with correct params
        mock_supabase.rpc.assert_called_once_with(
            "purchase_item_atomic",
            {
                "p_user_id": "user-123",
                "p_item_id": "item-1",
                "p_is_gift": False,
                "p_recipient_id": None,
                "p_gift_message": None,
            },
        )

    @pytest.mark.unit
    def test_item_not_found_from_rpc(self, service, mock_supabase) -> None:
        """Raises ItemNotFoundError when RPC returns item_not_found error."""
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "item_not_found"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(ItemNotFoundError, match="not found"):
            service.buy_item("user-123", "nonexistent-item")

    @pytest.mark.unit
    def test_insufficient_essence_from_rpc(self, service, mock_supabase) -> None:
        """Raises InsufficientEssenceError when RPC returns insufficient_essence."""
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "insufficient_essence"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(InsufficientEssenceError, match="Insufficient essence"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_no_essence_record_from_rpc(self, service, mock_supabase) -> None:
        """Raises InsufficientEssenceError when RPC returns no_essence_record."""
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "no_essence_record"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(InsufficientEssenceError, match="No essence balance"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_rpc_no_data_raises_error(self, service, mock_supabase) -> None:
        """Raises EssenceServiceError when RPC returns no data."""
        from app.models.room import EssenceServiceError

        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(data=None)
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(EssenceServiceError, match="no response"):
            service.buy_item("user-123", "item-1")

    @pytest.mark.unit
    def test_unknown_error_from_rpc(self, service, mock_supabase) -> None:
        """Raises EssenceServiceError with message when RPC returns unknown error."""
        from app.models.room import EssenceServiceError

        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "database_error"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(EssenceServiceError, match="database_error"):
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


# =============================================================================
# TestGiftItem
# =============================================================================


def _sample_partnership(
    partnership_id="part-1",
    requester_id="user-sender",
    addressee_id="user-recipient",
    status="accepted",
):
    """Sample partnerships row."""
    return {
        "id": partnership_id,
        "requester_id": requester_id,
        "addressee_id": addressee_id,
        "status": status,
    }


def _sample_recipient_profile(
    user_id="user-recipient",
    username="recipient_user",
    display_name="Recipient",
):
    """Sample users row for the gift recipient."""
    return {
        "id": user_id,
        "username": username,
        "display_name": display_name,
    }


class TestGiftItem:
    """Tests for gift_item() method using atomic RPC."""

    @pytest.mark.unit
    def test_gift_successful(self, service, mock_supabase) -> None:
        """Happy path: partnership valid, atomic RPC handles deduction and inventory."""
        tables = _setup_tables(mock_supabase, ["partnerships", "users", "furniture_essence"])

        # Partnership check: accepted partnership between sender and recipient
        tables["partnerships"].execute.return_value = MagicMock(
            data=[
                _sample_partnership(
                    requester_id="user-sender",
                    addressee_id="user-recipient",
                    status="accepted",
                )
            ]
        )

        # Recipient profile lookup for response display name
        tables["users"].execute.return_value = MagicMock(
            data=[_sample_recipient_profile(user_id="user-recipient", display_name="Recipient")]
        )

        # Balance fetch after gift (for enriched response)
        tables["furniture_essence"].execute.return_value = MagicMock(
            data=[_sample_balance(balance=95, total_earned=100, total_spent=5)]
        )

        # Atomic RPC succeeds with all data
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={
                "success": True,
                "inventory_id": "inv-gift-1",
                "new_balance": 95,
                "item_name": "Cozy Lamp",
                "cost": 5,
            }
        )
        mock_supabase.rpc.return_value = rpc_mock

        result = service.gift_item(
            sender_id="user-sender",
            recipient_id="user-recipient",
            item_id="item-gift",
            gift_message="Enjoy this lamp!",
        )

        # Verify return type and fields
        assert isinstance(result, GiftPurchaseResponse)
        assert result.inventory_item_id == "inv-gift-1"
        assert result.item_name == "Cozy Lamp"
        assert result.recipient_name == "Recipient"
        assert result.essence_spent == 5
        assert result.balance is not None
        assert result.balance.balance == 95

        # Verify atomic RPC was called with gift params
        mock_supabase.rpc.assert_called_once_with(
            "purchase_item_atomic",
            {
                "p_user_id": "user-sender",
                "p_item_id": "item-gift",
                "p_is_gift": True,
                "p_recipient_id": "user-recipient",
                "p_gift_message": "Enjoy this lamp!",
            },
        )

    @pytest.mark.unit
    def test_gift_to_self_fails(self, service, mock_supabase) -> None:
        """Raises SelfGiftError when sender_id == recipient_id."""
        with pytest.raises(SelfGiftError):
            service.gift_item(
                sender_id="user-123",
                recipient_id="user-123",
                item_id="item-1",
            )

    @pytest.mark.unit
    def test_gift_to_non_partner_fails(self, service, mock_supabase) -> None:
        """Raises NotPartnerError when no accepted partnership exists."""
        tables = _setup_tables(mock_supabase, ["partnerships"])

        # No partnership found
        tables["partnerships"].execute.return_value = MagicMock(data=[])

        with pytest.raises(NotPartnerError):
            service.gift_item(
                sender_id="user-sender",
                recipient_id="user-stranger",
                item_id="item-1",
            )

    @pytest.mark.unit
    def test_gift_insufficient_essence_from_rpc(self, service, mock_supabase) -> None:
        """Raises InsufficientEssenceError when RPC returns insufficient_essence."""
        tables = _setup_tables(mock_supabase, ["partnerships", "users"])

        # Partnership exists
        tables["partnerships"].execute.return_value = MagicMock(
            data=[
                _sample_partnership(
                    requester_id="user-sender",
                    addressee_id="user-recipient",
                    status="accepted",
                )
            ]
        )

        # Recipient profile
        tables["users"].execute.return_value = MagicMock(data=[_sample_recipient_profile()])

        # RPC returns failure (insufficient balance)
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "insufficient_essence"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(InsufficientEssenceError):
            service.gift_item(
                sender_id="user-sender",
                recipient_id="user-recipient",
                item_id="item-1",
            )

    @pytest.mark.unit
    def test_gift_item_not_found_from_rpc(self, service, mock_supabase) -> None:
        """Raises ItemNotFoundError when RPC returns item_not_found."""
        tables = _setup_tables(mock_supabase, ["partnerships", "users"])

        # Partnership exists
        tables["partnerships"].execute.return_value = MagicMock(
            data=[
                _sample_partnership(
                    requester_id="user-sender",
                    addressee_id="user-recipient",
                    status="accepted",
                )
            ]
        )

        # Recipient profile
        tables["users"].execute.return_value = MagicMock(data=[_sample_recipient_profile()])

        # RPC returns item not found
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(
            data={"success": False, "error": "item_not_found"}
        )
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(ItemNotFoundError):
            service.gift_item(
                sender_id="user-sender",
                recipient_id="user-recipient",
                item_id="nonexistent-item",
            )

    @pytest.mark.unit
    def test_gift_no_rpc_data_raises_error(self, service, mock_supabase) -> None:
        """Raises EssenceServiceError when RPC returns no data."""
        from app.models.room import EssenceServiceError

        tables = _setup_tables(mock_supabase, ["partnerships", "users"])

        # Partnership exists
        tables["partnerships"].execute.return_value = MagicMock(
            data=[
                _sample_partnership(
                    requester_id="user-sender",
                    addressee_id="user-recipient",
                    status="accepted",
                )
            ]
        )

        # Recipient profile
        tables["users"].execute.return_value = MagicMock(data=[_sample_recipient_profile()])

        # RPC returns no data
        rpc_mock = MagicMock()
        rpc_mock.execute.return_value = MagicMock(data=None)
        mock_supabase.rpc.return_value = rpc_mock

        with pytest.raises(EssenceServiceError, match="no response"):
            service.gift_item(
                sender_id="user-sender",
                recipient_id="user-recipient",
                item_id="item-1",
            )
