"""
Global exception handlers for FastAPI.

Maps domain exceptions to HTTP responses, eliminating try/except
boilerplate from routers. Register with register_exception_handlers(app).
"""

import logging
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def error_response(status_code: int, detail: str, code: Optional[str] = None) -> JSONResponse:
    """Build a standardized error JSON response."""
    content: dict = {"detail": detail}
    if code:
        content["code"] = code
    return JSONResponse(status_code=status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""
    # Credit exceptions
    from app.models.credit import (
        CreditNotFoundError,
        GiftLimitExceededError,
        GiftNotAllowedError,
        InsufficientCreditsError,
        InvalidReferralCodeError,
        ReferralAlreadyAppliedError,
        SelfReferralError,
    )

    # Rating exceptions
    from app.models.rating import (
        InvalidRatingTargetError,
        NoPendingRatingsError,
        RatingAlreadyExistsError,
        RedReasonRequiredError,
        SessionNotRatableError,
    )

    # Reflection exceptions
    from app.models.reflection import NotSessionParticipantError
    from app.models.reflection import SessionNotFoundError as ReflectionSessionNotFoundError

    # LiveKit exceptions
    from app.services.livekit_service import LiveKitServiceError

    # Session exceptions
    from app.services.session_service import (
        AlreadyInSessionError,
        SessionFullError,
        SessionPhaseError,
    )
    from app.services.session_service import (
        SessionNotFoundError as SessionServiceNotFoundError,
    )

    # User exceptions
    from app.services.user_service import UsernameConflictError, UserNotFoundError

    # --- Credit handlers ---

    @app.exception_handler(CreditNotFoundError)
    async def _credit_not_found(request: Request, exc: CreditNotFoundError) -> JSONResponse:
        return error_response(404, "Credit record not found.", "CREDIT_NOT_FOUND")

    @app.exception_handler(InsufficientCreditsError)
    async def _insufficient_credits(
        request: Request, exc: InsufficientCreditsError
    ) -> JSONResponse:
        return error_response(
            402,
            f"Insufficient credits. Available: {exc.available}, Required: {exc.required}",
            "INSUFFICIENT_CREDITS",
        )

    @app.exception_handler(GiftNotAllowedError)
    async def _gift_not_allowed(request: Request, exc: GiftNotAllowedError) -> JSONResponse:
        return error_response(
            403,
            f"Gifting not allowed for {exc.tier.value} tier. Upgrade to Pro or Elite.",
            "GIFT_NOT_ALLOWED",
        )

    @app.exception_handler(GiftLimitExceededError)
    async def _gift_limit(request: Request, exc: GiftLimitExceededError) -> JSONResponse:
        return error_response(
            429,
            f"Weekly gift limit reached ({exc.sent}/{exc.limit}). Resets on your refresh date.",
            "GIFT_LIMIT_EXCEEDED",
        )

    @app.exception_handler(ReferralAlreadyAppliedError)
    async def _referral_already(request: Request, exc: ReferralAlreadyAppliedError) -> JSONResponse:
        return error_response(
            409, "You have already used a referral code.", "REFERRAL_ALREADY_APPLIED"
        )

    @app.exception_handler(SelfReferralError)
    async def _self_referral(request: Request, exc: SelfReferralError) -> JSONResponse:
        return error_response(400, "Cannot use your own referral code.", "SELF_REFERRAL")

    @app.exception_handler(InvalidReferralCodeError)
    async def _invalid_referral(request: Request, exc: InvalidReferralCodeError) -> JSONResponse:
        return error_response(404, "Invalid referral code.", "INVALID_REFERRAL_CODE")

    # --- User handlers ---

    @app.exception_handler(UserNotFoundError)
    async def _user_not_found(request: Request, exc: UserNotFoundError) -> JSONResponse:
        return error_response(404, "User not found.", "USER_NOT_FOUND")

    @app.exception_handler(UsernameConflictError)
    async def _username_conflict(request: Request, exc: UsernameConflictError) -> JSONResponse:
        return error_response(409, str(exc), "USERNAME_CONFLICT")

    # --- Session handlers ---

    @app.exception_handler(SessionServiceNotFoundError)
    async def _session_not_found(
        request: Request, exc: SessionServiceNotFoundError
    ) -> JSONResponse:
        return error_response(404, "Session not found.", "SESSION_NOT_FOUND")

    @app.exception_handler(SessionFullError)
    async def _session_full(request: Request, exc: SessionFullError) -> JSONResponse:
        return error_response(409, "No available sessions found.", "SESSION_FULL")

    @app.exception_handler(AlreadyInSessionError)
    async def _already_in_session(request: Request, exc: AlreadyInSessionError) -> JSONResponse:
        return error_response(
            409, "You are already in a session at this time slot.", "ALREADY_IN_SESSION"
        )

    @app.exception_handler(SessionPhaseError)
    async def _session_phase(request: Request, exc: SessionPhaseError) -> JSONResponse:
        return error_response(
            409,
            f"Session is in {exc.current_phase} phase, requires {exc.required_phase}.",
            "SESSION_PHASE_ERROR",
        )

    # --- Reflection handlers ---

    @app.exception_handler(ReflectionSessionNotFoundError)
    async def _reflection_session_not_found(
        request: Request, exc: ReflectionSessionNotFoundError
    ) -> JSONResponse:
        return error_response(404, "Session not found.", "SESSION_NOT_FOUND")

    @app.exception_handler(NotSessionParticipantError)
    async def _not_participant(request: Request, exc: NotSessionParticipantError) -> JSONResponse:
        return error_response(403, "You are not a participant in this session.", "NOT_PARTICIPANT")

    # --- Rating handlers ---

    @app.exception_handler(RedReasonRequiredError)
    async def _red_reason_required(request: Request, exc: RedReasonRequiredError) -> JSONResponse:
        return error_response(
            422, "Red ratings require at least one reason.", "RED_REASON_REQUIRED"
        )

    @app.exception_handler(SessionNotRatableError)
    async def _session_not_ratable(request: Request, exc: SessionNotRatableError) -> JSONResponse:
        return error_response(403, "This session is not in a ratable state.", "SESSION_NOT_RATABLE")

    @app.exception_handler(InvalidRatingTargetError)
    async def _invalid_rating_target(
        request: Request, exc: InvalidRatingTargetError
    ) -> JSONResponse:
        return error_response(400, "Invalid rating target.", "INVALID_RATING_TARGET")

    @app.exception_handler(RatingAlreadyExistsError)
    async def _rating_exists(request: Request, exc: RatingAlreadyExistsError) -> JSONResponse:
        return error_response(
            409, "You have already rated participants in this session.", "RATING_ALREADY_EXISTS"
        )

    @app.exception_handler(NoPendingRatingsError)
    async def _no_pending_ratings(request: Request, exc: NoPendingRatingsError) -> JSONResponse:
        return error_response(
            404, "No pending ratings found for this session.", "NO_PENDING_RATINGS"
        )

    # --- Moderation handlers ---

    from app.models.moderation import (
        DuplicateReportError,
        ReportLimitExceededError,
        SelfReportError,
    )

    @app.exception_handler(SelfReportError)
    async def _self_report(request: Request, exc: SelfReportError) -> JSONResponse:
        return error_response(400, "Cannot report yourself.", "SELF_REPORT")

    @app.exception_handler(DuplicateReportError)
    async def _duplicate_report(request: Request, exc: DuplicateReportError) -> JSONResponse:
        return error_response(
            409, "You have already reported this user for this session.", "DUPLICATE_REPORT"
        )

    @app.exception_handler(ReportLimitExceededError)
    async def _report_limit(request: Request, exc: ReportLimitExceededError) -> JSONResponse:
        return error_response(
            429, "Report limit reached for this session.", "REPORT_LIMIT_EXCEEDED"
        )

    # --- Partner handlers ---

    from app.models.partner import (
        AlreadyPartnersError,
        InvalidInterestTagError,
        InvitationExpiredError,
        InvitationNotFoundError,
        NotPartnerError,
        PartnerLimitError,
        PartnerRequestExistsError,
        PartnershipNotFoundError,
        SelfPartnerError,
    )

    @app.exception_handler(PartnershipNotFoundError)
    async def _partnership_not_found(
        request: Request, exc: PartnershipNotFoundError
    ) -> JSONResponse:
        return error_response(404, "Partnership not found.", "PARTNERSHIP_NOT_FOUND")

    @app.exception_handler(AlreadyPartnersError)
    async def _already_partners(request: Request, exc: AlreadyPartnersError) -> JSONResponse:
        return error_response(
            409, "A partnership already exists between these users.", "ALREADY_PARTNERS"
        )

    @app.exception_handler(PartnerRequestExistsError)
    async def _partner_request_exists(
        request: Request, exc: PartnerRequestExistsError
    ) -> JSONResponse:
        return error_response(409, "A partner request already exists.", "PARTNER_REQUEST_EXISTS")

    @app.exception_handler(SelfPartnerError)
    async def _self_partner(request: Request, exc: SelfPartnerError) -> JSONResponse:
        return error_response(400, "Cannot send partner request to yourself.", "SELF_PARTNER")

    @app.exception_handler(PartnerLimitError)
    async def _partner_limit(request: Request, exc: PartnerLimitError) -> JSONResponse:
        return error_response(429, "Maximum number of partners reached.", "PARTNER_LIMIT_EXCEEDED")

    @app.exception_handler(InvitationNotFoundError)
    async def _invitation_not_found(request: Request, exc: InvitationNotFoundError) -> JSONResponse:
        return error_response(404, "Invitation not found.", "INVITATION_NOT_FOUND")

    @app.exception_handler(InvitationExpiredError)
    async def _invitation_expired(request: Request, exc: InvitationExpiredError) -> JSONResponse:
        return error_response(410, "Invitation has expired.", "INVITATION_EXPIRED")

    @app.exception_handler(NotPartnerError)
    async def _not_partner(request: Request, exc: NotPartnerError) -> JSONResponse:
        return error_response(403, "You can only invite partners to private tables.", "NOT_PARTNER")

    @app.exception_handler(InvalidInterestTagError)
    async def _invalid_interest_tag(request: Request, exc: InvalidInterestTagError) -> JSONResponse:
        return error_response(400, str(exc), "INVALID_INTEREST_TAG")

    # --- Schedule handlers ---

    from app.models.schedule import (
        ScheduleLimitError,
        ScheduleNotFoundError,
        ScheduleOwnershipError,
        SchedulePermissionError,
    )

    @app.exception_handler(ScheduleNotFoundError)
    async def _schedule_not_found(request: Request, exc: ScheduleNotFoundError) -> JSONResponse:
        return error_response(404, "Schedule not found.", "SCHEDULE_NOT_FOUND")

    @app.exception_handler(SchedulePermissionError)
    async def _schedule_permission(request: Request, exc: SchedulePermissionError) -> JSONResponse:
        return error_response(
            403,
            "Recurring schedules require the Unlimited plan.",
            "SCHEDULE_PERMISSION",
        )

    @app.exception_handler(ScheduleOwnershipError)
    async def _schedule_ownership(request: Request, exc: ScheduleOwnershipError) -> JSONResponse:
        return error_response(
            403, "You are not the creator of this schedule.", "SCHEDULE_OWNERSHIP"
        )

    @app.exception_handler(ScheduleLimitError)
    async def _schedule_limit(request: Request, exc: ScheduleLimitError) -> JSONResponse:
        return error_response(
            429, "Maximum number of recurring schedules reached.", "SCHEDULE_LIMIT_EXCEEDED"
        )

    # --- Infrastructure handlers ---

    @app.exception_handler(LiveKitServiceError)
    async def _livekit_error(request: Request, exc: LiveKitServiceError) -> JSONResponse:
        logger.error("LiveKit service error: %s", exc)
        return error_response(502, "LiveKit service error.", "LIVEKIT_ERROR")

    # --- Catch-all ---

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return error_response(500, "Internal server error.", "INTERNAL_ERROR")
