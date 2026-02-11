"""
Moderation router for flagged messages and user reports.

Endpoints:
- POST /flag: Log a client-side blocked message for pattern detection
- POST /reports: Submit a user report for admin review
- GET /reports/mine: Get reports submitted by the authenticated user
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.moderation import (
    FlaggedMessageRequest,
    FlaggedMessageResponse,
    MyReportsResponse,
    ReportResponse,
    SubmitReportRequest,
)
from app.services.moderation_service import ModerationService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_moderation_service() -> ModerationService:
    return ModerationService()


def get_user_service() -> UserService:
    return UserService()


@router.post("/flag", response_model=FlaggedMessageResponse)
@limiter.limit("30/minute")
async def flag_message(
    request: Request,
    body: FlaggedMessageRequest,
    user: AuthUser = Depends(require_auth_from_state),
    moderation_service: ModerationService = Depends(get_moderation_service),
    user_service: UserService = Depends(get_user_service),
) -> FlaggedMessageResponse:
    """Log a client-side blocked message for pattern detection."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    moderation_service.log_flagged_message(
        user_id=profile.id,
        session_id=body.session_id,
        content=body.content,
        matched_pattern=body.matched_pattern,
    )
    return FlaggedMessageResponse(success=True)


@router.post("/reports", response_model=ReportResponse)
@limiter.limit("5/minute")
async def submit_report(
    request: Request,
    report_request: SubmitReportRequest,
    user: AuthUser = Depends(require_auth_from_state),
    moderation_service: ModerationService = Depends(get_moderation_service),
    user_service: UserService = Depends(get_user_service),
) -> ReportResponse:
    """Submit a user report for admin review."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    result = moderation_service.submit_report(
        reporter_id=profile.id,
        reported_user_id=report_request.reported_user_id,
        session_id=report_request.session_id,
        category=report_request.category,
        description=report_request.description,
    )
    return ReportResponse(
        id=result["id"],
        category=result["category"],
        status=result["status"],
        created_at=result["created_at"],
    )


@router.get("/reports/mine", response_model=MyReportsResponse)
async def get_my_reports(
    user: AuthUser = Depends(require_auth_from_state),
    moderation_service: ModerationService = Depends(get_moderation_service),
    user_service: UserService = Depends(get_user_service),
) -> MyReportsResponse:
    """Get reports submitted by the authenticated user."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    reports = moderation_service.get_my_reports(profile.id)
    return MyReportsResponse(
        reports=[ReportResponse(**r) for r in reports],
        total=len(reports),
    )
