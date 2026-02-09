"""
User service for profile management operations.

Handles:
- User creation with upsert behavior (first OAuth login)
- Profile updates with conflict handling
- Username generation with collision handling
- Associated records creation (credits, essence, notifications)
"""

import random
import string
from datetime import datetime
from typing import Any, Optional, cast

from supabase import Client

from app.core.database import get_supabase
from app.models.user import UserProfile, UserProfileUpdate, UserPublicProfile


class UserServiceError(Exception):
    """Base exception for user service errors."""

    pass


class UserNotFoundError(UserServiceError):
    """User not found."""

    pass


class UsernameConflictError(UserServiceError):
    """Username already taken."""

    pass


class UserService:
    """Service for user profile operations."""

    # Default notification event types for new users
    DEFAULT_NOTIFICATION_EVENTS: list[str] = [
        "session_start",
        "match_found",
        "credit_refresh",
        "red_rating",
        "friend_joined",
    ]

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def _generate_username_from_email(self, email: str) -> str:
        """
        Generate username from email prefix.

        Examples:
            john.doe@gmail.com -> johndoe
            jane_smith@example.com -> jane_smith
            ab@x.com -> abuser (padded for minimum length)
        """
        prefix = email.split("@")[0]
        # Remove non-alphanumeric except underscore, lowercase
        username = "".join(c for c in prefix if c.isalnum() or c == "_").lower()
        # Ensure minimum length
        if len(username) < 3:
            username = username + "user"
        # Truncate to max 25 chars (leaving room for suffix)
        return username[:25]

    def _generate_random_suffix(self, length: int = 4) -> str:
        """Generate random alphanumeric suffix."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _find_unique_username(self, base_username: str, max_attempts: int = 10) -> str:
        """
        Find a unique username, adding random suffix if needed.

        Args:
            base_username: Base username to try
            max_attempts: Max attempts before raising error

        Returns:
            Unique username

        Raises:
            UserServiceError: If unable to find unique username after max attempts
        """
        # Try base username first
        result = self.supabase.table("users").select("id").eq("username", base_username).execute()
        if not result.data:
            return base_username

        # Try with random suffixes
        for _ in range(max_attempts):
            candidate = f"{base_username}_{self._generate_random_suffix()}"
            result = self.supabase.table("users").select("id").eq("username", candidate).execute()
            if not result.data:
                return candidate

        raise UserServiceError(f"Unable to generate unique username after {max_attempts} attempts")

    def get_user_by_auth_id(self, auth_id: str) -> Optional[UserProfile]:
        """
        Fetch user by Supabase auth ID with credit information.

        Args:
            auth_id: Supabase auth.uid()

        Returns:
            UserProfile if found, None otherwise
        """
        result = self.supabase.table("users").select("*").eq("auth_id", auth_id).execute()

        if not result.data:
            return None

        user_data = result.data[0]

        # Fetch credits for this user (uses new schema from migration 005)
        credits_result = (
            self.supabase.table("credits")
            .select("credits_remaining, tier, credit_cycle_start")
            .eq("user_id", user_data["id"])
            .execute()
        )

        if credits_result.data:
            credit_row = credits_result.data[0]
            user_data["credits_remaining"] = credit_row.get("credits_remaining", 0)
            user_data["credits_used_this_week"] = 0  # Deprecated - calculated from transactions now
            user_data["credit_tier"] = credit_row.get("tier", "free")
            user_data["credit_refresh_date"] = credit_row.get("credit_cycle_start")

        return UserProfile(**user_data)

    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """
        Fetch user by internal user ID with credit information.

        Args:
            user_id: Internal user UUID

        Returns:
            UserProfile if found, None otherwise
        """
        result = self.supabase.table("users").select("*").eq("id", user_id).execute()

        if not result.data:
            return None

        user_data = result.data[0]

        # Fetch credits for this user (uses new schema from migration 005)
        credits_result = (
            self.supabase.table("credits")
            .select("credits_remaining, tier, credit_cycle_start")
            .eq("user_id", user_id)
            .execute()
        )

        if credits_result.data:
            credit_row = credits_result.data[0]
            user_data["credits_remaining"] = credit_row.get("credits_remaining", 0)
            user_data["credits_used_this_week"] = 0  # Deprecated - calculated from transactions now
            user_data["credit_tier"] = credit_row.get("tier", "free")
            user_data["credit_refresh_date"] = credit_row.get("credit_cycle_start")

        return UserProfile(**user_data)

    def get_public_profile(self, user_id: str) -> Optional[UserPublicProfile]:
        """
        Fetch public profile for a user (limited fields).

        Args:
            user_id: Internal user UUID

        Returns:
            UserPublicProfile if found, None otherwise
        """
        # Select only public fields
        result = (
            self.supabase.table("users")
            .select(
                "id, username, display_name, bio, avatar_config, study_interests, "
                "reliability_score, total_focus_minutes, session_count, "
                "current_streak, longest_streak"
            )
            .eq("id", user_id)
            .execute()
        )

        if not result.data:
            return None

        return UserPublicProfile(**result.data[0])

    def create_user_if_not_exists(self, auth_id: str, email: str) -> tuple[UserProfile, bool]:
        """
        Create user if not exists (upsert for first OAuth login).

        Creates user record AND associated records:
        - credits row (Free tier, 2 credits)
        - furniture_essence row (0 balance)
        - notification_preferences rows (defaults for all event types)

        Args:
            auth_id: Supabase auth.uid()
            email: User's email from OAuth

        Returns:
            Tuple of (UserProfile, created) where created is True if new user
        """
        # Check if user already exists
        existing = self.get_user_by_auth_id(auth_id)
        if existing:
            return existing, False

        # Generate unique username
        base_username = self._generate_username_from_email(email)
        username = self._find_unique_username(base_username)

        # Create user record
        user_data = {
            "auth_id": auth_id,
            "email": email,
            "username": username,
            "display_name": username,  # Default display name to username
        }

        result = self.supabase.table("users").insert(user_data).execute()

        if not result.data:
            raise UserServiceError("Failed to create user record")

        # Cast result.data to expected type for mypy
        data_list = cast(list[dict[str, Any]], result.data)
        user_row = data_list[0]
        user_id = cast(str, user_row["id"])

        # Create associated records
        self._create_associated_records(user_id)

        return UserProfile(**user_row), True

    def _create_associated_records(self, user_id: str) -> None:
        """
        Create associated records for a new user.

        Creates:
        - credits row (Free tier, 2 credits)
        - furniture_essence row (0 balance)
        - notification_preferences rows (defaults for all event types)
        """
        # Create credits record
        # credit_cycle_start = today (rolling 7-day refresh from signup)
        # referral_code auto-generated by DB trigger
        from datetime import datetime, timezone

        self.supabase.table("credits").insert(
            {
                "user_id": user_id,
                "tier": "free",
                "credits_remaining": 2,
                "credit_cycle_start": datetime.now(timezone.utc).date().isoformat(),
                "gifts_sent_this_week": 0,
            }
        ).execute()

        # Create furniture_essence record
        self.supabase.table("furniture_essence").insert(
            {
                "user_id": user_id,
                "balance": 0,
                "total_earned": 0,
                "total_spent": 0,
            }
        ).execute()

        # Create default notification preferences
        notification_prefs: list[dict[str, Any]] = [
            {
                "user_id": user_id,
                "event_type": event_type,
                "email_enabled": True,
                "push_enabled": True,
            }
            for event_type in self.DEFAULT_NOTIFICATION_EVENTS
        ]
        self.supabase.table("notification_preferences").insert(notification_prefs).execute()

    def update_user_profile(self, auth_id: str, update: UserProfileUpdate) -> UserProfile:
        """
        Update user profile fields.

        Handles username uniqueness conflicts gracefully.

        Args:
            auth_id: Supabase auth.uid() of the user
            update: Partial update data

        Returns:
            Updated UserProfile

        Raises:
            UserNotFoundError: If user not found
            UsernameConflictError: If new username is already taken
        """
        # Get current user to verify they exist
        current = self.get_user_by_auth_id(auth_id)
        if not current:
            raise UserNotFoundError(f"User with auth_id {auth_id} not found")

        # Build update dict from non-None fields
        update_data: dict[str, Any] = {}
        update_dict = update.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            if value is not None:
                update_data[key] = value

        if not update_data:
            return current  # Nothing to update

        # Handle username conflict check
        if "username" in update_data:
            new_username = update_data["username"]
            if new_username != current.username:
                # Check if username is taken
                conflict_check = (
                    self.supabase.table("users").select("id").eq("username", new_username).execute()
                )

                if conflict_check.data:
                    raise UsernameConflictError(f"Username '{new_username}' is already taken")

        # Perform update
        result = self.supabase.table("users").update(update_data).eq("auth_id", auth_id).execute()

        if not result.data:
            raise UserServiceError("Failed to update user profile")

        return UserProfile(**result.data[0])

    def soft_delete_user(self, auth_id: str) -> datetime:
        """
        Soft-delete a user account with 30-day grace period.

        Sets deleted_at and schedules actual deletion 30 days out.
        User can cancel by signing back in before the scheduled date.

        Args:
            auth_id: Supabase auth.uid() of the user

        Returns:
            deletion_scheduled_at datetime

        Raises:
            UserNotFoundError: If user not found
        """
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        scheduled = now + timedelta(days=30)

        result = (
            self.supabase.table("users")
            .update({"deleted_at": now.isoformat(), "deletion_scheduled_at": scheduled.isoformat()})
            .eq("auth_id", auth_id)
            .execute()
        )

        if not result.data:
            raise UserNotFoundError(f"User with auth_id {auth_id} not found")

        return scheduled

    def record_session_completion(self, user_id: str, focus_minutes: int) -> None:
        """
        Update user stats after completing a session.

        Increments session_count by 1 and adds focus_minutes to total_focus_minutes.

        Args:
            user_id: User ID (not auth_id)
            focus_minutes: Minutes spent focusing in the session
        """
        # Use raw SQL for atomic increment
        # This avoids race conditions if user completes multiple sessions
        self.supabase.rpc(
            "increment_user_stats",
            {
                "p_user_id": user_id,
                "p_focus_minutes": focus_minutes,
            },
        ).execute()
