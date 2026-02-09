"""
Pydantic models for user-related operations.

Models:
- UserProfile: Full profile for authenticated user
- UserPublicProfile: Limited fields visible to other users
- UserProfileUpdate: Partial update request model
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserProfile(BaseModel):
    """Full user profile for authenticated user (GET /users/me)."""

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: str
    auth_id: str
    email: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None

    # Avatar & Social
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    social_links: dict[str, Any] = Field(default_factory=dict)
    study_interests: list[str] = Field(default_factory=list)
    preferred_language: str = "en"

    # Stats
    reliability_score: Decimal = Decimal("100.00")
    total_focus_minutes: int = 0
    session_count: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    last_session_date: Optional[date] = None

    # Credits (joined from credits table)
    credits_remaining: int = 0
    credits_used_this_week: int = 0
    credit_tier: str = "free"
    credit_refresh_date: Optional[datetime] = None

    # Pixel Art
    pixel_avatar_id: Optional[str] = None

    # Onboarding & Preferences
    is_onboarded: bool = False
    default_table_mode: str = "forced_audio"

    # Settings
    activity_tracking_enabled: bool = False
    email_notifications_enabled: bool = True
    push_notifications_enabled: bool = True

    # Timestamps
    created_at: datetime
    updated_at: datetime
    banned_until: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deletion_scheduled_at: Optional[datetime] = None


class UserPublicProfile(BaseModel):
    """Limited public profile visible to other users (GET /users/{user_id}).

    Excludes: email, auth_id, settings, banned_until
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    study_interests: list[str] = Field(default_factory=list)

    # Public stats only
    reliability_score: Decimal = Decimal("100.00")
    total_focus_minutes: int = 0
    session_count: int = 0
    current_streak: int = 0
    longest_streak: int = 0


class UserProfileUpdate(BaseModel):
    """Partial update model for PATCH /users/me.

    All fields are optional. Only provided fields are updated.
    """

    username: Optional[str] = Field(None, min_length=3, max_length=30)
    display_name: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=160)
    avatar_config: Optional[dict[str, Any]] = None
    social_links: Optional[dict[str, Any]] = None
    study_interests: Optional[list[str]] = None
    preferred_language: Optional[str] = None
    pixel_avatar_id: Optional[str] = None
    is_onboarded: Optional[bool] = None
    default_table_mode: Optional[str] = None
    activity_tracking_enabled: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None

    @field_validator("default_table_mode")
    @classmethod
    def validate_table_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("forced_audio", "quiet"):
            raise ValueError("Table mode must be 'forced_audio' or 'quiet'")
        return v

    @field_validator("pixel_avatar_id")
    @classmethod
    def validate_pixel_avatar(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from app.core.constants import PIXEL_CHARACTERS

        if v not in PIXEL_CHARACTERS:
            raise ValueError(f"Invalid pixel avatar. Must be one of: {PIXEL_CHARACTERS}")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Alphanumeric and underscores only, lowercase
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v.lower()

    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("en", "zh-TW"):
            raise ValueError("Language must be 'en' or 'zh-TW'")
        return v


class DeleteAccountResponse(BaseModel):
    """Response for DELETE /users/me (soft delete with grace period)."""

    message: str
    deletion_scheduled_at: datetime
