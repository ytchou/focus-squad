"""Unit tests for essence router endpoints.

Tests each endpoint by calling the async handler directly,
mocking AuthUser, EssenceService, and UserService dependencies.

Endpoints tested:
- GET /balance - get_essence_balance()
- GET /shop - get_shop_catalog()
- POST /buy - purchase_item()
- GET /inventory - get_user_inventory()
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.room import (
    EssenceBalance,
    InsufficientEssenceError,
    ItemNotFoundError,
    PurchaseRequest,
)
from app.routers.essence import (
    get_essence_balance,
    get_shop_catalog,
    get_user_inventory,
    purchase_item,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_request() -> MagicMock:
    """Mocked FastAPI Request object."""
    req = MagicMock()
    req.state = MagicMock()
    return req


@pytest.fixture
def mock_user() -> AuthUser:
    """Authenticated user fixture."""
    return AuthUser(auth_id="auth-abc-123", email="test@example.com")


@pytest.fixture
def mock_profile() -> MagicMock:
    """User profile returned by user_service.get_user_by_auth_id()."""
    profile = MagicMock()
    profile.id = "user-uuid-456"
    return profile


@pytest.fixture
def essence_service() -> MagicMock:
    """Mocked EssenceService."""
    return MagicMock()


@pytest.fixture
def user_service(mock_profile: MagicMock) -> MagicMock:
    """Mocked UserService that returns a profile by default."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = mock_profile
    return svc


@pytest.fixture
def user_service_no_profile() -> MagicMock:
    """Mocked UserService that returns None (user not found)."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = None
    return svc


# =============================================================================
# GET /balance - get_essence_balance()
# =============================================================================


class TestGetEssenceBalance:
    """Tests for the get_essence_balance endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_balance(
        self, mock_request, mock_user, essence_service, user_service, mock_profile
    ) -> None:
        """Happy path: returns EssenceBalance from service."""
        expected = MagicMock()
        essence_service.get_balance.return_value = expected

        result = await get_essence_balance(
            request=mock_request,
            user=mock_user,
            user_service=user_service,
            essence_service=essence_service,
        )

        assert result is expected
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        essence_service.get_balance.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_returns_zeros(
        self, mock_request, mock_user, essence_service, user_service_no_profile
    ) -> None:
        """User not in database returns EssenceBalance with all zeros."""
        result = await get_essence_balance(
            request=mock_request,
            user=mock_user,
            user_service=user_service_no_profile,
            essence_service=essence_service,
        )

        assert isinstance(result, EssenceBalance)
        assert result.balance == 0
        assert result.total_earned == 0
        assert result.total_spent == 0
        essence_service.get_balance.assert_not_called()


# =============================================================================
# GET /shop - get_shop_catalog()
# =============================================================================


class TestGetShopCatalog:
    """Tests for the get_shop_catalog endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_filters(self, mock_request, mock_user, essence_service) -> None:
        """Returns all shop items when no filters are applied."""
        expected_items = [MagicMock(), MagicMock()]
        essence_service.get_shop_items.return_value = expected_items

        result = await get_shop_catalog(
            request=mock_request,
            category=None,
            tier=None,
            user=mock_user,
            essence_service=essence_service,
        )

        assert result is expected_items
        essence_service.get_shop_items.assert_called_once_with(category=None, tier=None)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_category_filter(self, mock_request, mock_user, essence_service) -> None:
        """Filters shop items by category."""
        expected_items = [MagicMock()]
        essence_service.get_shop_items.return_value = expected_items

        result = await get_shop_catalog(
            request=mock_request,
            category="furniture",
            tier=None,
            user=mock_user,
            essence_service=essence_service,
        )

        assert result is expected_items
        essence_service.get_shop_items.assert_called_once_with(category="furniture", tier=None)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_with_tier_filter(self, mock_request, mock_user, essence_service) -> None:
        """Filters shop items by tier."""
        expected_items = [MagicMock()]
        essence_service.get_shop_items.return_value = expected_items

        result = await get_shop_catalog(
            request=mock_request,
            category=None,
            tier="premium",
            user=mock_user,
            essence_service=essence_service,
        )

        assert result is expected_items
        essence_service.get_shop_items.assert_called_once_with(category=None, tier="premium")


# =============================================================================
# POST /buy - purchase_item()
# =============================================================================


class TestPurchaseItem:
    """Tests for the purchase_item endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_purchase_success(
        self, mock_request, mock_user, essence_service, user_service, mock_profile
    ) -> None:
        """Happy path: item purchased and InventoryItem returned."""
        expected_item = MagicMock()
        essence_service.buy_item.return_value = expected_item
        purchase = PurchaseRequest(item_id="item-desk-001")

        result = await purchase_item(
            request=mock_request,
            purchase_request=purchase,
            user=mock_user,
            user_service=user_service,
            essence_service=essence_service,
        )

        assert result is expected_item
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        essence_service.buy_item.assert_called_once_with(
            user_id=mock_profile.id, item_id="item-desk-001"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, essence_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        purchase = PurchaseRequest(item_id="item-desk-001")

        with pytest.raises(HTTPException) as exc_info:
            await purchase_item(
                request=mock_request,
                purchase_request=purchase,
                user=mock_user,
                user_service=user_service_no_profile,
                essence_service=essence_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_insufficient_essence_propagates(
        self, mock_request, mock_user, essence_service, user_service
    ) -> None:
        """InsufficientEssenceError propagates directly from service."""
        essence_service.buy_item.side_effect = InsufficientEssenceError("Not enough essence")
        purchase = PurchaseRequest(item_id="item-desk-001")

        with pytest.raises(InsufficientEssenceError):
            await purchase_item(
                request=mock_request,
                purchase_request=purchase,
                user=mock_user,
                user_service=user_service,
                essence_service=essence_service,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_item_not_found_propagates(
        self, mock_request, mock_user, essence_service, user_service
    ) -> None:
        """ItemNotFoundError propagates directly from service."""
        essence_service.buy_item.side_effect = ItemNotFoundError("Item does not exist")
        purchase = PurchaseRequest(item_id="nonexistent-item")

        with pytest.raises(ItemNotFoundError):
            await purchase_item(
                request=mock_request,
                purchase_request=purchase,
                user=mock_user,
                user_service=user_service,
                essence_service=essence_service,
            )


# =============================================================================
# GET /inventory - get_user_inventory()
# =============================================================================


class TestGetUserInventory:
    """Tests for the get_user_inventory endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_inventory(
        self, mock_request, mock_user, essence_service, user_service, mock_profile
    ) -> None:
        """Happy path: returns list of InventoryItems from service."""
        expected_items = [MagicMock(), MagicMock(), MagicMock()]
        essence_service.get_inventory.return_value = expected_items

        result = await get_user_inventory(
            request=mock_request,
            user=mock_user,
            user_service=user_service,
            essence_service=essence_service,
        )

        assert result is expected_items
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        essence_service.get_inventory.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_returns_empty(
        self, mock_request, mock_user, essence_service, user_service_no_profile
    ) -> None:
        """User not in database returns empty list."""
        result = await get_user_inventory(
            request=mock_request,
            user=mock_user,
            user_service=user_service_no_profile,
            essence_service=essence_service,
        )

        assert result == []
        essence_service.get_inventory.assert_not_called()
