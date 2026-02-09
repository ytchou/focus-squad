"""Unit tests for users router endpoints.

Tests:
- GET /me: get_my_profile() - upsert user on first login
- PATCH /me: update_my_profile() - partial profile updates with error handling
- GET /{user_id}: get_user_profile() - public profile lookup
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.user import UserProfile, UserProfileUpdate, UserPublicProfile
from app.routers.users import (
    delete_my_account,
    get_my_profile,
    get_user_profile,
    update_my_profile,
)
from app.services.user_service import UsernameConflictError, UserNotFoundError


def _make_user_profile(**overrides) -> UserProfile:
    """Helper to build a UserProfile with sensible defaults."""
    defaults = {
        "id": "user-uuid-123",
        "auth_id": "auth-abc-123",
        "email": "test@example.com",
        "username": "testuser",
        "display_name": "testuser",
        "bio": None,
        "avatar_config": {},
        "social_links": {},
        "study_interests": [],
        "preferred_language": "en",
        "reliability_score": Decimal("100.00"),
        "total_focus_minutes": 0,
        "session_count": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "last_session_date": None,
        "credits_remaining": 2,
        "credits_used_this_week": 0,
        "credit_tier": "free",
        "credit_refresh_date": None,
        "pixel_avatar_id": None,
        "is_onboarded": False,
        "default_table_mode": "forced_audio",
        "activity_tracking_enabled": False,
        "email_notifications_enabled": True,
        "push_notifications_enabled": True,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "banned_until": None,
        "deleted_at": None,
        "deletion_scheduled_at": None,
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


def _make_public_profile(**overrides) -> UserPublicProfile:
    """Helper to build a UserPublicProfile with sensible defaults."""
    defaults = {
        "id": "user-uuid-123",
        "username": "testuser",
        "display_name": "testuser",
        "bio": None,
        "avatar_config": {},
        "study_interests": [],
        "reliability_score": Decimal("100.00"),
        "total_focus_minutes": 0,
        "session_count": 0,
        "current_streak": 0,
        "longest_streak": 0,
    }
    defaults.update(overrides)
    return UserPublicProfile(**defaults)


# =============================================================================
# GET /me - get_my_profile()
# =============================================================================


class TestGetMyProfile:
    """Tests for the GET /me endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_existing_user_profile(self) -> None:
        """Returns profile for an existing user (created=False)."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        profile = _make_user_profile()
        user_service = MagicMock()
        user_service.create_user_if_not_exists.return_value = (profile, False)

        result = await get_my_profile(current_user=current_user, user_service=user_service)

        assert result == profile
        user_service.create_user_if_not_exists.assert_called_once_with(
            auth_id="auth-abc-123",
            email="test@example.com",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_new_user_on_first_login(self) -> None:
        """Creates user on first OAuth login (created=True)."""
        current_user = AuthUser(auth_id="auth-new-user", email="new@example.com")
        profile = _make_user_profile(
            auth_id="auth-new-user", email="new@example.com", username="newuser"
        )
        user_service = MagicMock()
        user_service.create_user_if_not_exists.return_value = (profile, True)

        result = await get_my_profile(current_user=current_user, user_service=user_service)

        assert result == profile
        assert result.username == "newuser"
        user_service.create_user_if_not_exists.assert_called_once_with(
            auth_id="auth-new-user",
            email="new@example.com",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_passes_auth_id_and_email_from_current_user(self) -> None:
        """Verifies correct auth_id and email are forwarded to the service."""
        current_user = AuthUser(auth_id="specific-auth-id", email="specific@mail.com")
        profile = _make_user_profile(auth_id="specific-auth-id", email="specific@mail.com")
        user_service = MagicMock()
        user_service.create_user_if_not_exists.return_value = (profile, False)

        await get_my_profile(current_user=current_user, user_service=user_service)

        call_kwargs = user_service.create_user_if_not_exists.call_args.kwargs
        assert call_kwargs["auth_id"] == "specific-auth-id"
        assert call_kwargs["email"] == "specific@mail.com"


# =============================================================================
# PATCH /me - update_my_profile()
# =============================================================================


class TestUpdateMyProfile:
    """Tests for the PATCH /me endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_update(self) -> None:
        """Returns updated profile on successful update."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        update = UserProfileUpdate(display_name="New Name", bio="Hello world")
        updated_profile = _make_user_profile(display_name="New Name", bio="Hello world")
        user_service = MagicMock()
        user_service.update_user_profile.return_value = updated_profile

        result = await update_my_profile(
            update=update, current_user=current_user, user_service=user_service
        )

        assert result == updated_profile
        assert result.display_name == "New Name"
        assert result.bio == "Hello world"
        user_service.update_user_profile.assert_called_once_with(
            auth_id="auth-abc-123",
            update=update,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_username_update(self) -> None:
        """Successfully updates username when not conflicting."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        update = UserProfileUpdate(username="newname")
        updated_profile = _make_user_profile(username="newname")
        user_service = MagicMock()
        user_service.update_user_profile.return_value = updated_profile

        result = await update_my_profile(
            update=update, current_user=current_user, user_service=user_service
        )

        assert result.username == "newname"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self) -> None:
        """Raises 404 when user is not found."""
        current_user = AuthUser(auth_id="auth-ghost", email="ghost@example.com")
        update = UserProfileUpdate(display_name="Ghost")
        user_service = MagicMock()
        user_service.update_user_profile.side_effect = UserNotFoundError("User not found")

        with pytest.raises(HTTPException) as exc_info:
            await update_my_profile(
                update=update, current_user=current_user, user_service=user_service
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_username_conflict_raises_400(self) -> None:
        """Raises 400 when username is already taken."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        update = UserProfileUpdate(username="taken_name")
        user_service = MagicMock()
        user_service.update_user_profile.side_effect = UsernameConflictError(
            "Username 'taken_name' is already taken"
        )

        with pytest.raises(HTTPException) as exc_info:
            await update_my_profile(
                update=update, current_user=current_user, user_service=user_service
            )

        assert exc_info.value.status_code == 400
        assert "taken_name" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_username_conflict_detail_contains_error_message(self) -> None:
        """The 400 detail should include the original error message string."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        update = UserProfileUpdate(username="duplicate")
        error_msg = "Username 'duplicate' is already taken"
        user_service = MagicMock()
        user_service.update_user_profile.side_effect = UsernameConflictError(error_msg)

        with pytest.raises(HTTPException) as exc_info:
            await update_my_profile(
                update=update, current_user=current_user, user_service=user_service
            )

        assert exc_info.value.detail == error_msg


# =============================================================================
# GET /{user_id} - get_user_profile()
# =============================================================================


class TestGetUserProfile:
    """Tests for the GET /{user_id} endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_public_profile(self) -> None:
        """Returns public profile for a valid user_id."""
        public_profile = _make_public_profile(username="alice", display_name="Alice")
        user_service = MagicMock()
        user_service.get_public_profile.return_value = public_profile

        result = await get_user_profile(user_id="user-uuid-123", user_service=user_service)

        assert result == public_profile
        assert result.username == "alice"
        assert result.display_name == "Alice"
        user_service.get_public_profile.assert_called_once_with("user-uuid-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self) -> None:
        """Raises 404 when user_id does not exist."""
        user_service = MagicMock()
        user_service.get_public_profile.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_user_profile(user_id="nonexistent-id", user_service=user_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "User not found"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_passes_correct_user_id_to_service(self) -> None:
        """Verifies the user_id argument is forwarded correctly."""
        target_id = "target-user-uuid-456"
        public_profile = _make_public_profile(id=target_id)
        user_service = MagicMock()
        user_service.get_public_profile.return_value = public_profile

        await get_user_profile(user_id=target_id, user_service=user_service)

        user_service.get_public_profile.assert_called_once_with(target_id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_not_require_auth(self) -> None:
        """Endpoint should work without current_user (no auth dependency)."""
        public_profile = _make_public_profile()
        user_service = MagicMock()
        user_service.get_public_profile.return_value = public_profile

        # Call without current_user parameter -- the endpoint signature does not include it
        result = await get_user_profile(user_id="user-uuid-123", user_service=user_service)

        assert result == public_profile


# =============================================================================
# DELETE /me - delete_my_account()
# =============================================================================


class TestDeleteMyAccount:
    """Tests for the DELETE /me endpoint (soft delete)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_soft_delete(self) -> None:
        """Returns 200 with deletion scheduled message."""
        current_user = AuthUser(auth_id="auth-abc-123", email="test@example.com")
        scheduled = datetime(2025, 1, 31, tzinfo=timezone.utc)
        user_service = MagicMock()
        user_service.soft_delete_user.return_value = scheduled

        result = await delete_my_account(current_user=current_user, user_service=user_service)

        assert result.deletion_scheduled_at == scheduled
        assert "30 days" in result.message
        user_service.soft_delete_user.assert_called_once_with("auth-abc-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self) -> None:
        """Raises 404 when user doesn't exist."""
        current_user = AuthUser(auth_id="auth-ghost", email="ghost@example.com")
        user_service = MagicMock()
        user_service.soft_delete_user.side_effect = UserNotFoundError("User not found")

        with pytest.raises(HTTPException) as exc_info:
            await delete_my_account(current_user=current_user, user_service=user_service)

        assert exc_info.value.status_code == 404
