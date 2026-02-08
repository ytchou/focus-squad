"""Unit tests for reflection router endpoints.

Tests:
- save_reflection() - happy path, session not found, not participant
- get_session_reflections() - happy path, session not found
- get_diary() - happy path, user not found
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.reflection import (
    DiaryResponse,
    NotSessionParticipantError,
    ReflectionPhase,
    ReflectionResponse,
    SaveReflectionRequest,
    SessionNotFoundError,
    SessionReflectionsResponse,
)
from app.routers.reflections import get_diary, get_session_reflections, save_reflection


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def auth_user():
    """Standard authenticated user for tests."""
    return AuthUser(auth_id="auth-123", email="test@example.com")


@pytest.fixture
def mock_profile():
    """Mock user profile."""
    profile = MagicMock()
    profile.id = "user-123"
    return profile


@pytest.fixture
def mock_user_service(mock_profile):
    """Mock UserService that returns the mock profile."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = mock_profile
    return service


@pytest.fixture
def mock_user_service_no_user():
    """Mock UserService that returns None (user not found)."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = None
    return service


@pytest.fixture
def mock_reflection_service():
    """Mock ReflectionService."""
    return MagicMock()


# =============================================================================
# TestSaveReflection
# =============================================================================


class TestSaveReflection:
    """Tests for save_reflection endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_reflection_success(
        self, auth_user, mock_user_service, mock_reflection_service
    ) -> None:
        """Successfully saves a reflection and returns 201."""
        request = SaveReflectionRequest(phase=ReflectionPhase.SETUP, content="My goal")
        expected = ReflectionResponse(
            id="r-1",
            session_id="session-1",
            user_id="user-123",
            display_name="Test User",
            phase=ReflectionPhase.SETUP,
            content="My goal",
            created_at="2026-02-08T10:00:00+00:00",
            updated_at="2026-02-08T10:00:00+00:00",
        )
        mock_reflection_service.save_reflection.return_value = expected

        result = await save_reflection(
            session_id="session-1",
            request=request,
            user=auth_user,
            reflection_service=mock_reflection_service,
            user_service=mock_user_service,
        )

        assert result.id == "r-1"
        assert result.content == "My goal"
        mock_reflection_service.save_reflection.assert_called_once_with(
            session_id="session-1",
            user_id="user-123",
            phase=ReflectionPhase.SETUP,
            content="My goal",
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_reflection_user_not_found(
        self, auth_user, mock_user_service_no_user, mock_reflection_service
    ) -> None:
        """Returns 404 when user profile not found."""
        request = SaveReflectionRequest(phase=ReflectionPhase.SETUP, content="Test")

        with pytest.raises(HTTPException) as exc_info:
            await save_reflection(
                session_id="session-1",
                request=request,
                user=auth_user,
                reflection_service=mock_reflection_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_reflection_session_not_found(
        self, auth_user, mock_user_service, mock_reflection_service
    ) -> None:
        """Returns 404 when session doesn't exist."""
        request = SaveReflectionRequest(phase=ReflectionPhase.SETUP, content="Test")
        mock_reflection_service.save_reflection.side_effect = SessionNotFoundError("Not found")

        with pytest.raises(HTTPException) as exc_info:
            await save_reflection(
                session_id="nonexistent",
                request=request,
                user=auth_user,
                reflection_service=mock_reflection_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_save_reflection_not_participant(
        self, auth_user, mock_user_service, mock_reflection_service
    ) -> None:
        """Returns 403 when user isn't a session participant."""
        request = SaveReflectionRequest(phase=ReflectionPhase.SETUP, content="Test")
        mock_reflection_service.save_reflection.side_effect = NotSessionParticipantError(
            "Not a participant"
        )

        with pytest.raises(HTTPException) as exc_info:
            await save_reflection(
                session_id="session-1",
                request=request,
                user=auth_user,
                reflection_service=mock_reflection_service,
                user_service=mock_user_service,
            )
        assert exc_info.value.status_code == 403


# =============================================================================
# TestGetSessionReflections
# =============================================================================


class TestGetSessionReflections:
    """Tests for get_session_reflections endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_reflections_success(
        self, auth_user, mock_reflection_service
    ) -> None:
        """Returns all reflections for a session."""
        mock_reflection_service.get_session_reflections.return_value = [
            ReflectionResponse(
                id="r-1", session_id="session-1", user_id="user-1",
                display_name="Alice", phase=ReflectionPhase.SETUP,
                content="Goal 1", created_at="2026-02-08T10:00:00+00:00",
                updated_at="2026-02-08T10:00:00+00:00",
            ),
        ]

        result = await get_session_reflections(
            session_id="session-1",
            user=auth_user,
            reflection_service=mock_reflection_service,
        )

        assert isinstance(result, SessionReflectionsResponse)
        assert len(result.reflections) == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_reflections_session_not_found(
        self, auth_user, mock_reflection_service
    ) -> None:
        """Returns 404 when session doesn't exist."""
        mock_reflection_service.get_session_reflections.side_effect = SessionNotFoundError(
            "Not found"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_session_reflections(
                session_id="nonexistent",
                user=auth_user,
                reflection_service=mock_reflection_service,
            )
        assert exc_info.value.status_code == 404


# =============================================================================
# TestGetDiary
# =============================================================================


class TestGetDiary:
    """Tests for get_diary endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_diary_success(
        self, auth_user, mock_user_service, mock_reflection_service
    ) -> None:
        """Returns paginated diary response."""
        mock_reflection_service.get_diary.return_value = DiaryResponse(
            items=[], total=0, page=1, per_page=20
        )

        result = await get_diary(
            page=1,
            per_page=20,
            user=auth_user,
            reflection_service=mock_reflection_service,
            user_service=mock_user_service,
        )

        assert isinstance(result, DiaryResponse)
        mock_reflection_service.get_diary.assert_called_once_with(
            user_id="user-123", page=1, per_page=20
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_diary_user_not_found(
        self, auth_user, mock_user_service_no_user, mock_reflection_service
    ) -> None:
        """Returns 404 when user profile not found."""
        with pytest.raises(HTTPException) as exc_info:
            await get_diary(
                page=1,
                per_page=20,
                user=auth_user,
                reflection_service=mock_reflection_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404
