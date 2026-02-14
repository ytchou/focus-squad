"""
Growth timeline service.

Manages room snapshots at milestone events, uploading images to
Supabase Storage and tracking milestones for the user's growth timeline.
"""

import base64
import logging
import uuid
from typing import Optional

from supabase import Client

from app.core.constants import (
    DISCOVERABLE_COMPANIONS,
    MILESTONE_TYPES,
    SESSION_MILESTONE_INTERVAL,
    SNAPSHOT_MAX_SIZE_BYTES,
)
from app.core.database import get_supabase
from app.models.gamification import (
    InvalidMilestoneTypeError,
    RoomSnapshot,
    SnapshotTooLargeError,
    SnapshotUploadRequest,
    SnapshotUploadResponse,
    TimelineResponse,
)

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "room-snapshots"


class TimelineService:
    """Service for growth timeline snapshots and milestone detection."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def get_timeline(self, user_id: str, page: int = 1, per_page: int = 10) -> TimelineResponse:
        """Get paginated timeline of room snapshots, newest first."""
        offset = (page - 1) * per_page

        result = (
            self.supabase.table("room_snapshots")
            .select("*", count="exact")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        total = result.count if result.count is not None else 0
        snapshots = []

        # Compute base URL once instead of calling get_public_url() per row
        base_url = self.supabase.storage.from_(STORAGE_BUCKET).get_public_url("")
        # Strip trailing slash/empty-path artifacts for clean concatenation
        base_url = base_url.rstrip("/")

        for row in result.data:
            image_path = row["image_path"].lstrip("/")
            image_url = f"{base_url}/{image_path}"
            snapshots.append(
                RoomSnapshot(
                    id=row["id"],
                    milestone_type=row["milestone_type"],
                    image_url=image_url,
                    session_count_at=row.get("session_count_at", 0),
                    diary_excerpt=row.get("diary_excerpt"),
                    metadata=row.get("metadata", {}),
                    created_at=row["created_at"],
                )
            )

        return TimelineResponse(
            snapshots=snapshots,
            total=total,
            page=page,
            per_page=per_page,
        )

    def upload_snapshot(
        self,
        user_id: str,
        request: SnapshotUploadRequest,
        session_count: int = 0,
    ) -> SnapshotUploadResponse:
        """Upload a room snapshot for a milestone event."""
        if request.milestone_type not in MILESTONE_TYPES:
            raise InvalidMilestoneTypeError(f"Invalid milestone type: {request.milestone_type}")

        image_data = base64.b64decode(request.image_base64)
        if len(image_data) > SNAPSHOT_MAX_SIZE_BYTES:
            raise SnapshotTooLargeError(
                f"Image size {len(image_data)} exceeds limit {SNAPSHOT_MAX_SIZE_BYTES}"
            )

        file_id = uuid.uuid4().hex[:12]
        image_path = f"{user_id}/{file_id}.png"

        self.supabase.storage.from_(STORAGE_BUCKET).upload(
            path=image_path,
            file=image_data,
            file_options={"content-type": "image/png"},
        )

        image_url = self.supabase.storage.from_(STORAGE_BUCKET).get_public_url(image_path)

        result = (
            self.supabase.table("room_snapshots")
            .insert(
                {
                    "user_id": user_id,
                    "milestone_type": request.milestone_type,
                    "image_path": image_path,
                    "session_count_at": session_count,
                    "diary_excerpt": request.diary_excerpt,
                    "metadata": request.metadata,
                }
            )
            .execute()
        )

        row = result.data[0]
        return SnapshotUploadResponse(
            id=row["id"],
            image_url=image_url,
            milestone_type=row["milestone_type"],
            created_at=row["created_at"],
        )

    def check_milestones(self, user_id: str) -> list[str]:
        """
        Check which milestones the user has earned but not yet captured.

        Returns list of uncaptured milestone type strings.
        """
        existing = (
            self.supabase.table("room_snapshots")
            .select("milestone_type")
            .eq("user_id", user_id)
            .execute()
        )
        captured = {row["milestone_type"] for row in existing.data}

        uncaptured = []

        # first_item: user has at least 1 furniture item
        if "first_item" not in captured:
            items = (
                self.supabase.table("user_items")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            if items.data:
                uncaptured.append("first_item")

        # session_milestone: every SESSION_MILESTONE_INTERVAL sessions
        session_result = (
            self.supabase.table("sessions")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        session_count = session_result.count if session_result.count is not None else 0

        if session_count >= SESSION_MILESTONE_INTERVAL:
            if "session_milestone" not in captured:
                uncaptured.append("session_milestone")

        # companion_discovered: user has at least 1 discoverable companion
        if "companion_discovered" not in captured:
            companions = (
                self.supabase.table("user_companions")
                .select("companion_type")
                .eq("user_id", user_id)
                .execute()
            )
            discovered = [
                c for c in companions.data if c.get("companion_type") in DISCOVERABLE_COMPANIONS
            ]
            if discovered:
                uncaptured.append("companion_discovered")

        # first_diary: user has at least 1 diary note
        if "first_diary" not in captured:
            diary = (
                self.supabase.table("diary_notes")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .execute()
            )
            if diary.data:
                uncaptured.append("first_diary")

        return uncaptured
