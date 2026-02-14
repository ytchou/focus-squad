"""
Essence service for item shop and purchase operations.

Handles:
- Essence balance queries
- Shop catalog browsing with filters
- Item purchases with balance deduction
- User inventory retrieval
"""

import logging
from typing import Optional

from supabase import Client

from app.core.database import get_supabase
from app.models.partner import NotPartnerError
from app.models.room import (
    EssenceBalance,
    EssenceServiceError,
    GiftPurchaseResponse,
    InsufficientEssenceError,
    InventoryItem,
    ItemNotFoundError,
    PurchaseResponse,
    SelfGiftError,
    ShopItem,
)

logger = logging.getLogger(__name__)

TIER_ORDER = {"basic": 0, "standard": 1, "premium": 2}


class EssenceService:
    """Service for essence balance, item shop, and inventory operations."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def get_balance(self, user_id: str) -> EssenceBalance:
        result = (
            self.supabase.table("furniture_essence")
            .select("balance, total_earned, total_spent")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            return EssenceBalance(balance=0, total_earned=0, total_spent=0)

        return EssenceBalance(**result.data[0])

    def get_shop_items(
        self,
        category: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> list[ShopItem]:
        query = (
            self.supabase.table("items")
            .select("*")
            .eq("is_available", True)
            .eq("is_purchasable", True)
        )

        if category:
            query = query.eq("category", category)
        if tier:
            query = query.eq("tier", tier)

        query = query.order("essence_cost", desc=False)
        result = query.execute()

        if not result.data:
            return []

        items = [ShopItem(**row) for row in result.data]
        items.sort(key=lambda item: (TIER_ORDER.get(item.tier, 99), item.essence_cost))

        return items

    def buy_item(self, user_id: str, item_id: str) -> PurchaseResponse:
        """
        Purchase an item using atomic RPC.

        The purchase_item_atomic RPC handles:
        - Item lookup and availability check
        - Balance check with row lock (FOR UPDATE)
        - Essence deduction
        - Inventory insertion
        - Transaction logging

        All in a single atomic transaction - if any step fails, nothing is committed.

        Returns enriched PurchaseResponse with updated balance and inventory count,
        eliminating the need for extra round-trips from the frontend.
        """
        result = self.supabase.rpc(
            "purchase_item_atomic",
            {
                "p_user_id": user_id,
                "p_item_id": item_id,
                "p_is_gift": False,
                "p_recipient_id": None,
                "p_gift_message": None,
            },
        ).execute()

        if not result.data:
            raise EssenceServiceError("Purchase failed: no response from database")

        data = result.data
        if not data.get("success"):
            error = data.get("error", "unknown_error")
            if error == "item_not_found":
                raise ItemNotFoundError(f"Item {item_id} not found or unavailable")
            elif error == "insufficient_essence":
                raise InsufficientEssenceError("Insufficient essence for this purchase")
            elif error == "no_essence_record":
                raise InsufficientEssenceError("No essence balance found")
            else:
                raise EssenceServiceError(f"Purchase failed: {error}")

        # Fetch item details for response (RPC returns minimal data)
        item_result = self.supabase.table("items").select("*").eq("id", item_id).execute()
        item_data = item_result.data[0] if item_result.data else {}

        inventory_item = InventoryItem(
            id=data["inventory_id"],
            item_id=item_id,
            item=ShopItem(**item_data) if item_data else None,
            acquired_at=None,  # Will be set by DB default
            acquisition_type="purchased",
        )

        # Fetch updated balance and inventory count to eliminate extra round-trips
        balance = self.get_balance(user_id)
        inventory_count_result = (
            self.supabase.table("user_items")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        inventory_count = inventory_count_result.count if inventory_count_result.count else 0

        return PurchaseResponse(
            item=inventory_item,
            balance=balance,
            inventory_count=inventory_count,
        )

    def gift_item(
        self,
        sender_id: str,
        recipient_id: str,
        item_id: str,
        gift_message: Optional[str] = None,
    ) -> GiftPurchaseResponse:
        """
        Gift an item to a partner using atomic RPC.

        Validates partnership first, then uses purchase_item_atomic RPC for
        atomic essence deduction and inventory insertion.
        """
        if sender_id == recipient_id:
            raise SelfGiftError("Cannot gift an item to yourself.")

        # Verify accepted partnership (must check before RPC)
        partnership_result = (
            self.supabase.table("partnerships")
            .select("id")
            .eq("status", "accepted")
            .or_(
                f"and(requester_id.eq.{sender_id},addressee_id.eq.{recipient_id}),"
                f"and(requester_id.eq.{recipient_id},addressee_id.eq.{sender_id})"
            )
            .limit(1)
            .execute()
        )
        if not partnership_result.data:
            raise NotPartnerError("You must be partners to gift items.")

        # Look up recipient name for response
        recipient_result = (
            self.supabase.table("users")
            .select("display_name, username")
            .eq("id", recipient_id)
            .execute()
        )
        recipient_data = recipient_result.data[0] if recipient_result.data else {}
        recipient_name = recipient_data.get("display_name") or recipient_data.get(
            "username", "Unknown"
        )

        # Atomic purchase via RPC
        result = self.supabase.rpc(
            "purchase_item_atomic",
            {
                "p_user_id": sender_id,
                "p_item_id": item_id,
                "p_is_gift": True,
                "p_recipient_id": recipient_id,
                "p_gift_message": gift_message,
            },
        ).execute()

        if not result.data:
            raise EssenceServiceError("Gift purchase failed: no response from database")

        data = result.data
        if not data.get("success"):
            error = data.get("error", "unknown_error")
            if error == "item_not_found":
                raise ItemNotFoundError(f"Item {item_id} not found or unavailable")
            elif error == "insufficient_essence":
                raise InsufficientEssenceError("Insufficient essence to gift this item")
            elif error == "no_essence_record":
                raise InsufficientEssenceError("No essence balance found")
            else:
                raise EssenceServiceError(f"Gift purchase failed: {error}")

        # Fetch updated balance to eliminate extra round-trip
        balance = self.get_balance(sender_id)

        return GiftPurchaseResponse(
            inventory_item_id=data["inventory_id"],
            item_name=data.get("item_name", "Item"),
            recipient_name=recipient_name,
            essence_spent=data.get("cost", 0),
            balance=balance,
        )

    def get_inventory(self, user_id: str) -> list[InventoryItem]:
        user_items_result = (
            self.supabase.table("user_items")
            .select("*")
            .eq("user_id", user_id)
            .order("acquired_at", desc=True)
            .execute()
        )

        if not user_items_result.data:
            return []

        item_ids = list({row["item_id"] for row in user_items_result.data})

        items_result = self.supabase.table("items").select("*").in_("id", item_ids).execute()

        items_map: dict[str, ShopItem] = {}
        if items_result.data:
            for row in items_result.data:
                items_map[row["id"]] = ShopItem(**row)

        inventory: list[InventoryItem] = []
        for row in user_items_result.data:
            inventory.append(
                InventoryItem(
                    id=row["id"],
                    item_id=row["item_id"],
                    item=items_map.get(row["item_id"]),
                    acquired_at=row["acquired_at"],
                    acquisition_type=row["acquisition_type"],
                    gifted_by=row.get("gifted_by"),
                    gift_seen=row.get("gift_seen", True),
                )
            )

        return inventory
