"""
Room service for room state and companion visitor attraction.

Handles:
- Room initialization and state retrieval
- Room layout updates with grid validation
- Companion visitor attraction algorithm (Neko Atsume style)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from app.core.constants import (
    COMPANION_METADATA,
    DISCOVERABLE_COMPANIONS,
    ROOM_GRID_HEIGHT,
    ROOM_GRID_WIDTH,
    VISITOR_COOLDOWN_HOURS,
)
from app.core.database import get_supabase
from app.models.partner import NotPartnerError
from app.models.room import (
    CompanionInfo,
    GiftNotification,
    InvalidPlacementError,
    InventoryItem,
    PartnerRoomResponse,
    RoomPlacement,
    RoomResponse,
    RoomServiceError,
    RoomState,
    ShopItem,
    VisitorResult,
)


class RoomService:
    """Service for room state and companion visitor attraction."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def ensure_room(self, user_id: str) -> RoomState:
        """Get or create the user's room row."""
        result = (
            self.supabase.table("user_room")
            .select("user_id, room_type, layout, active_companion, updated_at")
            .eq("user_id", user_id)
            .execute()
        )

        if result.data:
            row = result.data[0]
            layout = [RoomPlacement(**p) for p in (row.get("layout") or [])]
            return RoomState(
                user_id=row["user_id"],
                room_type=row["room_type"],
                layout=layout,
                active_companion=row.get("active_companion"),
                updated_at=row.get("updated_at"),
            )

        default_row = {
            "user_id": user_id,
            "room_type": "starter",
            "layout": [],
        }
        insert_result = self.supabase.table("user_room").insert(default_row).execute()

        if not insert_result.data:
            raise RoomServiceError("Failed to create room for user")

        return RoomState(user_id=user_id, room_type="starter", layout=[])

    def get_room_state(self, user_id: str) -> RoomResponse:
        """Get complete room state including inventory, companions, and visitors."""
        room = self.ensure_room(user_id)

        inventory_result = (
            self.supabase.table("user_items")
            .select(
                "id, item_id, acquired_at, acquisition_type, "
                "gifted_by, gift_message, gift_seen, items(*)"
            )
            .eq("user_id", user_id)
            .execute()
        )

        inventory: list[InventoryItem] = []
        inventory_raw: list[dict] = []
        for row in inventory_result.data or []:
            item_data = row.get("items")
            shop_item = ShopItem(**item_data) if item_data else None
            inventory.append(
                InventoryItem(
                    id=row["id"],
                    item_id=row["item_id"],
                    item=shop_item,
                    acquired_at=row["acquired_at"],
                    acquisition_type=row.get("acquisition_type", "purchased"),
                    gifted_by=row.get("gifted_by"),
                    gift_seen=row.get("gift_seen", True),
                )
            )
            inventory_raw.append({**row, "_shop_item": item_data})

        companions_result = (
            self.supabase.table("user_companions")
            .select(
                "id, user_id, companion_type, is_starter, discovered_at, visit_scheduled_at, adopted_at"
            )
            .eq("user_id", user_id)
            .execute()
        )

        companions = [CompanionInfo(**row) for row in (companions_result.data or [])]

        visitors = self._check_visitors(
            user_id=user_id,
            layout=[p.model_dump() for p in room.layout],
            inventory_items=inventory_raw,
        )

        essence_result = (
            self.supabase.table("furniture_essence")
            .select("balance")
            .eq("user_id", user_id)
            .execute()
        )
        essence_balance = essence_result.data[0]["balance"] if essence_result.data else 0

        return RoomResponse(
            room=room,
            inventory=inventory,
            companions=companions,
            visitors=visitors,
            essence_balance=essence_balance,
        )

    def update_layout(self, user_id: str, placements: list[RoomPlacement]) -> RoomState:
        """Validate and update the room layout."""
        if not placements:
            self.supabase.table("user_room").update(
                {
                    "layout": [],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("user_id", user_id).execute()
            return self.ensure_room(user_id)

        inventory_ids = [p.inventory_id for p in placements]
        owned_result = (
            self.supabase.table("user_items")
            .select("id, item_id, items(size_w, size_h)")
            .eq("user_id", user_id)
            .in_("id", inventory_ids)
            .execute()
        )

        owned_map: dict = {}
        for row in owned_result.data or []:
            owned_map[row["id"]] = row

        for p in placements:
            if p.inventory_id not in owned_map:
                raise InvalidPlacementError(f"Item {p.inventory_id} not owned by user")

        for p in placements:
            item_data = owned_map[p.inventory_id].get("items") or {}
            size_w = item_data.get("size_w", 1)
            size_h = item_data.get("size_h", 1)

            if p.grid_x < 0 or p.grid_x + size_w > ROOM_GRID_WIDTH:
                raise InvalidPlacementError(
                    f"Item {p.inventory_id} x={p.grid_x} exceeds grid width "
                    f"(needs {size_w} cells, max x={ROOM_GRID_WIDTH - size_w})"
                )
            if p.grid_y < 0 or p.grid_y + size_h > ROOM_GRID_HEIGHT:
                raise InvalidPlacementError(
                    f"Item {p.inventory_id} y={p.grid_y} exceeds grid height "
                    f"(needs {size_h} cells, max y={ROOM_GRID_HEIGHT - size_h})"
                )

        occupied: list[tuple] = []
        for p in placements:
            item_data = owned_map[p.inventory_id].get("items") or {}
            size_w = item_data.get("size_w", 1)
            size_h = item_data.get("size_h", 1)

            cells = []
            for dx in range(size_w):
                for dy in range(size_h):
                    cell = (p.grid_x + dx, p.grid_y + dy)
                    if cell in occupied:
                        raise InvalidPlacementError(
                            f"Overlapping placement at ({cell[0]}, {cell[1]})"
                        )
                    cells.append(cell)
            occupied.extend(cells)

        layout_json = [p.model_dump() for p in placements]
        self.supabase.table("user_room").update(
            {
                "layout": layout_json,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("user_id", user_id).execute()

        return self.ensure_room(user_id)

    def _check_visitors(
        self,
        user_id: str,
        layout: list,
        inventory_items: list[dict],
    ) -> list[VisitorResult]:
        """Run the Neko Atsume companion attraction algorithm."""
        placed_inventory_ids = {p["inventory_id"] for p in layout}
        if not placed_inventory_ids:
            return []

        item_id_to_tags: dict = {}
        for row in inventory_items:
            shop_data = row.get("_shop_item") or row.get("items") or {}
            item_id_to_tags[row["id"]] = shop_data.get("attraction_tags", [])

        placed_tags: dict = {}
        for inv_id in placed_inventory_ids:
            tags = item_id_to_tags.get(inv_id, [])
            for tag in tags:
                placed_tags[tag] = placed_tags.get(tag, 0) + 1

        existing_result = (
            self.supabase.table("user_companions")
            .select("companion_type")
            .eq("user_id", user_id)
            .execute()
        )
        existing_types = {row["companion_type"] for row in (existing_result.data or [])}

        results: list[VisitorResult] = []
        now = datetime.now(timezone.utc)

        for companion_type in DISCOVERABLE_COMPANIONS:
            if companion_type in existing_types:
                continue

            metadata = COMPANION_METADATA.get(companion_type, {})
            preferred_tags = metadata.get("preferred_tags", [])
            threshold = metadata.get("threshold", 3)

            matching_count = 0
            for inv_id in placed_inventory_ids:
                tags = item_id_to_tags.get(inv_id, [])
                if any(tag in preferred_tags for tag in tags):
                    matching_count += 1

            if matching_count >= threshold:
                visit_time = now + timedelta(hours=VISITOR_COOLDOWN_HOURS)
                insert_data = {
                    "user_id": user_id,
                    "companion_type": companion_type,
                    "is_starter": False,
                    "discovered_at": now.isoformat(),
                    "visit_scheduled_at": visit_time.isoformat(),
                }
                # Use upsert with on_conflict to handle concurrent room loads
                # that might both try to insert the same companion type
                upsert_result = (
                    self.supabase.table("user_companions")
                    .upsert(insert_data, on_conflict="user_id,companion_type")
                    .execute()
                )
                if upsert_result.data:
                    results.append(
                        VisitorResult(
                            companion_type=companion_type,
                            visit_scheduled_at=visit_time,
                        )
                    )

        scheduled_result = (
            self.supabase.table("user_companions")
            .select("companion_type, visit_scheduled_at")
            .eq("user_id", user_id)
            .is_("adopted_at", "null")
            .not_.is_("visit_scheduled_at", "null")
            .execute()
        )

        for row in scheduled_result.data or []:
            try:
                scheduled_at = datetime.fromisoformat(
                    row["visit_scheduled_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                continue
            if now >= scheduled_at:
                comp_type = row["companion_type"]
                if not any(r.companion_type == comp_type for r in results):
                    results.append(
                        VisitorResult(
                            companion_type=comp_type,
                            visit_scheduled_at=scheduled_at,
                        )
                    )

        return results

    def _verify_partnership(self, user_id_a: str, user_id_b: str) -> bool:
        """Check if an accepted partnership exists between two users."""
        result = (
            self.supabase.table("partnerships")
            .select("id")
            .eq("status", "accepted")
            .or_(
                f"and(requester_id.eq.{user_id_a},addressee_id.eq.{user_id_b}),"
                f"and(requester_id.eq.{user_id_b},addressee_id.eq.{user_id_a})"
            )
            .limit(1)
            .execute()
        )
        return bool(result.data)

    def get_partner_room(self, viewer_id: str, owner_id: str) -> PartnerRoomResponse:
        """Get a partner's room state (read-only, no visitors or essence balance)."""
        if viewer_id == owner_id:
            raise RoomServiceError("Cannot visit your own room via partner view")

        if not self._verify_partnership(viewer_id, owner_id):
            raise NotPartnerError("You must be partners to visit their room.")

        room = self.ensure_room(owner_id)

        inventory_result = (
            self.supabase.table("user_items")
            .select(
                "id, item_id, acquired_at, acquisition_type, "
                "gifted_by, gift_message, gift_seen, items(*)"
            )
            .eq("user_id", owner_id)
            .execute()
        )

        inventory: list[InventoryItem] = []
        for row in inventory_result.data or []:
            item_data = row.get("items")
            shop_item = ShopItem(**item_data) if item_data else None
            inventory.append(
                InventoryItem(
                    id=row["id"],
                    item_id=row["item_id"],
                    item=shop_item,
                    acquired_at=row["acquired_at"],
                    acquisition_type=row.get("acquisition_type", "purchased"),
                    gifted_by=row.get("gifted_by"),
                    gift_seen=row.get("gift_seen", True),
                )
            )

        companions_result = (
            self.supabase.table("user_companions")
            .select(
                "id, user_id, companion_type, is_starter, discovered_at, "
                "visit_scheduled_at, adopted_at"
            )
            .eq("user_id", owner_id)
            .execute()
        )
        companions = [CompanionInfo(**row) for row in (companions_result.data or [])]

        owner_result = (
            self.supabase.table("users")
            .select("display_name, username, pixel_avatar_id")
            .eq("id", owner_id)
            .execute()
        )
        owner_data = owner_result.data[0] if owner_result.data else {}

        return PartnerRoomResponse(
            room=room,
            inventory=inventory,
            companions=companions,
            owner_name=owner_data.get("display_name") or owner_data.get("username", ""),
            owner_username=owner_data.get("username", ""),
            owner_pixel_avatar_id=owner_data.get("pixel_avatar_id"),
        )

    def get_unseen_gifts(self, user_id: str) -> list[GiftNotification]:
        """Get all unseen gift items for toast notifications on room load."""
        result = (
            self.supabase.table("user_items")
            .select(
                "id, gifted_by, gift_message, items(name, name_zh), users!gifted_by(display_name, username)"
            )
            .eq("user_id", user_id)
            .eq("gift_seen", False)
            .not_.is_("gifted_by", "null")
            .execute()
        )

        notifications: list[GiftNotification] = []
        for row in result.data or []:
            item_data = row.get("items") or {}
            sender_data = row.get("users") or {}
            notifications.append(
                GiftNotification(
                    inventory_item_id=row["id"],
                    item_name=item_data.get("name", "Item"),
                    item_name_zh=item_data.get("name_zh"),
                    gifted_by_name=sender_data.get("display_name")
                    or sender_data.get("username", "Someone"),
                    gift_message=row.get("gift_message"),
                )
            )

        return notifications

    def mark_gifts_seen(self, user_id: str, inventory_ids: list[str]) -> None:
        """Mark specific gift items as seen (dismisses toast notifications)."""
        if not inventory_ids:
            return
        (
            self.supabase.table("user_items")
            .update({"gift_seen": True})
            .eq("user_id", user_id)
            .in_("id", inventory_ids)
            .execute()
        )
