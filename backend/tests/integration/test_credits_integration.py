"""Integration tests for credit system API endpoints."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import AuthUser, require_auth_from_state
from app.core.middleware import JWTValidationMiddleware
from app.models.credit import (
    CreditBalance,
    CreditNotFoundError,
    GiftLimitExceededError,
    GiftNotAllowedError,
    GiftResponse,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    ReferralInfo,
    SelfReferralError,
    UserTier,
)
from app.models.user import UserProfile
from app.routers.credits import get_credit_service, get_user_service, router
from app.services.credit_service import CreditService
from app.services.user_service import UserService


@pytest.fixture
def mock_user_profile():
    """Mock user profile returned by UserService."""
    return UserProfile(
        id="user-uuid-123",
        auth_id="auth-user-uuid-12345",
        username="testuser",
        email="test@example.com",
        display_name="Test User",
        avatar_config={},
        reliability_score=100.0,
        total_sessions=5,
        essence_balance=10,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_credit_balance():
    """Mock credit balance returned by CreditService."""
    return CreditBalance(
        user_id="user-uuid-123",
        tier=UserTier.FREE,
        credits_remaining=2,
        weekly_allowance=2,
        max_balance=4,
        gifts_sent_this_week=0,
        max_gifts_per_week=0,
        credit_cycle_start=datetime.now(timezone.utc).date(),
        next_refresh=datetime.now(timezone.utc) + timedelta(days=7),
        referral_code="ABC12345",
    )


@pytest.fixture
def mock_referral_info():
    """Mock referral info returned by CreditService."""
    return ReferralInfo(
        referral_code="ABC12345",
        referrals_completed=3,
        referred_by=None,
        shareable_link="https://focus-squad.com/join?ref=ABC12345",
    )


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return AuthUser(auth_id="auth-user-uuid-12345", email="test@example.com")


@pytest.fixture
def mock_user_service(mock_user_profile):
    """Create mock UserService."""
    service = MagicMock(spec=UserService)
    service.get_user_by_auth_id.return_value = mock_user_profile
    return service


@pytest.fixture
def mock_credit_service(mock_credit_balance, mock_referral_info):
    """Create mock CreditService."""
    service = MagicMock(spec=CreditService)
    service.get_balance.return_value = mock_credit_balance
    service.get_referral_info.return_value = mock_referral_info
    return service


@pytest.fixture
def test_app(mock_auth_user, mock_user_service, mock_credit_service):
    """Create test FastAPI app with dependency overrides."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/credits")

    # Override dependencies
    app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
    app.dependency_overrides[get_user_service] = lambda: mock_user_service
    app.dependency_overrides[get_credit_service] = lambda: mock_credit_service

    return app


@pytest.fixture
def client(test_app):
    """Test client for the app."""
    return TestClient(test_app)


class TestGetBalance:
    """Tests for GET /api/v1/credits/balance endpoint."""

    @pytest.mark.integration
    def test_returns_balance_for_authenticated_user(
        self,
        client,
        mock_credit_balance,
    ):
        """Returns credit balance for authenticated user."""
        response = client.get("/api/v1/credits/balance")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-uuid-123"
        assert data["tier"] == "free"
        assert data["credits_remaining"] == 2
        assert data["weekly_allowance"] == 2
        assert data["referral_code"] == "ABC12345"

    @pytest.mark.integration
    def test_returns_401_without_auth(self):
        """Returns 401 when no token provided."""
        # Create app without auth override (requires real auth)
        app = FastAPI()
        app.add_middleware(JWTValidationMiddleware)
        app.include_router(router, prefix="/api/v1/credits")
        client = TestClient(app)

        response = client.get("/api/v1/credits/balance")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_returns_404_when_user_not_found(self, mock_auth_user, mock_credit_service):
        """Returns 404 when user profile not found."""
        # Create app with user service returning None
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        user_service = MagicMock(spec=UserService)
        user_service.get_user_by_auth_id.return_value = None

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: user_service
        app.dependency_overrides[get_credit_service] = lambda: mock_credit_service

        client = TestClient(app)
        response = client.get("/api/v1/credits/balance")

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.integration
    def test_returns_404_when_credit_record_not_found(self, mock_auth_user, mock_user_service):
        """Returns 404 when credit record not found."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.get_balance.side_effect = CreditNotFoundError("Not found")

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.get("/api/v1/credits/balance")

        assert response.status_code == 404
        assert "Credit record not found" in response.json()["detail"]


class TestGiftCredits:
    """Tests for POST /api/v1/credits/gift endpoint."""

    @pytest.mark.integration
    def test_gift_success(self, mock_auth_user, mock_user_service):
        """Successfully gifts credits to another user."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.gift_credit.return_value = GiftResponse(
            success=True,
            new_balance=7,
            message="Successfully gifted 1 credit(s)",
        )

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/gift",
            json={"recipient_user_id": "recipient-uuid", "amount": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_balance"] == 7

    @pytest.mark.integration
    def test_gift_forbidden_for_free_tier(self, mock_auth_user, mock_user_service):
        """Returns 403 when free tier user tries to gift."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.gift_credit.side_effect = GiftNotAllowedError(UserTier.FREE)

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/gift",
            json={"recipient_user_id": "recipient-uuid", "amount": 1},
        )

        assert response.status_code == 403
        assert "Upgrade to Pro or Elite" in response.json()["detail"]

    @pytest.mark.integration
    def test_gift_limit_exceeded(self, mock_auth_user, mock_user_service):
        """Returns 400 when weekly gift limit exceeded."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.gift_credit.side_effect = GiftLimitExceededError(4, 4)

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/gift",
            json={"recipient_user_id": "recipient-uuid", "amount": 1},
        )

        assert response.status_code == 400
        assert "Weekly gift limit reached" in response.json()["detail"]

    @pytest.mark.integration
    def test_gift_insufficient_credits(self, mock_auth_user, mock_user_service):
        """Returns 402 when sender has insufficient credits."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.gift_credit.side_effect = InsufficientCreditsError(
            user_id="user-123", required=2, available=1
        )

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/gift",
            json={"recipient_user_id": "recipient-uuid", "amount": 2},
        )

        assert response.status_code == 402
        assert "Insufficient credits" in response.json()["detail"]


class TestGetReferralInfo:
    """Tests for GET /api/v1/credits/referral endpoint."""

    @pytest.mark.integration
    def test_returns_referral_info(self, client, mock_referral_info):
        """Returns referral info for authenticated user."""
        response = client.get("/api/v1/credits/referral")

        assert response.status_code == 200
        data = response.json()
        assert data["referral_code"] == "ABC12345"
        assert data["referrals_completed"] == 3
        assert "shareable_link" in data


class TestApplyReferralCode:
    """Tests for POST /api/v1/credits/referral/apply endpoint."""

    @pytest.mark.integration
    def test_apply_referral_success(self, mock_auth_user, mock_user_service):
        """Successfully applies referral code."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.apply_referral_code.return_value = "referrer_user"

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/referral/apply",
            json={"referral_code": "XYZ98765"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["referred_by_username"] == "referrer_user"

    @pytest.mark.integration
    def test_apply_referral_already_applied(self, mock_auth_user, mock_user_service):
        """Returns 400 when user already has a referrer."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.apply_referral_code.side_effect = ReferralAlreadyAppliedError("Already used")

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/referral/apply",
            json={"referral_code": "XYZ98765"},
        )

        assert response.status_code == 400
        assert "already used a referral code" in response.json()["detail"]

    @pytest.mark.integration
    def test_apply_own_referral_code(self, mock_auth_user, mock_user_service):
        """Returns 400 when user tries to use own code."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.apply_referral_code.side_effect = SelfReferralError("Self referral")

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/referral/apply",
            json={"referral_code": "ABC12345"},
        )

        assert response.status_code == 400
        assert "own referral code" in response.json()["detail"]

    @pytest.mark.integration
    def test_apply_invalid_referral_code(self, mock_auth_user, mock_user_service):
        """Returns 404 when referral code doesn't exist."""
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/credits")

        credit_service = MagicMock(spec=CreditService)
        credit_service.apply_referral_code.side_effect = InvalidReferralCodeError("Not found")

        app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
        app.dependency_overrides[get_user_service] = lambda: mock_user_service
        app.dependency_overrides[get_credit_service] = lambda: credit_service

        client = TestClient(app)
        response = client.post(
            "/api/v1/credits/referral/apply",
            json={"referral_code": "INVALID123"},
        )

        assert response.status_code == 404
        assert "Invalid referral code" in response.json()["detail"]
