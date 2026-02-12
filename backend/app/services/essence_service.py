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
from app.models.room import (
    EssenceBalance,
    EssenceServiceError,
    InsufficientEssenceError,
    InventoryItem,
    ItemNotFoundError,
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

        balance_result = (
            self.supabase.table("furniture_essence")
            .select("balance, total_spent")
            .eq("user_id", user_id)
            .execute()
        )

        if not balance_result.data:
            raise InsufficientEssenceError(f"No essence balance found for user {user_id}")

        current_balance = balance_result.data[0]["balance"]
        current_spent = balance_result.data[0]["total_spent"]

        if current_balance < cost:
            raise InsufficientEssenceError(
                f"Insufficient essence: need {cost}, have {current_balance}"
            )

        self.supabase.table("furniture_essence").update(
            {
                "balance": current_balance - cost,
                "total_spent": current_spent + cost,
            }
        ).eq("user_id", user_id).execute()

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
