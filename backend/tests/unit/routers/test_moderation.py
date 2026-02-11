"""Unit tests for moderation router endpoints.

Tests each endpoint by calling the async handler directly,
mocking AuthUser, ModerationService, and UserService dependencies.

Endpoints tested:
- POST /flag - flag_message()
- POST /reports - submit_report()
- GET /reports/mine - get_my_reports()
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.moderation import (
    DuplicateReportError,
    FlaggedMessageRequest,
    ReportCategory,
    SelfReportError,
    SubmitReportRequest,
)
from app.routers.moderation import flag_message, get_my_reports, submit_report

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def auth_user() -> AuthUser:
    """Authenticated user fixture."""
    return AuthUser(auth_id="auth-abc-123", email="test@example.com")


@pytest.fixture
def mock_profile() -> MagicMock:
    """User profile returned by user_service.get_user_by_auth_id()."""
    profile = MagicMock()
    profile.id = "user-uuid-456"
    return profile


@pytest.fixture
def mock_user_service(mock_profile) -> MagicMock:
    """Mocked UserService that returns a profile by default."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = mock_profile
    return svc


@pytest.fixture
def mock_user_service_no_profile() -> MagicMock:
    """Mocked UserService that returns None (user not found)."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = None
    return svc


@pytest.fixture
def mock_moderation_service() -> MagicMock:
    """Mocked ModerationService."""
    return MagicMock()


# =============================================================================
# POST /flag - flag_message()
# =============================================================================


class TestFlagMessage:
    """Tests for the flag_message endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_flag_message_requires_auth(
        self, mock_moderation_service, mock_user_service_no_profile
    ) -> None:
        """Returns 404 when user profile not found (simulates missing auth)."""
        body = FlaggedMessageRequest(
            session_id="session-1",
            content="bad message",
            matched_pattern="slur",
        )
        auth_user = AuthUser(auth_id="unknown-auth", email="nobody@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await flag_message(
                request=MagicMock(),
                body=body,
                user=auth_user,
                moderation_service=mock_moderation_service,
                user_service=mock_user_service_no_profile,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_flag_message_success(
        self, auth_user, mock_moderation_service, mock_user_service, mock_profile
    ) -> None:
        """Happy path: logs flagged message and returns success."""
        body = FlaggedMessageRequest(
            session_id="session-1",
            content="bad message",
            matched_pattern="slur",
        )

        result = await flag_message(
            request=MagicMock(),
            body=body,
            user=auth_user,
            moderation_service=mock_moderation_service,
            user_service=mock_user_service,
        )

        assert result.success is True
        mock_moderation_service.log_flagged_message.assert_called_once_with(
            user_id=mock_profile.id,
            session_id="session-1",
            content="bad message",
            matched_pattern="slur",
        )
        mock_user_service.get_user_by_auth_id.assert_called_once_with(auth_user.auth_id)


# =============================================================================
# POST /reports - submit_report()
# =============================================================================


class TestSubmitReport:
    """Tests for the submit_report endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_report_requires_auth(
        self, mock_moderation_service, mock_user_service_no_profile
    ) -> None:
        """Returns 404 when user profile not found (simulates missing auth)."""
        report_request = SubmitReportRequest(
            reported_user_id="user-2",
            session_id="session-1",
            category=ReportCategory.SPAM_SCAM,
        )
        auth_user = AuthUser(auth_id="unknown-auth", email="nobody@example.com")

        with pytest.raises(HTTPException) as exc_info:
            await submit_report(
                request=MagicMock(),
                report_request=report_request,
                user=auth_user,
                moderation_service=mock_moderation_service,
                user_service=mock_user_service_no_profile,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_report_success(
        self, auth_user, mock_moderation_service, mock_user_service, mock_profile
    ) -> None:
        """Happy path: submits report and returns ReportResponse."""
        report_request = SubmitReportRequest(
            reported_user_id="user-2",
            session_id="session-1",
            category=ReportCategory.VERBAL_HARASSMENT,
            description="Rude behavior",
        )
        mock_moderation_service.submit_report.return_value = {
            "id": "report-1",
            "category": "verbal_harassment",
            "status": "pending",
            "created_at": "2026-02-10T12:00:00+00:00",
        }

        result = await submit_report(
            request=MagicMock(),
            report_request=report_request,
            user=auth_user,
            moderation_service=mock_moderation_service,
            user_service=mock_user_service,
        )

        assert result.id == "report-1"
        assert result.status == "pending"
        mock_moderation_service.submit_report.assert_called_once_with(
            reporter_id=mock_profile.id,
            reported_user_id="user-2",
            session_id="session-1",
            category=ReportCategory.VERBAL_HARASSMENT,
            description="Rude behavior",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_report_self_report_returns_400(
        self, auth_user, mock_moderation_service, mock_user_service
    ) -> None:
        """SelfReportError propagates from service (handled by global exception handler)."""
        report_request = SubmitReportRequest(
            reported_user_id="user-uuid-456",
            session_id="session-1",
            category=ReportCategory.OTHER,
        )
        mock_moderation_service.submit_report.side_effect = SelfReportError(
            "Cannot report yourself"
        )

        with pytest.raises(SelfReportError):
            await submit_report(
                request=MagicMock(),
                report_request=report_request,
                user=auth_user,
                moderation_service=mock_moderation_service,
                user_service=mock_user_service,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_submit_report_duplicate_returns_409(
        self, auth_user, mock_moderation_service, mock_user_service
    ) -> None:
        """DuplicateReportError propagates from service (handled by global exception handler)."""
        report_request = SubmitReportRequest(
            reported_user_id="user-2",
            session_id="session-1",
            category=ReportCategory.EXPLICIT_CONTENT,
        )
        mock_moderation_service.submit_report.side_effect = DuplicateReportError(
            "You have already reported this user for this session"
        )

        with pytest.raises(DuplicateReportError):
            await submit_report(
                request=MagicMock(),
                report_request=report_request,
                user=auth_user,
                moderation_service=mock_moderation_service,
                user_service=mock_user_service,
            )


# =============================================================================
# GET /reports/mine - get_my_reports()
# =============================================================================


class TestGetMyReports:
    """Tests for the get_my_reports endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_my_reports_success(
        self, auth_user, mock_moderation_service, mock_user_service, mock_profile
    ) -> None:
        """Happy path: returns MyReportsResponse with empty list."""
        mock_moderation_service.get_my_reports.return_value = []

        result = await get_my_reports(
            user=auth_user,
            moderation_service=mock_moderation_service,
            user_service=mock_user_service,
        )

        assert result.total == 0
        assert result.reports == []
        mock_moderation_service.get_my_reports.assert_called_once_with(mock_profile.id)
        mock_user_service.get_user_by_auth_id.assert_called_once_with(auth_user.auth_id)
