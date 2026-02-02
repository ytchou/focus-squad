"""Unit tests for UserService."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.user import UserProfileUpdate
from app.services.user_service import (
    UsernameConflictError,
    UserNotFoundError,
    UserService,
    UserServiceError,
)


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
        "activity_tracking_enabled": False,
        "email_notifications_enabled": True,
        "push_notifications_enabled": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "banned_until": None,
    }


class TestUsernameGeneration:
    """Tests for username generation logic."""

    def test_simple_email(self, user_service):
        """Simple email prefix becomes username."""
        assert user_service._generate_username_from_email("john@example.com") == "john"

    def test_email_with_dots(self, user_service):
        """Dots removed from email prefix."""
        result = user_service._generate_username_from_email("john.doe@gmail.com")
        assert result == "johndoe"

    def test_short_prefix(self, user_service):
        """Short prefixes padded with 'user'."""
        assert user_service._generate_username_from_email("ab@x.com") == "abuser"

    def test_special_chars_removed(self, user_service):
        """Special chars removed except underscore."""
        result = user_service._generate_username_from_email("john+test@x.com")
        assert result == "johntest"

    def test_underscore_preserved(self, user_service):
        """Underscores preserved in username."""
        result = user_service._generate_username_from_email("john_doe@x.com")
        assert result == "john_doe"

    def test_uppercase_lowercased(self, user_service):
        """Uppercase converted to lowercase."""
        result = user_service._generate_username_from_email("JohnDoe@x.com")
        assert result == "johndoe"

    def test_long_prefix_truncated(self, user_service):
        """Long prefixes truncated to 25 chars."""
        long_email = "a" * 50 + "@example.com"
        result = user_service._generate_username_from_email(long_email)
        assert len(result) == 25


class TestFindUniqueUsername:
    """Tests for unique username finding."""

    @pytest.mark.unit
    def test_available_username(self, user_service, mock_supabase):
        """Base username available - use it directly."""
        # Setup: no user with this username
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service._find_unique_username("johndoe")
        assert result == "johndoe"

    @pytest.mark.unit
    def test_username_taken_adds_suffix(self, user_service, mock_supabase):
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
    def test_max_attempts_exceeded(self, user_service, mock_supabase):
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
    def test_user_found(self, user_service, mock_supabase, sample_user_row):
        """Returns UserProfile when user exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [sample_user_row]

        result = user_service.get_user_by_auth_id("auth-123")

        assert result is not None
        assert result.id == "user-123"
        assert result.username == "johndoe"

    @pytest.mark.unit
    def test_user_not_found(self, user_service, mock_supabase):
        """Returns None when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service.get_user_by_auth_id("nonexistent")

        assert result is None


class TestCreateUserIfNotExists:
    """Tests for user creation with upsert behavior."""

    @pytest.mark.unit
    def test_returns_existing_user(self, user_service, mock_supabase, sample_user_row):
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
    def test_creates_new_user(self, user_service, mock_supabase, sample_user_row):
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
    def test_user_not_found(self, user_service, mock_supabase):
        """UserNotFoundError raised when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        update = UserProfileUpdate(display_name="New Name")

        with pytest.raises(UserNotFoundError):
            user_service.update_user_profile("nonexistent", update)

    @pytest.mark.unit
    def test_username_conflict(self, user_service, mock_supabase, sample_user_row):
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
    def test_successful_update(self, user_service, mock_supabase, sample_user_row):
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
    def test_no_changes(self, user_service, mock_supabase, sample_user_row):
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
    def test_returns_public_fields_only(self, user_service, mock_supabase):
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
    def test_not_found(self, user_service, mock_supabase):
        """Returns None when user doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = user_service.get_public_profile("nonexistent")

        assert result is None
