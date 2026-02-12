"""
Companion service for selection and adoption operations.

Handles:
- Listing user's companions
- Starter companion selection
- Visitor companion adoption
- Companion metadata lookups
"""

from datetime import datetime, timezone
from typing import Optional

from supabase import Client

from app.core.constants import COMPANION_METADATA, STARTER_COMPANIONS
from app.core.database import get_supabase
from app.models.room import (
    AlreadyHasStarterError,
    CompanionInfo,
    CompanionServiceError,
    InvalidStarterError,
    VisitorNotFoundError,
)


class CompanionService:
    """Service for companion selection and adoption operations."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def get_companions(self, user_id: str) -> list[CompanionInfo]:
        result = (
            self.supabase.table("user_companions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at")
            .execute()
        )

        return [CompanionInfo(**row) for row in result.data]

    def has_starter(self, user_id: str) -> bool:
        result = (
            self.supabase.table("user_companions")
            .select("id")
            .eq("user_id", user_id)
            .eq("is_starter", True)
            .execute()
        )

        return len(result.data) > 0

    def choose_starter(self, user_id: str, companion_type: str) -> CompanionInfo:
        if companion_type not in STARTER_COMPANIONS:
            raise InvalidStarterError(f"{companion_type} is not a valid starter companion")

        if self.has_starter(user_id):
            raise AlreadyHasStarterError("User already has a starter companion")

        now = datetime.now(timezone.utc).isoformat()

        result = (
            self.supabase.table("user_companions")
            .insert(
                {
                    "user_id": user_id,
                    "companion_type": companion_type,
                    "is_starter": True,
                    "adopted_at": now,
                }
            )
            .execute()
        )

        if not result.data:
            raise CompanionServiceError("Failed to create starter companion")

        return CompanionInfo(**result.data[0])

    def adopt_visitor(self, user_id: str, companion_type: str) -> CompanionInfo:
        result = (
            self.supabase.table("user_companions")
            .select("*")
            .eq("user_id", user_id)
            .eq("companion_type", companion_type)
            .is_("adopted_at", "null")
            .execute()
        )

        if not result.data:
            raise VisitorNotFoundError(f"No visiting {companion_type} found for user")

        visitor = result.data[0]
        now = datetime.now(timezone.utc).isoformat()

        updated = (
            self.supabase.table("user_companions")
            .update({"adopted_at": now})
            .eq("id", visitor["id"])
            .execute()
        )

        if not updated.data:
            raise CompanionServiceError("Failed to adopt visitor")

        return CompanionInfo(**updated.data[0])

    def get_companion_metadata(self, companion_type: str) -> dict:
        return COMPANION_METADATA.get(companion_type, {})
