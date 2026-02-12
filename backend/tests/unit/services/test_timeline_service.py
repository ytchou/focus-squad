"""Unit tests for TimelineService (TDD — written before implementation).

Tests:
- upload_snapshot() - valid upload, invalid milestone, too-large image
- check_milestones() - first_item, session_milestone, already captured
- get_timeline() - pagination, empty state
"""

import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.constants import SNAPSHOT_MAX_SIZE_BYTES
from app.models.gamification import (
    InvalidMilestoneTypeError,
    SnapshotTooLargeError,
    SnapshotUploadRequest,
    SnapshotUploadResponse,
    TimelineResponse,
)
from app.services.timeline_service import TimelineService


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    return TimelineService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.gte.return_value = mock
    mock.order.return_value = mock
    mock.range.return_value = mock
    mock.insert.return_value = mock
    mock.execute.return_value = MagicMock(data=[], count=0)
    return mock


def _setup_tables(mock_supabase, table_names):
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


def _small_image_b64():
    """A tiny valid base64 PNG (well under size limit)."""
    return base64.b64encode(b"fake-png-data-small").decode()


def _large_image_b64():
    """Base64 that decodes to > SNAPSHOT_MAX_SIZE_BYTES."""
    data = b"x" * (SNAPSHOT_MAX_SIZE_BYTES + 1)
    return base64.b64encode(data).decode()


# =============================================================================
# upload_snapshot()
# =============================================================================


class TestUploadSnapshot:
    def test_valid_upload_returns_response(self, service, mock_supabase):
        """Successfully uploads snapshot to storage and inserts DB row."""
        tables = _setup_tables(mock_supabase, ["room_snapshots"])

        # Mock storage upload
        storage_bucket = MagicMock()
        storage_bucket.upload.return_value = None
        storage_bucket.get_public_url.return_value = (
            "https://storage.example.com/room-snapshots/user-1/abc.png"
        )
        mock_supabase.storage.from_.return_value = storage_bucket

        # Mock DB insert
        now = datetime.now(timezone.utc)
        tables["room_snapshots"].execute.return_value = MagicMock(
            data=[
                {
                    "id": "snap-1",
                    "milestone_type": "first_item",
                    "image_path": "user-1/abc.png",
                    "session_count_at": 5,
                    "diary_excerpt": "Got my first desk!",
                    "metadata": {},
                    "created_at": now.isoformat(),
                }
            ]
        )

        request = SnapshotUploadRequest(
            milestone_type="first_item",
            image_base64=_small_image_b64(),
            diary_excerpt="Got my first desk!",
            metadata={},
        )

        result = service.upload_snapshot("user-1", request, session_count=5)

        assert isinstance(result, SnapshotUploadResponse)
        assert result.milestone_type == "first_item"
        storage_bucket.upload.assert_called_once()
        mock_supabase.table.assert_any_call("room_snapshots")

    def test_invalid_milestone_type_raises(self, service, mock_supabase):
        """Raises InvalidMilestoneTypeError for unknown milestone type."""
        request = SnapshotUploadRequest(
            milestone_type="invalid_type",
            image_base64=_small_image_b64(),
        )

        with pytest.raises(InvalidMilestoneTypeError):
            service.upload_snapshot("user-1", request, session_count=0)

    def test_too_large_image_raises(self, service, mock_supabase):
        """Raises SnapshotTooLargeError when decoded image exceeds size limit."""
        request = SnapshotUploadRequest(
            milestone_type="first_item",
            image_base64=_large_image_b64(),
        )

        with pytest.raises(SnapshotTooLargeError):
            service.upload_snapshot("user-1", request, session_count=0)


# =============================================================================
# check_milestones()
# =============================================================================


class TestCheckMilestones:
    def test_first_item_detected(self, service, mock_supabase):
        """Detects first_item milestone when user has items but no snapshot."""
        tables = _setup_tables(
            mock_supabase,
            ["room_snapshots", "user_items", "sessions", "user_companions", "diary_notes"],
        )

        # No existing snapshots
        tables["room_snapshots"].execute.return_value = MagicMock(data=[])

        # User has items
        tables["user_items"].execute.return_value = MagicMock(data=[{"id": "item-1"}], count=1)

        # User has 3 sessions
        tables["sessions"].execute.return_value = MagicMock(
            data=[{"id": "s1"}, {"id": "s2"}, {"id": "s3"}], count=3
        )

        # No companions discovered
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        # Has diary entries
        tables["diary_notes"].execute.return_value = MagicMock(data=[{"id": "d1"}], count=1)

        result = service.check_milestones("user-1")

        assert "first_item" in result

    def test_session_milestone_10(self, service, mock_supabase):
        """Detects session_milestone when user has 10+ sessions and no snapshot."""
        tables = _setup_tables(
            mock_supabase,
            ["room_snapshots", "user_items", "sessions", "user_companions", "diary_notes"],
        )

        # Has first_item snapshot already
        tables["room_snapshots"].execute.return_value = MagicMock(
            data=[{"milestone_type": "first_item"}]
        )

        # No items (won't trigger first_item again)
        tables["user_items"].execute.return_value = MagicMock(data=[], count=0)

        # User has 10 sessions
        tables["sessions"].execute.return_value = MagicMock(
            data=[{"id": f"s{i}"} for i in range(10)], count=10
        )

        # No discovered companions
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        # No diary
        tables["diary_notes"].execute.return_value = MagicMock(data=[], count=0)

        result = service.check_milestones("user-1")

        assert "session_milestone" in result

    def test_already_captured_not_returned(self, service, mock_supabase):
        """Milestones already captured as snapshots are not returned."""
        tables = _setup_tables(
            mock_supabase,
            ["room_snapshots", "user_items", "sessions", "user_companions", "diary_notes"],
        )

        # All common milestones already captured
        tables["room_snapshots"].execute.return_value = MagicMock(
            data=[
                {"milestone_type": "first_item"},
                {"milestone_type": "first_diary"},
            ]
        )

        # User has items (would trigger first_item, but already captured)
        tables["user_items"].execute.return_value = MagicMock(data=[{"id": "item-1"}], count=1)

        # 3 sessions (not enough for session_milestone)
        tables["sessions"].execute.return_value = MagicMock(
            data=[{"id": "s1"}, {"id": "s2"}, {"id": "s3"}], count=3
        )

        # No discovered companions
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        # Has diary but already captured
        tables["diary_notes"].execute.return_value = MagicMock(data=[{"id": "d1"}], count=1)

        result = service.check_milestones("user-1")

        assert "first_item" not in result
        assert "first_diary" not in result

    def test_companion_discovered_milestone(self, service, mock_supabase):
        """Detects companion_discovered when user has a discoverable companion."""
        tables = _setup_tables(
            mock_supabase,
            ["room_snapshots", "user_items", "sessions", "user_companions", "diary_notes"],
        )

        tables["room_snapshots"].execute.return_value = MagicMock(data=[])
        tables["user_items"].execute.return_value = MagicMock(data=[], count=0)
        tables["sessions"].execute.return_value = MagicMock(data=[], count=0)
        tables["user_companions"].execute.return_value = MagicMock(
            data=[{"companion_type": "owl", "is_discovered": True}]
        )
        tables["diary_notes"].execute.return_value = MagicMock(data=[], count=0)

        result = service.check_milestones("user-1")

        assert "companion_discovered" in result


# =============================================================================
# get_timeline()
# =============================================================================


class TestGetTimeline:
    def test_returns_paginated_snapshots(self, service, mock_supabase):
        """Returns paginated timeline with snapshot data."""
        tables = _setup_tables(mock_supabase, ["room_snapshots"])

        now = datetime.now(timezone.utc)
        tables["room_snapshots"].select.return_value = tables["room_snapshots"]
        tables["room_snapshots"].execute.return_value = MagicMock(
            data=[
                {
                    "id": "snap-1",
                    "milestone_type": "first_item",
                    "image_path": "user-1/abc.png",
                    "session_count_at": 5,
                    "diary_excerpt": "My first item!",
                    "metadata": {},
                    "created_at": now.isoformat(),
                }
            ],
            count=1,
        )

        # Mock storage for public URL
        storage_bucket = MagicMock()
        storage_bucket.get_public_url.return_value = (
            "https://storage.example.com/room-snapshots/user-1/abc.png"
        )
        mock_supabase.storage.from_.return_value = storage_bucket

        result = service.get_timeline("user-1", page=1, per_page=10)

        assert isinstance(result, TimelineResponse)
        assert result.total == 1
        assert result.page == 1
        assert len(result.snapshots) == 1
        assert result.snapshots[0].milestone_type == "first_item"

    def test_empty_timeline(self, service, mock_supabase):
        """Returns empty timeline when no snapshots exist."""
        tables = _setup_tables(mock_supabase, ["room_snapshots"])
        tables["room_snapshots"].execute.return_value = MagicMock(data=[], count=0)

        result = service.get_timeline("user-1", page=1, per_page=10)

        assert isinstance(result, TimelineResponse)
        assert result.total == 0
        assert result.snapshots == []
