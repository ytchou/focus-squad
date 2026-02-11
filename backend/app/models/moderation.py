"""
Chat safety & moderation models.

Three-layer moderation: client blocklist + server-side flag logging + user reports.
Design doc: .claude/plans/humble-munching-zebra.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import REPORT_DESCRIPTION_MAX_LENGTH

# ===========================================
# Enums
# ===========================================


class ReportCategory(str, Enum):
    """Categories for user reports (escalation-focused)."""

    VERBAL_HARASSMENT = "verbal_harassment"
    EXPLICIT_CONTENT = "explicit_content"
    THREATENING_BEHAVIOR = "threatening_behavior"
    SPAM_SCAM = "spam_scam"
    OTHER = "other"


# ===========================================
# Request Models
# ===========================================


class FlaggedMessageRequest(BaseModel):
    """Client-side blocked message logged for pattern detection."""

    session_id: str
    content: str = Field(..., max_length=500)
    matched_pattern: Optional[str] = None  # e.g. "slur", "sexual", "spam"


class SubmitReportRequest(BaseModel):
    """User report for serious issues needing admin review."""

    reported_user_id: str
    session_id: str
    category: ReportCategory
    description: Optional[str] = Field(None, max_length=REPORT_DESCRIPTION_MAX_LENGTH)


# ===========================================
# Response Models
# ===========================================


class FlaggedMessageResponse(BaseModel):
    """Acknowledgement for flagged message logging."""

    success: bool = True


class ReportResponse(BaseModel):
    """A submitted report."""

    id: str
    category: ReportCategory
    status: str
    created_at: datetime


class MyReportsResponse(BaseModel):
    """List of reports submitted by the user."""

    reports: list[ReportResponse]
    total: int


# ===========================================
# Exception Classes
# ===========================================


class ModerationError(Exception):
    """Base exception for moderation errors."""

    pass


class SelfReportError(ModerationError):
    """Cannot report yourself."""

    pass


class DuplicateReportError(ModerationError):
    """Already reported this user for this session."""

    pass


class ReportLimitExceededError(ModerationError):
    """Too many reports in one session."""

    pass
