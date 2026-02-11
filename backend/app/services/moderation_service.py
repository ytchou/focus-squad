"""
Moderation service for flagged messages and user reports.

Handles:
- Logging client-side blocked messages for pattern detection
- Submitting user reports for admin escalation
- Duplicate/self-report prevention
- Flag count queries for future auto-escalation

Design doc: .claude/plans/humble-munching-zebra.md
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from supabase import Client

from app.core.constants import FLAG_WINDOW_DAYS, MAX_REPORTS_PER_SESSION
from app.core.database import get_supabase
from app.models.moderation import (
    DuplicateReportError,
    ReportCategory,
    ReportLimitExceededError,
    SelfReportError,
)

logger = logging.getLogger(__name__)


class ModerationService:
    """Service for chat moderation and user reports."""

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def log_flagged_message(
        self,
        user_id: str,
        session_id: str,
        content: str,
        matched_pattern: Optional[str] = None,
    ) -> None:
        """Log a client-side blocked message for pattern detection."""
        self.supabase.table("chat_messages").insert(
            {
                "session_id": session_id,
                "user_id": user_id,
                "content": content,
                "is_flagged": True,
                "flagged_reason": matched_pattern,
            }
        ).execute()
        logger.info(
            "Flagged message logged: user=%s session=%s pattern=%s",
            user_id,
            session_id,
            matched_pattern,
        )

    def submit_report(
        self,
        reporter_id: str,
        reported_user_id: str,
        session_id: str,
        category: ReportCategory,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Submit a user report for admin review."""
        if reporter_id == reported_user_id:
            raise SelfReportError("Cannot report yourself")

        existing = (
            self.supabase.table("reports")
            .select("id")
            .eq("reporter_id", reporter_id)
            .eq("reported_user_id", reported_user_id)
            .eq("session_id", session_id)
            .execute()
        )
        if existing.data:
            raise DuplicateReportError("You have already reported this user for this session")

        session_reports = (
            self.supabase.table("reports")
            .select("id")
            .eq("reporter_id", reporter_id)
            .eq("session_id", session_id)
            .execute()
        )
        if len(session_reports.data) >= MAX_REPORTS_PER_SESSION:
            raise ReportLimitExceededError(f"Maximum {MAX_REPORTS_PER_SESSION} reports per session")

        row = {
            "reporter_id": reporter_id,
            "reported_user_id": reported_user_id,
            "session_id": session_id,
            "category": category.value,
            "description": description,
            "status": "pending",
        }
        result = self.supabase.table("reports").insert(row).execute()
        logger.info(
            "Report submitted: reporter=%s reported=%s category=%s",
            reporter_id,
            reported_user_id,
            category.value,
        )
        return dict(result.data[0]) if result.data else row  # type: ignore[arg-type]

    def get_user_flag_count(self, user_id: str, window_days: int = FLAG_WINDOW_DAYS) -> int:
        """Count flagged messages for a user in the rolling window."""
        since = datetime.now(timezone.utc) - timedelta(days=window_days)
        result = (
            self.supabase.table("chat_messages")
            .select("id")
            .eq("user_id", user_id)
            .eq("is_flagged", True)
            .gte("created_at", since.isoformat())
            .execute()
        )
        return len(result.data)

    def get_my_reports(self, reporter_id: str) -> list[dict[str, Any]]:
        """Get reports submitted by this user."""
        result = (
            self.supabase.table("reports")
            .select("id, category, status, created_at")
            .eq("reporter_id", reporter_id)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        reports: list[dict[str, Any]] = result.data
        return reports
