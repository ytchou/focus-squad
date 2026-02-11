"""Unit tests for ModerationService.

Tests:
- log_flagged_message() - inserts flagged message to chat_messages table
- submit_report() - happy path, self-report, duplicate, limit exceeded
- get_user_flag_count() - counts flagged messages in rolling window
- get_my_reports() - returns user's submitted reports
"""

from unittest.mock import MagicMock

import pytest

from app.models.moderation import (
    DuplicateReportError,
    ReportCategory,
    ReportLimitExceededError,
    SelfReportError,
)
from app.services.moderation_service import ModerationService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """ModerationService with mocked Supabase."""
    return ModerationService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _setup_table_router(mock_supabase, table_mocks: dict) -> None:
    """Configure table-specific mock routing."""
    mock_supabase.table.side_effect = lambda name: table_mocks.get(name, MagicMock())


# =============================================================================
# TestLogFlaggedMessage
# =============================================================================


class TestLogFlaggedMessage:
    """Tests for log_flagged_message()."""

    @pytest.mark.unit
    def test_log_flagged_message(self, service, mock_supabase) -> None:
        """Inserts a flagged message with correct fields."""
        chat_messages_mock = MagicMock()
        _setup_table_router(mock_supabase, {"chat_messages": chat_messages_mock})

        chat_messages_mock.insert.return_value.execute.return_value = MagicMock()

        service.log_flagged_message(
            user_id="user-1",
            session_id="session-1",
            content="bad words here",
            matched_pattern="slur",
        )

        chat_messages_mock.insert.assert_called_once_with(
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "content": "bad words here",
                "is_flagged": True,
                "flagged_reason": "slur",
            }
        )


# =============================================================================
# TestSubmitReport
# =============================================================================


class TestSubmitReport:
    """Tests for submit_report()."""

    @pytest.mark.unit
    def test_submit_report_success(self, service, mock_supabase) -> None:
        """Happy path: inserts report and returns the inserted row."""
        reports_mock = MagicMock()
        _setup_table_router(mock_supabase, {"reports": reports_mock})

        # Duplicate check: no existing report
        reports_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Insert returns the new row
        inserted_row = {
            "id": "report-1",
            "reporter_id": "user-1",
            "reported_user_id": "user-2",
            "session_id": "session-1",
            "category": "verbal_harassment",
            "description": "Said mean things",
            "status": "pending",
            "created_at": "2026-02-10T12:00:00+00:00",
        }
        reports_mock.insert.return_value.execute.return_value.data = [inserted_row]

        result = service.submit_report(
            reporter_id="user-1",
            reported_user_id="user-2",
            session_id="session-1",
            category=ReportCategory.VERBAL_HARASSMENT,
            description="Said mean things",
        )

        assert result["id"] == "report-1"
        assert result["category"] == "verbal_harassment"
        assert result["status"] == "pending"
        reports_mock.insert.assert_called_once()

    @pytest.mark.unit
    def test_submit_report_self_report_raises(self, service, mock_supabase) -> None:
        """Raises SelfReportError when reporter_id == reported_user_id."""
        with pytest.raises(SelfReportError, match="Cannot report yourself"):
            service.submit_report(
                reporter_id="user-1",
                reported_user_id="user-1",
                session_id="session-1",
                category=ReportCategory.SPAM_SCAM,
            )

    @pytest.mark.unit
    def test_submit_report_duplicate_raises(self, service, mock_supabase) -> None:
        """Raises DuplicateReportError when same reporter+reported+session exists."""
        reports_mock = MagicMock()
        _setup_table_router(mock_supabase, {"reports": reports_mock})

        # Duplicate check: existing report found
        reports_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "existing-report"}
        ]

        with pytest.raises(DuplicateReportError, match="already reported"):
            service.submit_report(
                reporter_id="user-1",
                reported_user_id="user-2",
                session_id="session-1",
                category=ReportCategory.OTHER,
            )

    @pytest.mark.unit
    def test_submit_report_limit_exceeded(self, service, mock_supabase) -> None:
        """Raises ReportLimitExceededError when 3 reports exist for this session."""
        reports_mock = MagicMock()
        _setup_table_router(mock_supabase, {"reports": reports_mock})

        # Duplicate check uses 3 .eq() calls: reporter_id, reported_user_id, session_id
        # Returns no duplicate
        reports_mock.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Session limit check uses 2 .eq() calls: reporter_id, session_id
        # Returns 3 existing reports (at limit)
        reports_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "r-1"},
            {"id": "r-2"},
            {"id": "r-3"},
        ]

        with pytest.raises(ReportLimitExceededError, match="Maximum 3 reports"):
            service.submit_report(
                reporter_id="user-1",
                reported_user_id="user-3",
                session_id="session-1",
                category=ReportCategory.EXPLICIT_CONTENT,
            )


# =============================================================================
# TestGetUserFlagCount
# =============================================================================


class TestGetUserFlagCount:
    """Tests for get_user_flag_count()."""

    @pytest.mark.unit
    def test_get_user_flag_count(self, service, mock_supabase) -> None:
        """Returns count of flagged messages in the rolling window."""
        chat_messages_mock = MagicMock()
        _setup_table_router(mock_supabase, {"chat_messages": chat_messages_mock})

        chat_messages_mock.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
            {"id": "flag-1"},
            {"id": "flag-2"},
            {"id": "flag-3"},
        ]

        count = service.get_user_flag_count("user-1", window_days=7)

        assert count == 3


# =============================================================================
# TestGetMyReports
# =============================================================================


class TestGetMyReports:
    """Tests for get_my_reports()."""

    @pytest.mark.unit
    def test_get_my_reports(self, service, mock_supabase) -> None:
        """Returns list of report dicts for the user."""
        reports_mock = MagicMock()
        _setup_table_router(mock_supabase, {"reports": reports_mock})

        expected_reports = [
            {
                "id": "r-1",
                "category": "verbal_harassment",
                "status": "pending",
                "created_at": "2026-02-10T12:00:00+00:00",
            },
            {
                "id": "r-2",
                "category": "spam_scam",
                "status": "resolved",
                "created_at": "2026-02-09T10:00:00+00:00",
            },
        ]
        reports_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = expected_reports

        result = service.get_my_reports("user-1")

        assert len(result) == 2
        assert result[0]["id"] == "r-1"
        assert result[1]["status"] == "resolved"
