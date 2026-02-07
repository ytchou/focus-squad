"""Unit tests for credit router endpoints.

Tests each endpoint by calling the async handler directly,
mocking AuthUser, CreditService, and UserService dependencies.

Endpoints tested:
- GET /balance - get_credit_balance()
- POST /gift - gift_credits()
- GET /referral - get_referral_info()
- POST /referral/apply - apply_referral_code()
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.credit import (
    ApplyReferralRequest,
    CreditNotFoundError,
    GiftLimitExceededError,
    GiftNotAllowedError,
    GiftRequest,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    SelfReferralError,
    UserTier,
)
from app.routers.credits import (
    apply_referral_code,
    get_credit_balance,
    get_referral_info,
    gift_credits,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_user() -> AuthUser:
    """Authenticated user fixture."""
    return AuthUser(auth_id="auth-abc-123", email="test@example.com")


@pytest.fixture
def mock_profile() -> MagicMock:
    """User profile returned by user_service.get_user_by_auth_id()."""
    profile = MagicMock()
    profile.id = "user-uuid-456"
    return profile


@pytest.fixture
def credit_service() -> MagicMock:
    """Mocked CreditService."""
    return MagicMock()


@pytest.fixture
def user_service(mock_profile: MagicMock) -> MagicMock:
    """Mocked UserService that returns a profile by default."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = mock_profile
    return svc


@pytest.fixture
def user_service_no_profile() -> MagicMock:
    """Mocked UserService that returns None (user not found)."""
    svc = MagicMock()
    svc.get_user_by_auth_id.return_value = None
    return svc


# =============================================================================
# GET /balance - get_credit_balance()
# =============================================================================


class TestGetCreditBalance:
    """Tests for the get_credit_balance endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_balance(self, mock_user, credit_service, user_service, mock_profile):
        """Happy path: returns CreditBalance from service."""
        expected_balance = MagicMock()
        credit_service.get_balance.return_value = expected_balance

        result = await get_credit_balance(
            user=mock_user,
            credit_service=credit_service,
            user_service=user_service,
        )

        assert result is expected_balance
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        credit_service.get_balance.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_user, credit_service, user_service_no_profile
    ):
        """User not in database raises 404."""
        with pytest.raises(HTTPException) as exc_info:
            await get_credit_balance(
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service_no_profile,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credit_not_found_raises_404(self, mock_user, credit_service, user_service):
        """Missing credit record raises 404 with onboarding hint."""
        credit_service.get_balance.side_effect = CreditNotFoundError("not found")

        with pytest.raises(HTTPException) as exc_info:
            await get_credit_balance(
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 404
        assert "Credit record not found" in exc_info.value.detail
        assert "onboarding" in exc_info.value.detail


# =============================================================================
# POST /gift - gift_credits()
# =============================================================================


class TestGiftCredits:
    """Tests for the gift_credits endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gift_success(self, mock_user, credit_service, user_service, mock_profile):
        """Happy path: gift processed and response returned."""
        expected_response = MagicMock()
        credit_service.gift_credit.return_value = expected_response
        request = GiftRequest(recipient_user_id="recipient-789", amount=2)

        result = await gift_credits(
            request=request,
            user=mock_user,
            credit_service=credit_service,
            user_service=user_service,
            x_idempotency_key="idem-key-1",
        )

        assert result is expected_response
        credit_service.gift_credit.assert_called_once_with(
            sender_id=mock_profile.id,
            recipient_id="recipient-789",
            amount=2,
            idempotency_key="idem-key-1",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gift_without_idempotency_key(
        self, mock_user, credit_service, user_service, mock_profile
    ):
        """Idempotency key is optional and passes None when absent."""
        expected_response = MagicMock()
        credit_service.gift_credit.return_value = expected_response
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        result = await gift_credits(
            request=request,
            user=mock_user,
            credit_service=credit_service,
            user_service=user_service,
            x_idempotency_key=None,
        )

        assert result is expected_response
        credit_service.gift_credit.assert_called_once_with(
            sender_id=mock_profile.id,
            recipient_id="recipient-789",
            amount=1,
            idempotency_key=None,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gift_user_not_found_raises_404(
        self, mock_user, credit_service, user_service_no_profile
    ):
        """Sender not in database raises 404."""
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service_no_profile,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gift_not_allowed_raises_403(self, mock_user, credit_service, user_service):
        """Free tier user attempting to gift raises 403."""
        credit_service.gift_credit.side_effect = GiftNotAllowedError(tier=UserTier.FREE)
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 403
        assert "free" in exc_info.value.detail.lower()
        assert "Upgrade to Pro or Elite" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_gift_limit_exceeded_raises_400(self, mock_user, credit_service, user_service):
        """Exceeded weekly gift limit raises 400."""
        credit_service.gift_credit.side_effect = GiftLimitExceededError(sent=4, limit=4)
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 400
        assert "4/4" in exc_info.value.detail
        assert "gift limit" in exc_info.value.detail.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_insufficient_credits_raises_402(self, mock_user, credit_service, user_service):
        """Not enough credits to gift raises 402."""
        credit_service.gift_credit.side_effect = InsufficientCreditsError(
            user_id="user-uuid-456", available=0, required=2
        )
        request = GiftRequest(recipient_user_id="recipient-789", amount=2)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 402
        assert "Available: 0" in exc_info.value.detail
        assert "Required: 2" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_recipient_credit_not_found_raises_404(
        self, mock_user, credit_service, user_service
    ):
        """Recipient credit record missing raises 404 with recipient detail."""
        credit_service.gift_credit.side_effect = CreditNotFoundError(
            "Recipient credit record not found"
        )
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 404
        assert "Recipient" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sender_credit_not_found_raises_404(
        self, mock_user, credit_service, user_service
    ):
        """Sender credit record missing raises 404 with generic detail."""
        credit_service.gift_credit.side_effect = CreditNotFoundError(
            "Sender credit record not found"
        )
        request = GiftRequest(recipient_user_id="recipient-789", amount=1)

        with pytest.raises(HTTPException) as exc_info:
            await gift_credits(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
                x_idempotency_key=None,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Credit record not found."


# =============================================================================
# GET /referral - get_referral_info()
# =============================================================================


class TestGetReferralInfo:
    """Tests for the get_referral_info endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_referral_info(
        self, mock_user, credit_service, user_service, mock_profile
    ):
        """Happy path: returns ReferralInfo from service."""
        expected_info = MagicMock()
        credit_service.get_referral_info.return_value = expected_info

        result = await get_referral_info(
            user=mock_user,
            credit_service=credit_service,
            user_service=user_service,
        )

        assert result is expected_info
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        credit_service.get_referral_info.assert_called_once_with(mock_profile.id)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_user, credit_service, user_service_no_profile
    ):
        """User not in database raises 404."""
        with pytest.raises(HTTPException) as exc_info:
            await get_referral_info(
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service_no_profile,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credit_not_found_raises_404(self, mock_user, credit_service, user_service):
        """Missing credit record raises 404."""
        credit_service.get_referral_info.side_effect = CreditNotFoundError("not found")

        with pytest.raises(HTTPException) as exc_info:
            await get_referral_info(
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 404
        assert "Credit record not found" in exc_info.value.detail


# =============================================================================
# POST /referral/apply - apply_referral_code()
# =============================================================================


class TestApplyReferralCode:
    """Tests for the apply_referral_code endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_success(self, mock_user, credit_service, user_service, mock_profile):
        """Happy path: referral applied, returns success response."""
        credit_service.apply_referral_code.return_value = "referrer_user"
        request = ApplyReferralRequest(referral_code="ABC123")

        result = await apply_referral_code(
            request=request,
            user=mock_user,
            credit_service=credit_service,
            user_service=user_service,
        )

        assert result.success is True
        assert result.referred_by_username == "referrer_user"
        user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        credit_service.apply_referral_code.assert_called_once_with(
            user_id=mock_profile.id,
            referral_code="ABC123",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(
        self, mock_user, credit_service, user_service_no_profile
    ):
        """User not in database raises 404."""
        request = ApplyReferralRequest(referral_code="ABC123")

        with pytest.raises(HTTPException) as exc_info:
            await apply_referral_code(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service_no_profile,
            )

        assert exc_info.value.status_code == 404
        assert "User not found" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_referral_already_applied_raises_400(
        self, mock_user, credit_service, user_service
    ):
        """User already used a referral code raises 400."""
        credit_service.apply_referral_code.side_effect = ReferralAlreadyAppliedError(
            "already applied"
        )
        request = ApplyReferralRequest(referral_code="ABC123")

        with pytest.raises(HTTPException) as exc_info:
            await apply_referral_code(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 400
        assert "already used" in exc_info.value.detail.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_self_referral_raises_400(self, mock_user, credit_service, user_service):
        """Using own referral code raises 400."""
        credit_service.apply_referral_code.side_effect = SelfReferralError("self referral")
        request = ApplyReferralRequest(referral_code="MY_OWN")

        with pytest.raises(HTTPException) as exc_info:
            await apply_referral_code(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 400
        assert "own referral code" in exc_info.value.detail.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_referral_code_raises_404(self, mock_user, credit_service, user_service):
        """Non-existent referral code raises 404."""
        credit_service.apply_referral_code.side_effect = InvalidReferralCodeError("invalid")
        request = ApplyReferralRequest(referral_code="BOGUS")

        with pytest.raises(HTTPException) as exc_info:
            await apply_referral_code(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 404
        assert "Invalid referral code" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credit_not_found_raises_404(self, mock_user, credit_service, user_service):
        """Missing credit record raises 404."""
        credit_service.apply_referral_code.side_effect = CreditNotFoundError("not found")
        request = ApplyReferralRequest(referral_code="VALID")

        with pytest.raises(HTTPException) as exc_info:
            await apply_referral_code(
                request=request,
                user=mock_user,
                credit_service=credit_service,
                user_service=user_service,
            )

        assert exc_info.value.status_code == 404
        assert "Credit record not found" in exc_info.value.detail
