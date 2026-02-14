"""
Peer review / rating service.

Handles:
- Submitting batch ratings for session tablemates
- Reliability score calculation (weighted average with time decay)
- Reporting power multipliers (paid/free/new)
- Penalty system (dynamic thresholds, 48hr ban + credit loss)
- Pending ratings tracking (soft blocker for next session)

Design doc: output/plan/2026-02-08-peer-review-system.md
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from supabase import Client

from app.core.constants import (
    BAN_DURATION_HOURS,
    COMMUNITY_AGE_GATE_DAYS,
    COMMUNITY_AGE_GATE_SESSIONS,
    FREE_ESTABLISHED_RED_WEIGHT,
    FREE_NEW_RED_WEIGHT,
    FREE_USER_BAN_THRESHOLD,
    PAID_RED_WEIGHT,
    PAID_USER_BAN_THRESHOLD,
    PENALTY_CREDIT_DEDUCTION,
    RELIABILITY_HALF_LIFE_DAYS,
    RELIABILITY_HORIZON_DAYS,
    RELIABILITY_NEW_USER_THRESHOLD,
)
from app.core.database import get_supabase
from app.models.rating import (
    InvalidRatingTargetError,
    PendingRatingInfo,
    RateableUser,
    RatingAlreadyExistsError,
    RatingHistoryItem,
    RatingHistoryResponse,
    RatingHistorySummary,
    RatingSubmitResponse,
    RatingValue,
    RedReasonRequiredError,
    ReliabilityTier,
    SessionNotRatableError,
    SingleRating,
)

logger = logging.getLogger(__name__)


class RatingService:
    """Service for peer review ratings and reliability scoring."""

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Public API
    # =========================================================================

    def submit_ratings(
        self,
        session_id: str,
        rater_id: str,
        ratings: list[SingleRating],
    ) -> RatingSubmitResponse:
        """
        Submit batch ratings for all tablemates in a session.

        Validates session state, participant membership, and rating rules.
        After insertion, triggers reliability recalculation and penalty checks.
        """
        self._validate_ratings_input(ratings)

        session = self._get_session(session_id)
        if session["current_phase"] not in ("social", "ended"):
            raise SessionNotRatableError(
                f"Session {session_id} is in phase '{session['current_phase']}', not ratable"
            )

        self._verify_rater_is_participant(session_id, rater_id)

        ratee_ids = [r.ratee_id for r in ratings]
        self._verify_ratees_are_human_participants(session_id, ratee_ids)
        self._verify_not_self_rating(rater_id, ratee_ids)
        self._check_duplicate_ratings(session_id, rater_id)

        rater_profile = self._get_rater_profile(rater_id)
        reporting_power = self.get_reporting_power(rater_id)

        inserted_count = 0
        ratee_ids_to_recalc = []
        red_ratee_ids: set[str] = set()

        for single_rating in ratings:
            reason_json = None
            if single_rating.rating == RatingValue.RED and single_rating.reasons:
                reason_json = {
                    "reasons": [r.value for r in single_rating.reasons],
                }
                if single_rating.other_reason_text:
                    reason_json["other_text"] = single_rating.other_reason_text

            weight = reporting_power if single_rating.rating == RatingValue.RED else Decimal("1.0")

            row = {
                "session_id": session_id,
                "rater_id": rater_id,
                "ratee_id": single_rating.ratee_id,
                "rating": single_rating.rating.value,
                "rater_reliability_at_time": float(rater_profile.get("reliability_score", 100)),
                "weight": float(weight),
                "reason": reason_json,
            }

            self.supabase.table("ratings").insert(row).execute()
            inserted_count += 1

            if single_rating.rating != RatingValue.SKIP:
                ratee_ids_to_recalc.append(single_rating.ratee_id)
            if single_rating.rating == RatingValue.RED:
                red_ratee_ids.add(single_rating.ratee_id)

        self._mark_pending_completed(session_id, rater_id)

        for ratee_id in ratee_ids_to_recalc:
            new_score = self.calculate_reliability_score(ratee_id)
            self.supabase.table("users").update({"reliability_score": float(new_score)}).eq(
                "id", ratee_id
            ).execute()

            if ratee_id in red_ratee_ids:
                self.check_and_apply_penalty(ratee_id)

        return RatingSubmitResponse(
            success=True,
            ratings_submitted=inserted_count,
        )

    def skip_all_ratings(self, session_id: str, user_id: str) -> None:
        """Mark pending ratings as completed without submitting any."""
        self._mark_pending_completed(session_id, user_id)

    def calculate_reliability_score(self, user_id: str) -> Decimal:
        """
        Recalculate reliability score using weighted average with time decay.

        Algorithm:
          score = sum(value * combined_weight) / sum(combined_weight) * 100
          time_weight = 0.5 ^ (days_since / 30)
          voter_weight = rater_reliability / 100
          combined_weight = time_weight * voter_weight

        Adjustments:
        - 180-day horizon
        - New user blend with default 100 if <5 non-skip ratings
        - Community age gate: new raters' Red ratings carry zero weight
        """
        horizon_date = datetime.now(timezone.utc) - timedelta(days=RELIABILITY_HORIZON_DAYS)

        result = (
            self.supabase.table("ratings")
            .select("rating, rater_reliability_at_time, weight, created_at, rater_id")
            .eq("ratee_id", user_id)
            .gte("created_at", horizon_date.isoformat())
            .neq("rating", "skip")
            .execute()
        )

        ratings = result.data
        if not ratings:
            return Decimal("100.00")

        now = datetime.now(timezone.utc)
        total_weighted_value = Decimal("0")
        total_weight = Decimal("0")
        non_skip_count = 0

        for r in ratings:
            non_skip_count += 1
            value = Decimal("1.0") if r["rating"] == "green" else Decimal("0.0")

            created_at = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            days_since = max((now - created_at).total_seconds() / 86400, 0)
            time_weight = Decimal(str(math.pow(0.5, days_since / RELIABILITY_HALF_LIFE_DAYS)))

            rater_reliability = Decimal(str(r.get("rater_reliability_at_time") or 100))
            voter_weight = rater_reliability / Decimal("100")

            combined_weight = time_weight * voter_weight
            total_weighted_value += value * combined_weight
            total_weight += combined_weight

        if total_weight == 0:
            return Decimal("100.00")

        raw_score = (total_weighted_value / total_weight) * Decimal("100")

        if non_skip_count < RELIABILITY_NEW_USER_THRESHOLD:
            phantom_count = RELIABILITY_NEW_USER_THRESHOLD - non_skip_count
            blended = (
                raw_score * Decimal(str(non_skip_count))
                + Decimal("100") * Decimal(str(phantom_count))
            ) / Decimal(str(RELIABILITY_NEW_USER_THRESHOLD))
            raw_score = blended

        return raw_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_reporting_power(self, rater_id: str) -> Decimal:
        """
        Calculate reporting power multiplier for a rater.

        Returns:
        - 1.0 for paid users (pro/elite/infinite/admin)
        - 0.5 for free users with 5+ sessions and 7+ day account
        - 0.0 for free users <5 sessions or <7 day account
        """
        data = (
            self.supabase.table("users")
            .select("session_count, created_at")
            .eq("id", rater_id)
            .single()
            .execute()
        ).data

        tier = self._get_user_tier(rater_id)

        if tier in ("pro", "elite", "infinite", "admin"):
            return Decimal(str(PAID_RED_WEIGHT))

        session_count = data.get("session_count", 0) if data else 0
        created_at_str = data.get("created_at", "") if data else ""

        if created_at_str:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            account_age_days = (datetime.now(timezone.utc) - created_at).days
        else:
            account_age_days = 0

        if (
            session_count >= COMMUNITY_AGE_GATE_SESSIONS
            and account_age_days >= COMMUNITY_AGE_GATE_DAYS
        ):
            return Decimal(str(FREE_ESTABLISHED_RED_WEIGHT))

        return Decimal(str(FREE_NEW_RED_WEIGHT))

    def check_and_apply_penalty(self, user_id: str) -> Optional[datetime]:
        """
        Check if user has accumulated enough weighted reds for a ban.

        Dynamic thresholds:
        - Paid users: 3.0 weighted reds in rolling 7 days
        - Free users: 1.5 weighted reds in rolling 7 days

        Returns banned_until datetime if penalty applied, None otherwise.
        """
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        result = (
            self.supabase.table("ratings")
            .select("weight, created_at")
            .eq("ratee_id", user_id)
            .gte("created_at", seven_days_ago.isoformat())
            .eq("rating", "red")
            .execute()
        )

        weighted_total = sum(Decimal(str(r["weight"])) for r in result.data)

        tier = self._get_user_tier(user_id)
        threshold = (
            Decimal(str(PAID_USER_BAN_THRESHOLD))
            if tier in ("pro", "elite", "infinite", "admin")
            else Decimal(str(FREE_USER_BAN_THRESHOLD))
        )

        if weighted_total >= threshold:
            banned_until = datetime.now(timezone.utc) + timedelta(hours=BAN_DURATION_HOURS)

            self.supabase.table("users").update({"banned_until": banned_until.isoformat()}).eq(
                "id", user_id
            ).execute()

            try:
                from app.services.credit_service import CreditService

                credit_service = CreditService(supabase=self.supabase)
                credit_service.deduct_credit(user_id, PENALTY_CREDIT_DEDUCTION)
            except Exception:
                logger.warning(
                    "Failed to deduct penalty credit for user %s", user_id, exc_info=True
                )

            return banned_until

        return None

    def has_pending_ratings(self, user_id: str) -> bool:
        """Quick check for the session-join soft blocker."""
        now = datetime.now(timezone.utc)
        result = (
            self.supabase.table("pending_ratings")
            .select("id")
            .eq("user_id", user_id)
            .is_("completed_at", "null")
            .gt("expires_at", now.isoformat())
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    def get_pending_ratings(self, user_id: str) -> Optional[PendingRatingInfo]:
        """Get the user's oldest uncompleted, non-expired pending rating."""
        now = datetime.now(timezone.utc)
        result = (
            self.supabase.table("pending_ratings")
            .select("id, session_id, rateable_user_ids, expires_at")
            .eq("user_id", user_id)
            .is_("completed_at", "null")
            .gt("expires_at", now.isoformat())
            .order("created_at")
            .limit(1)
            .execute()
        )

        if not result.data:
            return None

        pending = result.data[0]
        rateable_user_ids = pending["rateable_user_ids"]

        users_result = (
            self.supabase.table("users")
            .select("id, username, display_name, avatar_config")
            .in_("id", rateable_user_ids)
            .execute()
        )

        rateable_users = [
            RateableUser(
                user_id=u["id"],
                username=u["username"],
                display_name=u.get("display_name"),
                avatar_config=u.get("avatar_config", {}),
            )
            for u in users_result.data
        ]

        return PendingRatingInfo(
            session_id=pending["session_id"],
            rateable_users=rateable_users,
            expires_at=datetime.fromisoformat(pending["expires_at"].replace("Z", "+00:00")),
        )

    def get_reliability_tier(self, score: Decimal, total_ratings: int) -> ReliabilityTier:
        """Map score + rating count to display tier."""
        if total_ratings < RELIABILITY_NEW_USER_THRESHOLD:
            return ReliabilityTier.NEW
        if score >= Decimal("95"):
            return ReliabilityTier.TRUSTED
        if score >= Decimal("80"):
            return ReliabilityTier.GOOD
        return ReliabilityTier.FAIR

    def get_rating_history(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> RatingHistoryResponse:
        """Get paginated history of ratings received by this user.

        Returns privacy-safe items (no rater identity) plus aggregate summary.
        """
        offset = (page - 1) * per_page

        # Aggregate counts via SQL — O(1) memory regardless of total ratings
        green_result = (
            self.supabase.table("ratings")
            .select("id", count="exact")
            .eq("ratee_id", user_id)
            .eq("rating", "green")
            .execute()
        )
        red_result = (
            self.supabase.table("ratings")
            .select("id", count="exact")
            .eq("ratee_id", user_id)
            .eq("rating", "red")
            .execute()
        )

        green_count = green_result.count or 0
        red_count = red_result.count or 0
        total_received = green_count + red_count
        green_percentage = (
            round((green_count / total_received) * 100, 1) if total_received > 0 else 0.0
        )

        # Paginated items (most recent first)
        items_result = (
            self.supabase.table("ratings")
            .select("id, session_id, rating, created_at")
            .eq("ratee_id", user_id)
            .neq("rating", "skip")
            .order("created_at", desc=True)
            .range(offset, offset + per_page - 1)
            .execute()
        )

        items = [
            RatingHistoryItem(
                id=r["id"],
                session_id=r["session_id"],
                rating=r["rating"],
                created_at=r["created_at"],
            )
            for r in items_result.data
        ]

        summary = RatingHistorySummary(
            total_received=total_received,
            green_count=green_count,
            red_count=red_count,
            green_percentage=green_percentage,
        )

        return RatingHistoryResponse(
            summary=summary,
            items=items,
            total=total_received,
            page=page,
            per_page=per_page,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _validate_ratings_input(self, ratings: list[SingleRating]) -> None:
        """Validate that red ratings have reasons."""
        for r in ratings:
            if r.rating == RatingValue.RED:
                if not r.reasons:
                    raise RedReasonRequiredError("Red ratings require at least one reason")

    def _get_session(self, session_id: str) -> dict:
        """Fetch session record."""
        result = (
            self.supabase.table("sessions")
            .select("id, current_phase")
            .eq("id", session_id)
            .single()
            .execute()
        )
        return result.data

    def _verify_rater_is_participant(self, session_id: str, rater_id: str) -> None:
        """Verify the rater was a participant in this session."""
        result = (
            self.supabase.table("session_participants")
            .select("user_id, participant_type")
            .eq("session_id", session_id)
            .eq("user_id", rater_id)
            .execute()
        )
        if not result.data:
            raise InvalidRatingTargetError(f"User {rater_id} was not in session {session_id}")

    def _verify_ratees_are_human_participants(self, session_id: str, ratee_ids: list) -> None:
        """Verify all ratees are human participants in the session."""
        result = (
            self.supabase.table("session_participants")
            .select("user_id, participant_type")
            .eq("session_id", session_id)
            .in_("user_id", ratee_ids)
            .execute()
        )
        found = {r["user_id"] for r in result.data}
        for ratee_id in ratee_ids:
            if ratee_id not in found:
                raise InvalidRatingTargetError(
                    f"User {ratee_id} is not a human participant in session {session_id}"
                )

        for r in result.data:
            if r["participant_type"] != "human":
                raise InvalidRatingTargetError(
                    f"User {r['user_id']} is an AI companion, not ratable"
                )

    def _get_rater_profile(self, rater_id: str) -> dict:
        """Get rater's profile for reliability snapshot."""
        result = (
            self.supabase.table("users")
            .select("reliability_score, session_count, created_at")
            .eq("id", rater_id)
            .single()
            .execute()
        )
        return result.data

    def _mark_pending_completed(self, session_id: str, user_id: str) -> None:
        """Mark pending rating as completed."""
        now = datetime.now(timezone.utc)
        self.supabase.table("pending_ratings").update({"completed_at": now.isoformat()}).eq(
            "session_id", session_id
        ).eq("user_id", user_id).execute()

    def _get_user_tier(self, user_id: str) -> str:
        """Look up a user's credit tier."""
        credit_data = (
            self.supabase.table("credits").select("tier").eq("user_id", user_id).single().execute()
        ).data
        return credit_data.get("tier", "free") if credit_data else "free"

    def _verify_not_self_rating(self, rater_id: str, ratee_ids: list[str]) -> None:
        """Prevent users from rating themselves."""
        if rater_id in ratee_ids:
            raise InvalidRatingTargetError("Cannot rate yourself")

    def _check_duplicate_ratings(self, session_id: str, rater_id: str) -> None:
        """Check if rater already submitted ratings for this session."""
        result = (
            self.supabase.table("ratings")
            .select("id")
            .eq("session_id", session_id)
            .eq("rater_id", rater_id)
            .limit(1)
            .execute()
        )
        if result.data:
            raise RatingAlreadyExistsError(
                f"User {rater_id} already rated participants in session {session_id}"
            )
