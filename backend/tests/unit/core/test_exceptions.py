"""Tests for global exception handlers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import register_exception_handlers
from app.models.credit import (
    CreditNotFoundError,
    GiftLimitExceededError,
    GiftNotAllowedError,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    SelfReferralError,
    UserTier,
)
from app.models.rating import (
    InvalidRatingTargetError,
    NoPendingRatingsError,
    RatingAlreadyExistsError,
    RedReasonRequiredError,
    SessionNotRatableError,
)
from app.models.reflection import NotSessionParticipantError
from app.models.reflection import SessionNotFoundError as ReflectionSessionNotFoundError
from app.services.session_service import (
    AlreadyInSessionError,
    SessionFullError,
    SessionPhaseError,
)
from app.services.session_service import (
    SessionNotFoundError as SessionServiceNotFoundError,
)
from app.services.user_service import UsernameConflictError, UserNotFoundError


def _make_app_with_route(exc_to_raise: Exception):
    """Create a minimal FastAPI app that raises the given exception."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test")
    async def trigger():
        raise exc_to_raise

    return TestClient(app, raise_server_exceptions=False)


class TestCreditExceptionHandlers:
    def test_credit_not_found(self):
        client = _make_app_with_route(CreditNotFoundError("Record missing"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "CREDIT_NOT_FOUND"
        assert "Record missing" in resp.json()["detail"]

    def test_insufficient_credits(self):
        client = _make_app_with_route(
            InsufficientCreditsError(user_id="u1", required=3, available=1)
        )
        resp = client.get("/test")
        assert resp.status_code == 402
        assert resp.json()["code"] == "INSUFFICIENT_CREDITS"
        assert "Available: 1" in resp.json()["detail"]
        assert "Required: 3" in resp.json()["detail"]

    def test_gift_not_allowed(self):
        client = _make_app_with_route(GiftNotAllowedError(UserTier.FREE))
        resp = client.get("/test")
        assert resp.status_code == 403
        assert resp.json()["code"] == "GIFT_NOT_ALLOWED"
        assert "free" in resp.json()["detail"]

    def test_gift_limit_exceeded(self):
        client = _make_app_with_route(GiftLimitExceededError(4, 4))
        resp = client.get("/test")
        assert resp.status_code == 429
        assert resp.json()["code"] == "GIFT_LIMIT_EXCEEDED"
        assert "4/4" in resp.json()["detail"]

    def test_referral_already_applied(self):
        client = _make_app_with_route(ReferralAlreadyAppliedError("Already used"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "REFERRAL_ALREADY_APPLIED"

    def test_self_referral(self):
        client = _make_app_with_route(SelfReferralError("Self"))
        resp = client.get("/test")
        assert resp.status_code == 400
        assert resp.json()["code"] == "SELF_REFERRAL"

    def test_invalid_referral_code(self):
        client = _make_app_with_route(InvalidReferralCodeError("Bad code"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "INVALID_REFERRAL_CODE"


class TestUserExceptionHandlers:
    def test_user_not_found(self):
        client = _make_app_with_route(UserNotFoundError("No user"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "USER_NOT_FOUND"

    def test_username_conflict(self):
        client = _make_app_with_route(UsernameConflictError("Taken"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "USERNAME_CONFLICT"


class TestSessionExceptionHandlers:
    def test_session_not_found(self):
        client = _make_app_with_route(SessionServiceNotFoundError("Missing"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "SESSION_NOT_FOUND"

    def test_session_full(self):
        client = _make_app_with_route(SessionFullError("Full"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "SESSION_FULL"

    def test_already_in_session(self):
        client = _make_app_with_route(AlreadyInSessionError("s1", "u1"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "ALREADY_IN_SESSION"

    def test_session_phase_error(self):
        client = _make_app_with_route(SessionPhaseError("setup", "work_1"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "SESSION_PHASE_ERROR"
        assert "setup" in resp.json()["detail"]
        assert "work_1" in resp.json()["detail"]


class TestReflectionExceptionHandlers:
    def test_reflection_session_not_found(self):
        client = _make_app_with_route(ReflectionSessionNotFoundError("s1"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "SESSION_NOT_FOUND"

    def test_not_session_participant(self):
        client = _make_app_with_route(NotSessionParticipantError("s1", "u1"))
        resp = client.get("/test")
        assert resp.status_code == 403
        assert resp.json()["code"] == "NOT_PARTICIPANT"


class TestRatingExceptionHandlers:
    def test_red_reason_required(self):
        client = _make_app_with_route(RedReasonRequiredError())
        resp = client.get("/test")
        assert resp.status_code == 422
        assert resp.json()["code"] == "RED_REASON_REQUIRED"

    def test_session_not_ratable(self):
        client = _make_app_with_route(SessionNotRatableError("s1"))
        resp = client.get("/test")
        assert resp.status_code == 403
        assert resp.json()["code"] == "SESSION_NOT_RATABLE"

    def test_invalid_rating_target(self):
        client = _make_app_with_route(InvalidRatingTargetError("Bad target"))
        resp = client.get("/test")
        assert resp.status_code == 400
        assert resp.json()["code"] == "INVALID_RATING_TARGET"

    def test_rating_already_exists(self):
        client = _make_app_with_route(RatingAlreadyExistsError("s1", "u1"))
        resp = client.get("/test")
        assert resp.status_code == 409
        assert resp.json()["code"] == "RATING_ALREADY_EXISTS"

    def test_no_pending_ratings(self):
        client = _make_app_with_route(NoPendingRatingsError("s1", "u1"))
        resp = client.get("/test")
        assert resp.status_code == 404
        assert resp.json()["code"] == "NO_PENDING_RATINGS"


class TestCatchAllHandler:
    def test_unhandled_exception_returns_500(self):
        client = _make_app_with_route(RuntimeError("Something broke"))
        resp = client.get("/test")
        assert resp.status_code == 500
        assert resp.json()["code"] == "INTERNAL_ERROR"
        assert "Internal server error" in resp.json()["detail"]

    def test_error_response_format(self):
        client = _make_app_with_route(CreditNotFoundError("Test"))
        resp = client.get("/test")
        data = resp.json()
        assert "detail" in data
        assert "code" in data
