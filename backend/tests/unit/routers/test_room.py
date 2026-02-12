"""Unit tests for room router endpoints.

Tests each endpoint by calling the async handler directly,
mocking AuthUser, RoomService, and UserService dependencies.

Endpoints tested:
- GET / - get_room_state()
- PUT /layout - update_room_layout()
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.room import InvalidPlacementError, LayoutUpdate, RoomPlacement
from app.routers.room import get_room_state, update_room_layout

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
def room_service() -> MagicMock:
    """Mocked RoomService."""
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
# GET / - get_room_state()
# =============================================================================


class TestGetRoomState:
    """Tests for the get_room_state endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_room_state(
        self, mock_request, mock_user, room_service, user_service, mock_profile
    ) -> None:
        """Happy path: returns RoomResponse from service."""
        expected_room = MagicMock()
        room_service.get_room_state.return_value = expected_room

        result = await get_room_state(
            request=mock_request,
            user=mock_user,
            user_service=user_service,
            room_service=room_service,
        )

        assert result is expected_room
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        room_service.get_room_state.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, room_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        with pytest.raises(HTTPException) as exc_info:
            await get_room_state(
                request=mock_request,
                user=mock_user,
                user_service=user_service_no_profile,
                room_service=room_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        room_service.get_room_state.assert_not_called()


# =============================================================================
# PUT /layout - update_room_layout()
# =============================================================================


class TestUpdateRoomLayout:
    """Tests for the update_room_layout endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_success(
        self, mock_request, mock_user, room_service, user_service, mock_profile
    ) -> None:
        """Happy path: layout updated and RoomState returned."""
        expected_state = MagicMock()
        room_service.update_layout.return_value = expected_state

        placements = [
            RoomPlacement(inventory_id="inv-001", grid_x=0, grid_y=0, rotation=0),
            RoomPlacement(inventory_id="inv-002", grid_x=2, grid_y=3, rotation=1),
        ]
        layout = LayoutUpdate(placements=placements)

        result = await update_room_layout(
            request=mock_request,
            layout_update=layout,
            user=mock_user,
            user_service=user_service,
            room_service=room_service,
        )

        assert result is expected_state
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        room_service.update_layout.assert_called_once_with(
            user_id=mock_profile.id, placements=placements
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, room_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        layout = LayoutUpdate(placements=[])

        with pytest.raises(HTTPException) as exc_info:
            await update_room_layout(
                request=mock_request,
                layout_update=layout,
                user=mock_user,
                user_service=user_service_no_profile,
                room_service=room_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        room_service.update_layout.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_placement_propagates(
        self, mock_request, mock_user, room_service, user_service
    ) -> None:
        """InvalidPlacementError propagates directly from service."""
        room_service.update_layout.side_effect = InvalidPlacementError(
            "Item overlaps with existing placement"
        )
        placements = [
            RoomPlacement(inventory_id="inv-001", grid_x=0, grid_y=0, rotation=0),
        ]
        layout = LayoutUpdate(placements=placements)

        with pytest.raises(InvalidPlacementError):
            await update_room_layout(
                request=mock_request,
                layout_update=layout,
                user=mock_user,
                user_service=user_service,
                room_service=room_service,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_placements(
        self, mock_request, mock_user, room_service, user_service, mock_profile
    ) -> None:
        """Submitting empty placements clears the room layout."""
        expected_state = MagicMock()
        room_service.update_layout.return_value = expected_state
        layout = LayoutUpdate(placements=[])

        result = await update_room_layout(
            request=mock_request,
            layout_update=layout,
            user=mock_user,
            user_service=user_service,
            room_service=room_service,
        )

        assert result is expected_state
        room_service.update_layout.assert_called_once_with(user_id=mock_profile.id, placements=[])
