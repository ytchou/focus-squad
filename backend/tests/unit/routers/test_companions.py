"""Unit tests for companion router endpoints.

Tests each endpoint by calling the async handler directly,
mocking AuthUser, CompanionService, and UserService dependencies.

Endpoints tested:
- GET / - get_companions()
- POST /choose-starter - choose_starter_companion()
- POST /adopt - adopt_visitor()
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.room import (
    AdoptRequest,
    AlreadyHasStarterError,
    CompanionType,
    InvalidStarterError,
    StarterChoice,
    VisitorNotFoundError,
)
from app.routers.companions import (
    adopt_visitor,
    choose_starter_companion,
    get_companions,
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
def companion_service() -> MagicMock:
    """Mocked CompanionService."""
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
# GET / - get_companions()
# =============================================================================


class TestGetCompanions:
    """Tests for the get_companions endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_companions(
        self,
        mock_request,
        mock_user,
        companion_service,
        user_service,
        mock_profile,
    ) -> None:
        """Happy path: returns list of CompanionInfo from service."""
        expected = [MagicMock(), MagicMock()]
        companion_service.get_companions.return_value = expected

        result = await get_companions(
            request=mock_request,
            user=mock_user,
            user_service=user_service,
            companion_service=companion_service,
        )

        assert result is expected
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        companion_service.get_companions.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, companion_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        with pytest.raises(HTTPException) as exc_info:
            await get_companions(
                request=mock_request,
                user=mock_user,
                user_service=user_service_no_profile,
                companion_service=companion_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        companion_service.get_companions.assert_not_called()


# =============================================================================
# POST /choose-starter - choose_starter_companion()
# =============================================================================


class TestChooseStarterCompanion:
    """Tests for the choose_starter_companion endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_choose_success(
        self,
        mock_request,
        mock_user,
        companion_service,
        user_service,
        mock_profile,
    ) -> None:
        """Happy path: starter companion chosen and CompanionInfo returned."""
        expected_companion = MagicMock()
        companion_service.choose_starter.return_value = expected_companion
        choice = StarterChoice(companion_type=CompanionType.CAT)

        result = await choose_starter_companion(
            request=mock_request,
            starter_choice=choice,
            user=mock_user,
            user_service=user_service,
            companion_service=companion_service,
        )

        assert result is expected_companion
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        companion_service.choose_starter.assert_called_once_with(
            user_id=mock_profile.id,
            companion_type="cat",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, companion_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        choice = StarterChoice(companion_type=CompanionType.DOG)

        with pytest.raises(HTTPException) as exc_info:
            await choose_starter_companion(
                request=mock_request,
                starter_choice=choice,
                user=mock_user,
                user_service=user_service_no_profile,
                companion_service=companion_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        companion_service.choose_starter.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_starter_propagates(
        self, mock_request, mock_user, companion_service, user_service
    ) -> None:
        """InvalidStarterError propagates directly from service."""
        companion_service.choose_starter.side_effect = InvalidStarterError(
            "owl is not a valid starter companion"
        )
        choice = StarterChoice(companion_type=CompanionType.OWL)

        with pytest.raises(InvalidStarterError):
            await choose_starter_companion(
                request=mock_request,
                starter_choice=choice,
                user=mock_user,
                user_service=user_service,
                companion_service=companion_service,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_already_has_starter_propagates(
        self, mock_request, mock_user, companion_service, user_service
    ) -> None:
        """AlreadyHasStarterError propagates directly from service."""
        companion_service.choose_starter.side_effect = AlreadyHasStarterError(
            "User already chose a starter companion"
        )
        choice = StarterChoice(companion_type=CompanionType.BUNNY)

        with pytest.raises(AlreadyHasStarterError):
            await choose_starter_companion(
                request=mock_request,
                starter_choice=choice,
                user=mock_user,
                user_service=user_service,
                companion_service=companion_service,
            )


# =============================================================================
# POST /adopt - adopt_visitor()
# =============================================================================


class TestAdoptVisitor:
    """Tests for the adopt_visitor endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_adopt_success(
        self,
        mock_request,
        mock_user,
        companion_service,
        user_service,
        mock_profile,
    ) -> None:
        """Happy path: visiting companion adopted and CompanionInfo returned."""
        expected_companion = MagicMock()
        companion_service.adopt_visitor.return_value = expected_companion
        adopt = AdoptRequest(companion_type=CompanionType.FOX)

        result = await adopt_visitor(
            request=mock_request,
            adopt_request=adopt,
            user=mock_user,
            user_service=user_service,
            companion_service=companion_service,
        )

        assert result is expected_companion
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        companion_service.adopt_visitor.assert_called_once_with(
            user_id=mock_profile.id,
            companion_type="fox",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_request, mock_user, companion_service, user_service_no_profile
    ) -> None:
        """User not in database raises HTTPException 404."""
        adopt = AdoptRequest(companion_type=CompanionType.RACCOON)

        with pytest.raises(HTTPException) as exc_info:
            await adopt_visitor(
                request=mock_request,
                adopt_request=adopt,
                user=mock_user,
                user_service=user_service_no_profile,
                companion_service=companion_service,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail
        companion_service.adopt_visitor.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_visitor_not_found_propagates(
        self, mock_request, mock_user, companion_service, user_service
    ) -> None:
        """VisitorNotFoundError propagates directly from service."""
        companion_service.adopt_visitor.side_effect = VisitorNotFoundError(
            "No visiting turtle found"
        )
        adopt = AdoptRequest(companion_type=CompanionType.TURTLE)

        with pytest.raises(VisitorNotFoundError):
            await adopt_visitor(
                request=mock_request,
                adopt_request=adopt,
                user=mock_user,
                user_service=user_service,
                companion_service=companion_service,
            )
