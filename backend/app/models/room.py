"""
Room, companion, and item shop models.

Aligned with design doc: output/plan/2026-02-12-gamification-design.md
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import ROOM_GRID_HEIGHT, ROOM_GRID_WIDTH

# ===========================================
# Enums
# ===========================================


class ItemCategory(str, Enum):
    """Item categories in the shop catalog."""

    FURNITURE = "furniture"
    DECOR = "decor"
    PLANT = "plant"
    PET_ACCESSORY = "pet_accessory"
    SEASONAL = "seasonal"


class ItemTier(str, Enum):
    """Item pricing tiers."""

    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class ItemRarity(str, Enum):
    """Item rarity levels."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"


class RoomType(str, Enum):
    """Room types unlocked via milestones."""

    STARTER = "starter"
    STUDY_LOFT = "study_loft"
    ROOFTOP_GARDEN = "rooftop_garden"
    COZY_CABIN = "cozy_cabin"


class CompanionType(str, Enum):
    """All companion types (4 starters + 4 discoverable)."""

    CAT = "cat"
    DOG = "dog"
    BUNNY = "bunny"
    HAMSTER = "hamster"
    OWL = "owl"
    FOX = "fox"
    TURTLE = "turtle"
    RACCOON = "raccoon"


class CompanionStatus(str, Enum):
    """Computed companion status."""

    ADOPTED = "adopted"
    VISITING = "visiting"
    SCHEDULED = "scheduled"


# ===========================================
# Response Models
# ===========================================


class ShopItem(BaseModel):
    """An item from the catalog (shop display)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_zh: Optional[str] = None
    description: Optional[str] = None
    description_zh: Optional[str] = None
    category: str
    rarity: str
    image_url: Optional[str] = None
    essence_cost: int
    tier: str
    size_w: int = 1
    size_h: int = 1
    attraction_tags: list = Field(default_factory=list)
    is_available: bool = True


class InventoryItem(BaseModel):
    """An item the user owns (one row per copy)."""

    model_config = ConfigDict(from_attributes=True)

    id: str  # user_items.id (unique per copy)
    item_id: str
    item: Optional[ShopItem] = None  # joined catalog data
    acquired_at: Optional[datetime] = None  # Set by DB on insert, may be None on fresh purchase
    acquisition_type: str = "purchased"
    gifted_by: Optional[str] = None
    gifted_by_name: Optional[str] = None
    gift_seen: bool = True


class RoomPlacement(BaseModel):
    """A single item placed on the room grid."""

    inventory_id: str
    grid_x: int = Field(ge=0, lt=ROOM_GRID_WIDTH)
    grid_y: int = Field(ge=0, lt=ROOM_GRID_HEIGHT)
    rotation: int = Field(default=0, ge=0, lt=4)  # 0, 1, 2, 3 = 0, 90, 180, 270


class RoomState(BaseModel):
    """User's room state."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    room_type: str = "starter"
    layout: list[RoomPlacement] = Field(default_factory=list)
    active_companion: Optional[str] = None
    updated_at: Optional[datetime] = None


class CompanionInfo(BaseModel):
    """A companion the user has (adopted or visiting)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    companion_type: str
    is_starter: bool = False
    discovered_at: Optional[datetime] = None
    visit_scheduled_at: Optional[datetime] = None
    adopted_at: Optional[datetime] = None

    @property
    def status(self) -> CompanionStatus:
        if self.adopted_at:
            return CompanionStatus.ADOPTED
        if self.visit_scheduled_at and not self.adopted_at:
            return CompanionStatus.SCHEDULED
        return CompanionStatus.VISITING


class VisitorResult(BaseModel):
    """A newly discovered companion visitor."""

    companion_type: str
    visit_scheduled_at: datetime


class EssenceBalance(BaseModel):
    """User's essence balance."""

    model_config = ConfigDict(from_attributes=True)

    balance: int = 0
    total_earned: int = 0
    total_spent: int = 0


class RoomResponse(BaseModel):
    """Complete room state response (room + inventory + companions + visitors)."""

    room: RoomState
    inventory: list[InventoryItem]
    companions: list[CompanionInfo]
    visitors: list[VisitorResult] = Field(default_factory=list)
    essence_balance: int = 0


# ===========================================
# Request Models
# ===========================================


class GiftPurchaseRequest(BaseModel):
    """Buy an item as a gift for a partner."""

    item_id: str
    recipient_id: str
    gift_message: Optional[str] = Field(None, max_length=200)


class PurchaseResponse(BaseModel):
    """Enriched response after purchasing an item (includes updated balance and inventory count)."""

    item: InventoryItem
    balance: EssenceBalance
    inventory_count: int


class GiftPurchaseResponse(BaseModel):
    """Response after gifting an item."""

    inventory_item_id: str
    item_name: str
    recipient_name: str
    essence_spent: int
    balance: Optional[EssenceBalance] = None


class PartnerRoomResponse(BaseModel):
    """Read-only partner room state (no visitors, no essence balance)."""

    room: RoomState
    inventory: list[InventoryItem]
    companions: list[CompanionInfo]
    owner_name: str
    owner_username: str
    owner_pixel_avatar_id: Optional[str] = None


class GiftNotification(BaseModel):
    """Unseen gift info for toast display on room load."""

    inventory_item_id: str
    item_name: str
    item_name_zh: Optional[str] = None
    gifted_by_name: str
    gift_message: Optional[str] = None


class MarkGiftsSeenRequest(BaseModel):
    """Request to mark gift items as seen."""

    inventory_ids: list[str]


class PurchaseRequest(BaseModel):
    """Purchase an item from the shop."""

    item_id: str


class LayoutUpdate(BaseModel):
    """Update the room layout."""

    placements: list[RoomPlacement]


class StarterChoice(BaseModel):
    """Choose a starter companion."""

    companion_type: CompanionType


class AdoptRequest(BaseModel):
    """Adopt a visiting companion."""

    companion_type: CompanionType


# ===========================================
# Exception Classes
# ===========================================


class EssenceServiceError(Exception):
    """Base exception for essence/shop errors."""

    pass


class InsufficientEssenceError(EssenceServiceError):
    """Not enough essence to make a purchase."""

    pass


class ItemNotFoundError(EssenceServiceError):
    """Item not found or not available."""

    pass


class RoomServiceError(Exception):
    """Base exception for room errors."""

    pass


class InvalidPlacementError(RoomServiceError):
    """Item placement is invalid (wrong position, not owned, etc.)."""

    pass


class CompanionServiceError(Exception):
    """Base exception for companion errors."""

    pass


class AlreadyHasStarterError(CompanionServiceError):
    """User already chose a starter companion."""

    pass


class InvalidStarterError(CompanionServiceError):
    """Not a valid starter companion type."""

    pass


class VisitorNotFoundError(CompanionServiceError):
    """No visiting companion of this type exists."""

    pass


class SelfGiftError(EssenceServiceError):
    """Cannot gift an item to yourself."""

    pass
