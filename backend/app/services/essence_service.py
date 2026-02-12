"""
Essence service for item shop and purchase operations.

Handles:
- Essence balance queries
- Shop catalog browsing with filters
- Item purchases with balance deduction
- User inventory retrieval
"""

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
    SelfGiftError,
    ShopItem,
)

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

    def buy_item(self, user_id: str, item_id: str) -> InventoryItem:
        item_result = self.supabase.table("items").select("*").eq("id", item_id).execute()

        if not item_result.data:
            raise ItemNotFoundError(f"Item {item_id} not found")

        item_data = item_result.data[0]

        if not item_data.get("is_available") or not item_data.get("is_purchasable"):
            raise ItemNotFoundError(f"Item {item_id} is not available for purchase")

        cost = item_data["essence_cost"]

        # Atomic balance deduction via RPC — prevents race conditions from
        # concurrent purchases by using UPDATE ... WHERE balance >= cost
        deduct_result = self.supabase.rpc(
            "deduct_essence",
            {"p_user_id": user_id, "p_cost": cost},
        ).execute()

        if not deduct_result.data or not deduct_result.data.get("success", False):
            raise InsufficientEssenceError(f"Insufficient essence to purchase item costing {cost}")

        self.supabase.table("essence_transactions").insert(
            {
                "user_id": user_id,
                "amount": -cost,
                "transaction_type": "item_purchase",
                "description": f"Purchased {item_data['name']}",
                "related_item_id": item_id,
            }
        ).execute()

        inventory_result = (
            self.supabase.table("user_items")
            .insert(
                {
                    "user_id": user_id,
                    "item_id": item_id,
                    "acquisition_type": "purchased",
                }
            )
            .execute()
        )

        if not inventory_result.data:
            raise EssenceServiceError("Failed to add item to inventory")

        row = inventory_result.data[0]
        return InventoryItem(
            id=row["id"],
            item_id=row["item_id"],
            item=ShopItem(**item_data),
            acquired_at=row["acquired_at"],
            acquisition_type=row["acquisition_type"],
        )

    def gift_item(
        self,
        sender_id: str,
        recipient_id: str,
        item_id: str,
        gift_message: Optional[str] = None,
    ) -> GiftPurchaseResponse:
        """Buy an item as a gift for a partner.

        Flow: validate self-gift → look up item → check partnership →
        deduct sender essence → log transaction → insert inventory for recipient.
        """
        if sender_id == recipient_id:
            raise SelfGiftError("Cannot gift an item to yourself.")

        # Look up item
        item_result = self.supabase.table("items").select("*").eq("id", item_id).execute()
        if not item_result.data:
            raise ItemNotFoundError(f"Item {item_id} not found")

        item_data = item_result.data[0]
        if not item_data.get("is_available") or not item_data.get("is_purchasable"):
            raise ItemNotFoundError(f"Item {item_id} is not available for purchase")

        # Verify accepted partnership
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

        cost = item_data["essence_cost"]

        # Atomic deduction from sender's balance
        deduct_result = self.supabase.rpc(
            "deduct_essence",
            {"p_user_id": sender_id, "p_cost": cost},
        ).execute()

        if not deduct_result.data or not deduct_result.data.get("success", False):
            raise InsufficientEssenceError(f"Insufficient essence to gift item costing {cost}")

        # Log transaction for sender
        self.supabase.table("essence_transactions").insert(
            {
                "user_id": sender_id,
                "amount": -cost,
                "transaction_type": "item_gift",
                "description": f"Gifted {item_data['name']} to {recipient_name}",
                "related_item_id": item_id,
            }
        ).execute()

        # Insert item into recipient's inventory
        insert_data: dict = {
            "user_id": recipient_id,
            "item_id": item_id,
            "acquisition_type": "gift",
            "gifted_by": sender_id,
        }
        if gift_message:
            insert_data["gift_message"] = gift_message

        inventory_result = self.supabase.table("user_items").insert(insert_data).execute()

        if not inventory_result.data:
            raise EssenceServiceError("Failed to add gift to recipient's inventory")

        return GiftPurchaseResponse(
            inventory_item_id=inventory_result.data[0]["id"],
            item_name=item_data["name"],
            recipient_name=recipient_name,
            essence_spent=cost,
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
                )
            )

        return inventory
