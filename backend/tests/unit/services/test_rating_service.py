"""Unit tests for RatingService (TDD — written before implementation)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models.rating import (
    RatingValue,
    RedReasonRequiredError,
    ReliabilityTier,
    SingleRating,
)


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def rating_service(mock_supabase):
    """RatingService with mocked Supabase."""
    from app.services.rating_service import RatingService

    return RatingService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_rating_row(
    rating: str = "green",
    days_ago: int = 0,
    rater_reliability: float = 100.0,
    weight: float = 1.0,
) -> dict:
    """Create a rating record dict as returned from DB."""
    created_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {
        "id": "rating-id",
        "session_id": "session-1",
        "rater_id": "rater-1",
        "ratee_id": "ratee-1",
        "rating": rating,
        "rater_reliability_at_time": rater_reliability,
        "weight": weight,
        "reason": None,
        "created_at": created_at.isoformat(),
    }


def _make_user_row(
    user_id: str = "user-1",
    tier: str = "free",
    session_count: int = 10,
    created_at_days_ago: int = 30,
) -> dict:
    """Create a user record dict for reporting power lookups."""
    created_at = datetime.now(timezone.utc) - timedelta(days=created_at_days_ago)
    return {
        "id": user_id,
        "session_count": session_count,
        "created_at": created_at.isoformat(),
    }


def _make_credit_row(user_id: str = "user-1", tier: str = "free") -> dict:
    """Create a credit record dict for tier lookups."""
    return {
        "user_id": user_id,
        "tier": tier,
    }


# =============================================================================
# TestGetReliabilityTier
# =============================================================================


class TestGetReliabilityTier:
    """Tests for get_reliability_tier() — pure logic, no DB."""

    @pytest.mark.unit
    def test_trusted_tier(self, rating_service) -> None:
        """Score 95-100 with enough ratings = Trusted."""
        assert rating_service.get_reliability_tier(Decimal("100.0"), 10) == ReliabilityTier.TRUSTED
        assert rating_service.get_reliability_tier(Decimal("95.0"), 10) == ReliabilityTier.TRUSTED

    @pytest.mark.unit
    def test_good_tier(self, rating_service) -> None:
        """Score 80-94 = Good."""
        assert rating_service.get_reliability_tier(Decimal("94.99"), 10) == ReliabilityTier.GOOD
        assert rating_service.get_reliability_tier(Decimal("80.0"), 10) == ReliabilityTier.GOOD

    @pytest.mark.unit
    def test_fair_tier(self, rating_service) -> None:
        """Score 60-79 = Fair."""
        assert rating_service.get_reliability_tier(Decimal("79.99"), 10) == ReliabilityTier.FAIR
        assert rating_service.get_reliability_tier(Decimal("60.0"), 10) == ReliabilityTier.FAIR

    @pytest.mark.unit
    def test_below_fair_still_fair(self, rating_service) -> None:
        """Score below 60 but with enough ratings is still Fair (lowest scored tier)."""
        assert rating_service.get_reliability_tier(Decimal("30.0"), 10) == ReliabilityTier.FAIR

    @pytest.mark.unit
    def test_new_user_regardless_of_score(self, rating_service) -> None:
        """Users with <5 non-skip ratings are always New, regardless of score."""
        assert rating_service.get_reliability_tier(Decimal("100.0"), 4) == ReliabilityTier.NEW
        assert rating_service.get_reliability_tier(Decimal("100.0"), 0) == ReliabilityTier.NEW
        assert rating_service.get_reliability_tier(Decimal("50.0"), 3) == ReliabilityTier.NEW


# =============================================================================
# TestCalculateReliabilityScore
# =============================================================================


class TestCalculateReliabilityScore:
    """Tests for calculate_reliability_score() — core algorithm."""

    @pytest.mark.unit
    def test_all_green_returns_100(self, rating_service, mock_supabase) -> None:
        """All green ratings = 100.0 reliability."""
        ratings = [
            _make_rating_row("green", days_ago=0),
            _make_rating_row("green", days_ago=0),
            _make_rating_row("green", days_ago=0),
        ]
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = ratings

        # Mock user lookup for community age gate
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        }

        score = rating_service.calculate_reliability_score("user-1")
        assert score == Decimal("100.00")

    @pytest.mark.unit
    def test_all_red_returns_0(self, rating_service, mock_supabase) -> None:
        """All red ratings = 0.0 reliability (after enough ratings)."""
        ratings = [
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
        ]
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = ratings

        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        }

        score = rating_service.calculate_reliability_score("user-1")
        assert score == Decimal("0.00")

    @pytest.mark.unit
    def test_skip_excluded_from_calculation(self, rating_service, mock_supabase) -> None:
        """Skip ratings are excluded entirely (filtered at DB level by .neq('rating', 'skip'))."""
        # DB query filters out skips, so mock only returns the 1 green
        ratings = [
            _make_rating_row("green", days_ago=0),
        ]
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = ratings

        # Only 1 non-skip rating → blended with default 100
        # blended = (100 * 1 + 100 * 4) / 5 = 100.0
        score = rating_service.calculate_reliability_score("user-1")
        assert score == Decimal("100.00")

    @pytest.mark.unit
    def test_new_user_blend_with_default(self, rating_service, mock_supabase) -> None:
        """Users with <5 non-skip ratings blend with default 100."""
        # 3 reds = raw score 0.0
        # blended = (0 * 3 + 100 * 2) / 5 = 40.0
        ratings = [
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
            _make_rating_row("red", days_ago=0),
        ]
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = ratings

        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        }

        score = rating_service.calculate_reliability_score("user-1")
        assert score == Decimal("40.00")

    @pytest.mark.unit
    def test_no_ratings_returns_default_100(self, rating_service, mock_supabase) -> None:
        """User with no ratings at all keeps default 100."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = []

        score = rating_service.calculate_reliability_score("user-1")
        assert score == Decimal("100.00")

    @pytest.mark.unit
    def test_voter_weight_by_reliability(self, rating_service, mock_supabase) -> None:
        """Ratings from low-reliability users carry less weight."""
        # 1 green from 100-reliability rater, 1 red from 50-reliability rater
        # green: value=1.0, voter_weight=1.0, time_weight~=1.0 → contrib = 1.0
        # red: value=0.0, voter_weight=0.5, time_weight~=1.0 → contrib = 0.0
        # score = 1.0 / (1.0 + 0.5) * 100 = 66.67
        # But only 2 non-skip ratings → blended = (66.67 * 2 + 100 * 3) / 5 = 86.67
        ratings = [
            _make_rating_row("green", days_ago=0, rater_reliability=100.0),
            _make_rating_row("red", days_ago=0, rater_reliability=50.0),
        ]
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = ratings

        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        }

        score = rating_service.calculate_reliability_score("user-1")
        # Blended: (66.67 * 2 + 100 * 3) / 5 ≈ 86.67
        assert Decimal("86") <= score <= Decimal("87")


# =============================================================================
# TestGetReportingPower
# =============================================================================


class TestGetReportingPower:
    """Tests for get_reporting_power() — tier + history based multiplier."""

    @pytest.mark.unit
    def test_paid_user_weight_1_0(self, rating_service, mock_supabase) -> None:
        """Paid users always have 1.0 reporting power."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        # Credit tier lookup
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "tier": "pro",
        }
        # User data lookup
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "tier": "pro",
        }

        power = rating_service.get_reporting_power("paid-user")
        assert power == Decimal("1.0")

    @pytest.mark.unit
    def test_free_established_user_weight_0_5(self, rating_service, mock_supabase) -> None:
        """Free users with 5+ sessions and 7+ day old account = 0.5."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "tier": "free",
        }

        power = rating_service.get_reporting_power("free-established")
        assert power == Decimal("0.5")

    @pytest.mark.unit
    def test_free_new_account_weight_0(self, rating_service, mock_supabase) -> None:
        """Free users with account <7 days old = 0.0."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "tier": "free",
        }

        power = rating_service.get_reporting_power("free-new-account")
        assert power == Decimal("0.0")

    @pytest.mark.unit
    def test_free_low_sessions_weight_0(self, rating_service, mock_supabase) -> None:
        """Free users with <5 completed sessions = 0.0."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "session_count": 3,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
            "tier": "free",
        }

        power = rating_service.get_reporting_power("free-low-sessions")
        assert power == Decimal("0.0")


# =============================================================================
# TestCheckAndApplyPenalty
# =============================================================================


class TestCheckAndApplyPenalty:
    """Tests for check_and_apply_penalty() — dynamic threshold system."""

    @pytest.mark.unit
    def test_no_penalty_below_threshold(self, rating_service, mock_supabase) -> None:
        """No penalty when weighted reds are below threshold."""
        # 1 red from a paid user = 1.0 weighted → below free threshold of 1.5
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Ratings in last 7 days
        mock_table.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value.data = [
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
        ]

        # User's credit tier
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "tier": "free",
        }

        result = rating_service.check_and_apply_penalty("user-1")
        assert result is None

    @pytest.mark.unit
    def test_paid_user_threshold_3_reds(self, rating_service, mock_supabase) -> None:
        """Paid user needs 3.0 weighted reds to trigger penalty."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # 3 reds at weight 1.0 each = 3.0 → exactly at paid threshold
        mock_table.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value.data = [
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
        ]

        # Paid user
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "tier": "pro",
        }

        # Mock the ban application (update user + deduct credit)
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = rating_service.check_and_apply_penalty("paid-user")
        assert result is not None  # Returns banned_until datetime

    @pytest.mark.unit
    def test_free_user_threshold_1_5_weighted_reds(self, rating_service, mock_supabase) -> None:
        """Free user triggers at 1.5 weighted reds."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # 2 reds from paid users = 2.0 → above free threshold of 1.5
        mock_table.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value.data = [
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
            {"weight": 1.0, "created_at": datetime.now(timezone.utc).isoformat()},
        ]

        # Free user
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "tier": "free",
        }

        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = rating_service.check_and_apply_penalty("free-user")
        assert result is not None


# =============================================================================
# TestSubmitRatings
# =============================================================================


class TestSubmitRatings:
    """Tests for submit_ratings() — the full submission flow."""

    @pytest.mark.unit
    def test_red_reason_required(self, rating_service, mock_supabase) -> None:
        """Red rating without reasons raises error."""
        ratings = [
            SingleRating(ratee_id="user-2", rating=RatingValue.RED, reasons=None),
        ]

        with pytest.raises(RedReasonRequiredError):
            rating_service.submit_ratings("session-1", "user-1", ratings)

    @pytest.mark.unit
    def test_red_with_empty_reasons_raises(self, rating_service, mock_supabase) -> None:
        """Red rating with empty reasons list raises error."""
        ratings = [
            SingleRating(ratee_id="user-2", rating=RatingValue.RED, reasons=[]),
        ]

        with pytest.raises(RedReasonRequiredError):
            rating_service.submit_ratings("session-1", "user-1", ratings)

    @pytest.mark.unit
    def test_green_without_reasons_ok(self, rating_service, mock_supabase) -> None:
        """Green rating doesn't need reasons — validation passes."""
        ratings = [
            SingleRating(ratee_id="user-2", rating=RatingValue.GREEN),
        ]
        # Validation should not raise for Green with no reasons
        # (the _validate_ratings_input is the gate; test it directly)
        rating_service._validate_ratings_input(ratings)  # Should not raise

    @pytest.mark.unit
    def test_submit_ratings_full_flow(self, rating_service, mock_supabase) -> None:
        """Full submit flow with table-specific mocks."""
        ratings = [
            SingleRating(ratee_id="user-2", rating=RatingValue.GREEN),
        ]

        # Table-specific mocks to avoid chain collision
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        users_mock = MagicMock()
        credits_mock = MagicMock()
        ratings_mock = MagicMock()
        pending_mock = MagicMock()

        def table_router(name):
            return {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "users": users_mock,
                "credits": credits_mock,
                "ratings": ratings_mock,
                "pending_ratings": pending_mock,
            }.get(name, MagicMock())

        mock_supabase.table.side_effect = table_router

        # Session: social phase
        sessions_mock.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "id": "session-1",
            "current_phase": "social",
        }

        # Rater is participant
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"user_id": "user-1", "participant_type": "human"},
        ]
        # Ratee is human participant
        participants_mock.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
            {"user_id": "user-2", "participant_type": "human"},
        ]

        # Rater profile
        users_mock.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "reliability_score": 100.0,
            "session_count": 10,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        }

        # Credits tier for reporting power
        credits_mock.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "tier": "free",
        }

        # Insert rating
        ratings_mock.insert.return_value.execute.return_value.data = [{"id": "r-1"}]
        # Reliability recalc query (empty = default 100)
        ratings_mock.select.return_value.eq.return_value.gte.return_value.neq.return_value.execute.return_value.data = []
        # Penalty check (no reds in 7 days)
        ratings_mock.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value.data = []

        # Pending ratings update
        pending_mock.update.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        # Users update (reliability score)
        users_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = rating_service.submit_ratings("session-1", "user-1", ratings)
        assert result.success is True
        assert result.ratings_submitted == 1


# =============================================================================
# TestPendingRatings
# =============================================================================


class TestPendingRatings:
    """Tests for has_pending_ratings() and get_pending_ratings()."""

    @pytest.mark.unit
    def test_has_pending_returns_true(self, rating_service, mock_supabase) -> None:
        """Returns True when uncompleted, non-expired pending ratings exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value.data = [
            {"id": "pending-1"},
        ]

        assert rating_service.has_pending_ratings("user-1") is True

    @pytest.mark.unit
    def test_has_pending_returns_false_when_none(self, rating_service, mock_supabase) -> None:
        """Returns False when no pending ratings exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.limit.return_value.execute.return_value.data = []

        assert rating_service.has_pending_ratings("user-1") is False

    @pytest.mark.unit
    def test_get_pending_returns_info(self, rating_service, mock_supabase) -> None:
        """Returns PendingRatingInfo with rateable user details."""
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Pending rating record
        mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "pending-1",
                "session_id": "session-1",
                "rateable_user_ids": ["user-2", "user-3"],
                "expires_at": expires.isoformat(),
            },
        ]

        # User details for rateable users
        mock_table.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-2", "username": "alice", "display_name": "Alice", "avatar_config": {}},
            {"id": "user-3", "username": "bob", "display_name": "Bob", "avatar_config": {}},
        ]

        result = rating_service.get_pending_ratings("user-1")
        assert result is not None
        assert result.session_id == "session-1"
        assert len(result.rateable_users) == 2

    @pytest.mark.unit
    def test_get_pending_returns_none_when_empty(self, rating_service, mock_supabase) -> None:
        """Returns None when no pending ratings."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        result = rating_service.get_pending_ratings("user-1")
        assert result is None
