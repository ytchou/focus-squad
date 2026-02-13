"""
Accountability partner service.

Handles:
- Sending and responding to partnership requests
- Listing partners and pending requests
- Removing partners (with recurring schedule cascade)
- User search with partnership status
- Interest tag management
- Tracking last session together

Design doc: output/plan/2026-02-12-accountability-partners-design.md
"""

import asyncio
import logging
from datetime import datetime, timezone
from itertools import combinations
from typing import Optional

from supabase import Client

from app.core.constants import (
    INTEREST_TAGS,
    MAX_INTEREST_TAGS_PER_USER,
    MAX_PARTNERS,
    PARTNER_SEARCH_LIMIT,
)
from app.core.database import get_supabase
from app.core.redis import get_redis
from app.models.partner import (
    AlreadyPartnersError,
    InvalidInterestTagError,
    PartnerLimitError,
    PartnerRequestExistsError,
    PartnershipNotFoundError,
    SelfPartnerError,
)

logger = logging.getLogger(__name__)

PARTNER_CACHE_TTL = 300  # 5 minutes
PARTNER_CACHE_LOCK_TTL = 5  # Lock expires after 5 seconds to prevent deadlocks


class PartnerService:
    """Service for accountability partner management."""

    def __init__(self, supabase: Optional[Client] = None, redis: Optional[object] = None) -> None:
        self._supabase = supabase
        self._redis = redis

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis()
        return self._redis

    # =========================================================================
    # Public API
    # =========================================================================

    async def get_accepted_partner_ids(self, user_id: str) -> set[str]:
        """
        Get accepted partner IDs with Redis cache.

        Uses Redis SET for O(1) membership checks.
        TTL of 5 minutes handles missed invalidations.
        Uses lock to prevent cache stampede on concurrent misses.
        """
        cache_key = f"partners:{user_id}:accepted"
        lock_key = f"partners:{user_id}:lock"

        # Try cache first
        cached = await self.redis.smembers(cache_key)
        if cached:
            return cached

        # Cache miss - try to acquire lock to prevent stampede
        # SETNX returns True if lock acquired, False if another request has it
        acquired = await self.redis.set(lock_key, "1", nx=True, ex=PARTNER_CACHE_LOCK_TTL)

        if not acquired:
            # Another request is populating the cache - wait briefly and retry cache
            await asyncio.sleep(0.1)
            cached = await self.redis.smembers(cache_key)
            if cached:
                return cached
            # Still no cache after wait - proceed anyway (lock may have expired)

        try:
            # Query DB
            result = (
                self.supabase.table("partnerships")
                .select("requester_id, addressee_id")
                .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}")
                .eq("status", "accepted")
                .execute()
            )

            partner_ids: set[str] = set()
            for row in result.data or []:
                other_id = (
                    row["addressee_id"] if row["requester_id"] == user_id else row["requester_id"]
                )
                partner_ids.add(other_id)

            # Cache result (only if non-empty)
            if partner_ids:
                await self.redis.sadd(cache_key, *partner_ids)
                await self.redis.expire(cache_key, PARTNER_CACHE_TTL)

            return partner_ids
        finally:
            # Release lock
            await self.redis.delete(lock_key)

    async def _invalidate_partner_cache(self, user_id: str) -> None:
        """Invalidate partner cache for a user."""
        await self.redis.delete(f"partners:{user_id}:accepted")

    def _invalidate_partner_cache_sync(self, user_id: str) -> None:
        """
        Sync wrapper for cache invalidation.

        Schedules async invalidation as a background task if in an event loop,
        otherwise silently skips (cache will expire via TTL).
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._invalidate_partner_cache(user_id))
        except RuntimeError:
            # No event loop running - cache will expire via TTL
            pass

    def send_request(self, requester_id: str, addressee_id: str) -> dict:
        """
        Send a partnership request to another user.

        Validates:
        - Not sending to self
        - No existing partnership or pending request in either direction
        - Requester hasn't hit MAX_PARTNERS accepted partners

        Returns:
            The created partnership record dict.

        Raises:
            SelfPartnerError: Cannot partner with yourself
            AlreadyPartnersError: Already accepted partners
            PartnerRequestExistsError: Pending request already exists
            PartnerLimitError: Requester at max partner count
        """
        if requester_id == addressee_id:
            raise SelfPartnerError("Cannot send a partner request to yourself")

        existing = self._find_partnership(requester_id, addressee_id)
        if existing:
            if existing["status"] == "accepted":
                raise AlreadyPartnersError("You are already partners with this user")
            if existing["status"] == "pending":
                raise PartnerRequestExistsError(
                    "A partner request already exists between you and this user"
                )

        accepted_count = self._count_accepted_partners(requester_id)
        if accepted_count >= MAX_PARTNERS:
            raise PartnerLimitError(f"You have reached the maximum of {MAX_PARTNERS} partners")

        result = (
            self.supabase.table("partnerships")
            .insert(
                {
                    "requester_id": requester_id,
                    "addressee_id": addressee_id,
                    "status": "pending",
                }
            )
            .execute()
        )

        # Invalidate cache for both users
        self._invalidate_partner_cache_sync(requester_id)
        self._invalidate_partner_cache_sync(addressee_id)

        return result.data[0]

    def respond_to_request(self, partnership_id: str, user_id: str, accept: bool) -> dict:
        """
        Accept or decline a pending partnership request.

        Only the addressee can respond.

        Returns:
            The updated partnership record dict.

        Raises:
            PartnershipNotFoundError: Partnership doesn't exist or isn't pending
        """
        partnership = self._get_partnership(partnership_id)

        if partnership["status"] != "pending":
            raise PartnershipNotFoundError(f"Partnership {partnership_id} is not pending")

        if partnership["addressee_id"] != user_id:
            raise PartnershipNotFoundError("Only the addressee can respond to this request")

        if accept:
            update_data = {
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            update_data = {"status": "declined"}

        result = (
            self.supabase.table("partnerships")
            .update(update_data)
            .eq("id", partnership_id)
            .execute()
        )

        # Invalidate cache for both users
        requester_id = partnership["requester_id"]
        addressee_id = partnership["addressee_id"]
        self._invalidate_partner_cache_sync(requester_id)
        self._invalidate_partner_cache_sync(addressee_id)

        return result.data[0]

    def list_partners(self, user_id: str) -> list[dict]:
        """
        List all accepted partners for a user with profile info.

        Returns a list of dicts, each containing partnership_id and partner profile
        fields: user_id, username, display_name, avatar_config, pixel_avatar_id,
        reliability_score, study_interests, last_session_together.
        """
        result = (
            self.supabase.table("partnerships")
            .select("id, requester_id, addressee_id, last_session_together")
            .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}")
            .eq("status", "accepted")
            .execute()
        )

        if not result.data:
            return []

        partner_ids = []
        partnership_map: dict[str, dict] = {}
        for row in result.data:
            partner_id = (
                row["addressee_id"] if row["requester_id"] == user_id else row["requester_id"]
            )
            partner_ids.append(partner_id)
            partnership_map[partner_id] = row

        users_result = (
            self.supabase.table("users")
            .select(
                "id, username, display_name, avatar_config, "
                "pixel_avatar_id, reliability_score, study_interests"
            )
            .in_("id", partner_ids)
            .execute()
        )

        partners = []
        for user in users_result.data:
            pship = partnership_map[user["id"]]
            partners.append(
                {
                    "partnership_id": pship["id"],
                    "user_id": user["id"],
                    "username": user["username"],
                    "display_name": user.get("display_name"),
                    "avatar_config": user.get("avatar_config") or {},
                    "pixel_avatar_id": user.get("pixel_avatar_id"),
                    "reliability_score": user.get("reliability_score", 100),
                    "study_interests": user.get("study_interests") or [],
                    "last_session_together": pship.get("last_session_together"),
                }
            )

        return partners

    def list_requests(self, user_id: str) -> list[dict]:
        """
        List all pending partnership requests involving this user.

        Each result includes a 'direction' field: "incoming" or "outgoing".
        """
        result = (
            self.supabase.table("partnerships")
            .select("id, requester_id, addressee_id, created_at")
            .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}")
            .eq("status", "pending")
            .execute()
        )

        if not result.data:
            return []

        incoming_ids = []
        outgoing_ids = []
        request_map: dict[str, dict] = {}

        for row in result.data:
            if row["addressee_id"] == user_id:
                other_id = row["requester_id"]
                incoming_ids.append(other_id)
                request_map[other_id] = {**row, "direction": "incoming"}
            else:
                other_id = row["addressee_id"]
                outgoing_ids.append(other_id)
                request_map[other_id] = {**row, "direction": "outgoing"}

        all_user_ids = incoming_ids + outgoing_ids
        if not all_user_ids:
            return []

        users_result = (
            self.supabase.table("users")
            .select("id, username, display_name, avatar_config, pixel_avatar_id")
            .in_("id", all_user_ids)
            .execute()
        )

        requests = []
        for user in users_result.data:
            req = request_map[user["id"]]
            requests.append(
                {
                    "partnership_id": req["id"],
                    "user_id": user["id"],
                    "username": user["username"],
                    "display_name": user.get("display_name"),
                    "avatar_config": user.get("avatar_config") or {},
                    "pixel_avatar_id": user.get("pixel_avatar_id"),
                    "direction": req["direction"],
                    "created_at": req["created_at"],
                }
            )

        return requests

    def remove_partner(self, partnership_id: str, user_id: str) -> None:
        """
        Remove a partner and cascade-clean recurring schedules.

        If removing a partner from a recurring schedule leaves it with no
        partners, the schedule is deactivated.

        Raises:
            PartnershipNotFoundError: Partnership not found or user not in it
        """
        partnership = self._get_partnership(partnership_id)

        if partnership["requester_id"] != user_id and partnership["addressee_id"] != user_id:
            raise PartnershipNotFoundError("You are not part of this partnership")

        partner_id = (
            partnership["addressee_id"]
            if partnership["requester_id"] == user_id
            else partnership["requester_id"]
        )

        self.supabase.table("partnerships").delete().eq("id", partnership_id).execute()

        # Invalidate cache for both users
        self._invalidate_partner_cache_sync(user_id)
        self._invalidate_partner_cache_sync(partner_id)

        self._cascade_remove_from_schedules(user_id, partner_id)
        self._cascade_remove_from_group_conversations(user_id, partner_id)

    def search_users(self, query: str, current_user_id: str) -> list[dict]:
        """
        Search users by username or display_name.

        Results include partnership_status field indicating current relationship.
        Excludes the searching user from results.
        """
        search_pattern = f"%{query}%"

        result = (
            self.supabase.table("users")
            .select("id, username, display_name, avatar_config, pixel_avatar_id, study_interests")
            .or_(f"username.ilike.{search_pattern},display_name.ilike.{search_pattern}")
            .neq("id", current_user_id)
            .limit(PARTNER_SEARCH_LIMIT)
            .execute()
        )

        if not result.data:
            return []

        user_ids = [u["id"] for u in result.data]
        status_map = self._get_partnership_statuses(current_user_id, user_ids)

        users = []
        for user in result.data:
            users.append(
                {
                    "user_id": user["id"],
                    "username": user["username"],
                    "display_name": user.get("display_name"),
                    "avatar_config": user.get("avatar_config") or {},
                    "pixel_avatar_id": user.get("pixel_avatar_id"),
                    "study_interests": user.get("study_interests") or [],
                    "partnership_status": status_map.get(user["id"]),
                }
            )

        return users

    def update_last_session_together(self, user_ids: list[str]) -> None:
        """
        Update last_session_together for all partner pairs in a session.

        Called after a session ends. For each pair combination of user_ids,
        checks if they share a partnership and updates the timestamp.
        """
        if len(user_ids) < 2:
            return

        now = datetime.now(timezone.utc).isoformat()

        for user_a, user_b in combinations(user_ids, 2):
            partnership = self._find_partnership(user_a, user_b)
            if partnership and partnership["status"] == "accepted":
                self.supabase.table("partnerships").update({"last_session_together": now}).eq(
                    "id", partnership["id"]
                ).execute()

    def get_interest_tags(self, user_id: str) -> list[str]:
        """Get the user's study interest tags."""
        result = (
            self.supabase.table("users")
            .select("study_interests")
            .eq("id", user_id)
            .single()
            .execute()
        )

        return result.data.get("study_interests") or []

    def set_interest_tags(self, user_id: str, tags: list[str]) -> list[str]:
        """
        Set the user's study interest tags.

        Validates all tags are from the INTEREST_TAGS constant and
        total count doesn't exceed MAX_INTEREST_TAGS_PER_USER.

        Raises:
            InvalidInterestTagError: Invalid tag or too many tags
        """
        invalid = [t for t in tags if t not in INTEREST_TAGS]
        if invalid:
            raise InvalidInterestTagError(
                f"Invalid interest tags: {invalid}. Valid tags: {INTEREST_TAGS}"
            )

        if len(tags) > MAX_INTEREST_TAGS_PER_USER:
            raise InvalidInterestTagError(
                f"Maximum {MAX_INTEREST_TAGS_PER_USER} interest tags allowed, got {len(tags)}"
            )

        self.supabase.table("users").update({"study_interests": tags}).eq("id", user_id).execute()

        return tags

    def get_partnership_status(self, user_a_id: str, user_b_id: str) -> Optional[str]:
        """
        Check if a partnership exists between two users.

        Returns:
            Status string ('pending', 'accepted') or None if no partnership.
        """
        partnership = self._find_partnership(user_a_id, user_b_id)
        if not partnership:
            return None
        if partnership["status"] in ("pending", "accepted"):
            return partnership["status"]
        return None

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _get_partnership(self, partnership_id: str) -> dict:
        """Fetch a partnership by ID. Raises if not found."""
        result = self.supabase.table("partnerships").select("*").eq("id", partnership_id).execute()

        if not result.data:
            raise PartnershipNotFoundError(f"Partnership {partnership_id} not found")

        return result.data[0]

    def _find_partnership(self, user_a_id: str, user_b_id: str) -> Optional[dict]:
        """
        Find an existing partnership between two users in either direction.

        Only returns pending or accepted partnerships (ignores declined).
        """
        result = (
            self.supabase.table("partnerships")
            .select("id, requester_id, addressee_id, status")
            .or_(
                f"and(requester_id.eq.{user_a_id},addressee_id.eq.{user_b_id}),"
                f"and(requester_id.eq.{user_b_id},addressee_id.eq.{user_a_id})"
            )
            .in_("status", ["pending", "accepted"])
            .execute()
        )

        if not result.data:
            return None

        return result.data[0]

    def _count_accepted_partners(self, user_id: str) -> int:
        """Count the number of accepted partnerships for a user."""
        result = (
            self.supabase.table("partnerships")
            .select("id", count="exact")
            .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}")
            .eq("status", "accepted")
            .execute()
        )

        return result.count or 0

    def _get_partnership_statuses(
        self, current_user_id: str, other_user_ids: list[str]
    ) -> dict[str, Optional[str]]:
        """
        Batch lookup partnership statuses between current user and a list of others.

        Returns a dict mapping user_id -> status ('pending'/'accepted') or absent if none.
        """
        if not other_user_ids:
            return {}

        result = (
            self.supabase.table("partnerships")
            .select("requester_id, addressee_id, status")
            .or_(f"requester_id.eq.{current_user_id},addressee_id.eq.{current_user_id}")
            .in_("status", ["pending", "accepted"])
            .execute()
        )

        status_map: dict[str, Optional[str]] = {}
        for row in result.data:
            other_id = (
                row["addressee_id"]
                if row["requester_id"] == current_user_id
                else row["requester_id"]
            )
            if other_id in other_user_ids:
                status_map[other_id] = row["status"]

        return status_map

    def _cascade_remove_from_schedules(self, user_id: str, partner_id: str) -> None:
        """
        Remove a partner from any recurring schedules created by user_id,
        and vice versa. If a schedule has no partners left, deactivate it.

        Uses a fetch-modify-update pattern since supabase-py doesn't expose
        Postgres array_remove directly.
        """
        for creator_id, removed_id in [
            (user_id, partner_id),
            (partner_id, user_id),
        ]:
            result = (
                self.supabase.table("recurring_schedules")
                .select("id, partner_ids")
                .eq("creator_id", creator_id)
                .eq("is_active", True)
                .execute()
            )

            for schedule in result.data:
                current_partners = schedule.get("partner_ids") or []
                if removed_id not in current_partners:
                    continue

                new_partners = [pid for pid in current_partners if pid != removed_id]

                if not new_partners:
                    self.supabase.table("recurring_schedules").update(
                        {"partner_ids": [], "is_active": False}
                    ).eq("id", schedule["id"]).execute()
                    logger.info(
                        "Deactivated recurring schedule %s (no partners left)",
                        schedule["id"],
                    )
                else:
                    self.supabase.table("recurring_schedules").update(
                        {"partner_ids": new_partners}
                    ).eq("id", schedule["id"]).execute()
                    logger.info(
                        "Removed partner %s from recurring schedule %s",
                        removed_id,
                        schedule["id"],
                    )

    def _cascade_remove_from_group_conversations(self, user_id: str, partner_id: str) -> None:
        """
        Remove users from group conversations where they have no remaining
        mutual partners after an un-partnering event.

        Checks BOTH directions symmetrically: user_id may need removal from
        groups where they only had partner_id as a mutual partner, and vice versa.
        """
        user_convs = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", user_id)
            .execute()
        )
        partner_convs = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", partner_id)
            .execute()
        )

        user_conv_ids = {m["conversation_id"] for m in user_convs.data}
        partner_conv_ids = {m["conversation_id"] for m in partner_convs.data}
        shared_conv_ids = user_conv_ids & partner_conv_ids

        if not shared_conv_ids:
            return

        groups = (
            self.supabase.table("conversations")
            .select("id")
            .in_("id", list(shared_conv_ids))
            .eq("type", "group")
            .execute()
        )

        for group in groups.data:
            members = (
                self.supabase.table("conversation_members")
                .select("user_id")
                .eq("conversation_id", group["id"])
                .execute()
            )
            member_ids = [m["user_id"] for m in members.data]

            # Check both users symmetrically
            for check_user in [user_id, partner_id]:
                if check_user not in member_ids:
                    continue
                others = [mid for mid in member_ids if mid != check_user]

                has_remaining_partner = False
                for other_id in others:
                    partnership = self._find_partnership(check_user, other_id)
                    if partnership and partnership["status"] == "accepted":
                        has_remaining_partner = True
                        break

                if not has_remaining_partner:
                    self.supabase.table("conversation_members").delete().eq(
                        "conversation_id", group["id"]
                    ).eq("user_id", check_user).execute()
                    member_ids.remove(check_user)
                    logger.info(
                        "Removed %s from group %s (no remaining mutual partners)",
                        check_user,
                        group["id"],
                    )
