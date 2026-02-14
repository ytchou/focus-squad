"""Unit tests for UserService."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.models.user import UserProfileUpdate
from app.services.user_service import (
    UsernameConflictError,
    UserNotFoundError,
    UserService,
    UserServiceError,
)


@pytest.fixture(autouse=True)
def mock_cache():
    """Patch cache functions so unit tests never touch real Redis."""
    with (
        patch("app.services.user_service.cache_get", return_value=None),
        patch("app.services.user_service.cache_set"),
        patch("app.services.user_service.cache_delete"),
    ):
        yield


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def user_service(mock_supabase):
    """UserService with mocked Supabase."""
    return UserService(supabase=mock_supabase)


@pytest.fixture
def sample_user_row():
    """Sample user data from database."""
    return {
        "id": "user-123",
        "auth_id": "auth-123",
        "email": "john@example.com",
        "username": "johndoe",
        "display_name": "John Doe",
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
        "pixel_avatar_id": None,
        "is_onboarded": False,
        "default_table_mode": "forced_audio",
        "activity_tracking_enabled": False,
        "email_notifications_enabled": True,
        "push_notifications_enabled": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "banned_until": None,
        "deleted_at": None,
        "deletion_scheduled_at": None,
    }


class TestUsernameGeneration:
    """Tests for username generation logic."""

    def test_simple_email(self, user_service) -> None:
        """Simple email prefix becomes username."""
        assert user_service._generate_username_from_email("john@example.com") == "john"

    def test_email_with_dots(self, user_service) -> None:
        """Dots removed from email prefix."""
        result = user_service._generate_username_from_email("john.doe@gmail.com")
        assert result == "johndoe"

    def test_short_prefix(self, user_service) -> None:
        """Short prefixes padded with 'user'."""
        assert user_service._generate_username_from_email("ab@x.com") == "abuser"

    def test_special_chars_removed(self, user_service) -> None:
        """Special chars removed except underscore."""
        result = user_service._generate_username_from_email("john+test@x.com")
        assert result == "johntest"

    def test_underscore_preserved(self, user_service) -> None:
        """Underscores preserved in username."""
        result = user_service._generate_username_from_email("john_doe@x.com")
        assert result == "john_doe"

    def test_uppercase_lowercased(self, user_service) -> None:
        """Uppercase converted to lowercase."""
        result = user_service._generate_username_from_email("JohnDoe@x.com")
        assert result == "johndoe"

    def test_long_prefix_truncated(self, user_service) -> None:
        """Long prefixes truncated to 25 chars."""
        long_email = "a" * 50 + "@example.com"
        result = user_service._generate_username_from_email(long_email)
        assert len(result) == 25


class TestFindUniqueUsername:
    """Tests for unique username finding."""

    @pytest.mark.unit
    def test_available_username(self, user_service, mock_supabase) -> None:
        """Base username available - use it directly."""
        # Setup: no user with this username
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service._find_unique_username("johndoe")
        assert result == "johndoe"

    @pytest.mark.unit
    def test_username_taken_adds_suffix(self, user_service, mock_supabase) -> None:
        """Username taken - add suffix."""
        call_count = 0

        def mock_execute():
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            # First call: username exists, subsequent calls: suffix available
            mock_result.data = [{"id": "existing"}] if call_count == 1 else []
            return mock_result

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute = mock_execute

        result = user_service._find_unique_username("johndoe")
        assert result.startswith("johndoe_")
        assert len(result) == len("johndoe_") + 4  # 4-char suffix

    @pytest.mark.unit
    def test_max_attempts_exceeded(self, user_service, mock_supabase) -> None:
        """Error raised after max attempts."""
        # All usernames taken
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "existing"}
        ]

        with pytest.raises(UserServiceError, match="Unable to generate unique username"):
            user_service._find_unique_username("johndoe", max_attempts=3)


class TestGetUserByAuthId:
    """Tests for get_user_by_auth_id method."""

    @pytest.mark.unit
    def test_user_found(self, user_service, mock_supabase, sample_user_row) -> None:
        """Returns UserProfile when user exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        result = user_service.get_user_by_auth_id("auth-123")

        assert result is not None
        assert result.id == "user-123"
        assert result.username == "johndoe"

    @pytest.mark.unit
    def test_user_not_found(self, user_service, mock_supabase) -> None:
        """Returns None when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service.get_user_by_auth_id("nonexistent")

        assert result is None


class TestCreateUserIfNotExists:
    """Tests for user creation with upsert behavior."""

    @pytest.mark.unit
    def test_returns_existing_user(self, user_service, mock_supabase, sample_user_row) -> None:
        """Existing user returned without creating new one."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        profile, created = user_service.create_user_if_not_exists("auth-123", "john@example.com")

        assert not created
        assert profile.id == "user-123"
        # Verify insert was not called
        mock_table.insert.assert_not_called()

    @pytest.mark.unit
    def test_creates_new_user(self, user_service, mock_supabase, sample_user_row) -> None:
        """New user created with associated records."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call: user doesn't exist (for get_user_by_auth_id)
        # Second call: username doesn't exist (for _find_unique_username)
        # Third call: insert returns new user
        call_count = 0

        def mock_select_execute():
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            mock_result.data = []
            return mock_result

        mock_table.select.return_value.eq.return_value.execute = mock_select_execute
        mock_table.insert.return_value.execute.return_value.data = [sample_user_row]

        profile, created = user_service.create_user_if_not_exists("auth-123", "john@example.com")

        assert created
        assert profile.username == "johndoe"
        # Verify insert was called for user, credits, essence, and notifications
        assert mock_table.insert.call_count >= 1


class TestUpdateUserProfile:
    """Tests for profile update logic."""

    @pytest.mark.unit
    def test_user_not_found(self, user_service, mock_supabase) -> None:
        """UserNotFoundError raised when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        update = UserProfileUpdate(display_name="New Name")

        with pytest.raises(UserNotFoundError):
            user_service.update_user_profile("nonexistent", update)

    @pytest.mark.unit
    def test_username_conflict(self, user_service, mock_supabase, sample_user_row) -> None:
        """UsernameConflictError raised when username is taken."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First select: current user exists
        # Second select: conflict check finds another user
        call_count = 0

        def mock_select_eq(*args):
            nonlocal call_count
            call_count += 1
            mock = MagicMock()
            if call_count == 1:
                # Current user lookup
                mock.execute.return_value.data = [sample_user_row]
            else:
                # Conflict check - username is taken
                mock.execute.return_value.data = [{"id": "other-user"}]
            return mock

        mock_table.select.return_value.eq = mock_select_eq

        update = UserProfileUpdate(username="taken_name")

        with pytest.raises(UsernameConflictError, match="already taken"):
            user_service.update_user_profile("auth-123", update)

    @pytest.mark.unit
    def test_successful_update(self, user_service, mock_supabase, sample_user_row) -> None:
        """Profile updated successfully."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Get current user
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        # Update returns updated user
        updated_row = sample_user_row.copy()
        updated_row["display_name"] = "New Name"
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [updated_row]

        update = UserProfileUpdate(display_name="New Name")
        result = user_service.update_user_profile("auth-123", update)

        assert result.display_name == "New Name"

    @pytest.mark.unit
    def test_no_changes(self, user_service, mock_supabase, sample_user_row) -> None:
        """No update when no fields changed."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        # Empty update - all fields None
        update = UserProfileUpdate()
        result = user_service.update_user_profile("auth-123", update)

        # Should return current profile without calling update
        assert result.username == "johndoe"
        mock_table.update.assert_not_called()


class TestGetPublicProfile:
    """Tests for public profile retrieval."""

    @pytest.mark.unit
    def test_returns_public_fields_only(self, user_service, mock_supabase) -> None:
        """Only public fields returned."""
        public_data = {
            "id": "user-123",
            "username": "johndoe",
            "display_name": "John Doe",
            "bio": "Hello world",
            "avatar_config": {},
            "study_interests": ["python", "math"],
            "reliability_score": Decimal("95.50"),
            "total_focus_minutes": 1200,
            "session_count": 24,
            "current_streak": 5,
            "longest_streak": 10,
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [public_data]

        result = user_service.get_public_profile("user-123")

        assert result is not None
        assert result.username == "johndoe"
        assert result.reliability_score == Decimal("95.50")
        # Verify email and auth_id are not in public profile
        assert not hasattr(result, "email") or "email" not in result.model_fields
        assert not hasattr(result, "auth_id") or "auth_id" not in result.model_fields

    @pytest.mark.unit
    def test_not_found(self, user_service, mock_supabase) -> None:
        """Returns None when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service.get_public_profile("nonexistent")

        assert result is None


class TestSoftDeleteUser:
    """Tests for soft delete user method."""

    @pytest.mark.unit
    def test_soft_delete_sets_deletion_fields(self, user_service, mock_supabase) -> None:
        """Soft delete sets deleted_at and deletion_scheduled_at."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "user-123", "auth_id": "auth-123"}
        ]

        result = user_service.soft_delete_user("auth-123")

        assert result is not None
        mock_table.update.assert_called_once()
        update_arg = mock_table.update.call_args[0][0]
        assert "deleted_at" in update_arg
        assert "deletion_scheduled_at" in update_arg

    @pytest.mark.unit
    def test_soft_delete_user_not_found(self, user_service, mock_supabase) -> None:
        """UserNotFoundError raised when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(UserNotFoundError):
            user_service.soft_delete_user("nonexistent")


class TestCancelAccountDeletion:
    """Tests for cancel account deletion method."""

    @pytest.mark.unit
    def test_cancel_clears_deletion_fields(
        self, user_service, mock_supabase, sample_user_row
    ) -> None:
        """Cancel deletion clears deleted_at and deletion_scheduled_at."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        # update() returns user row
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [sample_user_row]
        # get_user_by_auth_id needs select + credits
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        result = user_service.cancel_account_deletion("auth-123")

        assert result is not None
        mock_table.update.assert_called_once_with(
            {"deleted_at": None, "deletion_scheduled_at": None}
        )

    @pytest.mark.unit
    def test_cancel_deletion_user_not_found(self, user_service, mock_supabase) -> None:
        """UserNotFoundError raised when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.update.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(UserNotFoundError):
            user_service.cancel_account_deletion("nonexistent")


class TestCreditsRetryLogic:
    """Tests for referral code collision retry logic."""

    @pytest.mark.unit
    def test_credits_created_on_first_attempt(self, user_service, mock_supabase) -> None:
        """Credits created successfully on first attempt."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [{"id": "cred-1"}]

        # Should not raise
        user_service._create_credits_with_retry("user-123")

        mock_table.insert.assert_called_once()

    @pytest.mark.unit
    def test_credits_retry_on_referral_code_collision(self, user_service, mock_supabase) -> None:
        """Credits created after retry when referral code collision occurs."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First 2 attempts fail with unique constraint, 3rd succeeds
        call_count = 0

        def mock_insert_execute():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("unique constraint violation on referral_code")
            result = MagicMock()
            result.data = [{"id": "cred-1"}]
            return result

        mock_table.insert.return_value.execute = mock_insert_execute

        user_service._create_credits_with_retry("user-123")

        assert mock_table.insert.call_count == 3

    @pytest.mark.unit
    def test_credits_raises_after_max_attempts(self, user_service, mock_supabase) -> None:
        """UserServiceError raised after max retry attempts."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # All attempts fail with unique constraint
        mock_table.insert.return_value.execute.side_effect = Exception(
            "unique constraint violation on referral_code"
        )

        with pytest.raises(UserServiceError, match="referral code collision"):
            user_service._create_credits_with_retry("user-123", max_attempts=3)

        assert mock_table.insert.call_count == 3

    @pytest.mark.unit
    def test_credits_raises_immediately_on_non_collision_error(
        self, user_service, mock_supabase
    ) -> None:
        """Non-collision errors raised immediately without retry."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Error is not a referral code collision
        mock_table.insert.return_value.execute.side_effect = Exception(
            "foreign key constraint violation"
        )

        with pytest.raises(Exception, match="foreign key constraint"):
            user_service._create_credits_with_retry("user-123")

        # Should only try once - no retry for non-collision errors
        assert mock_table.insert.call_count == 1
