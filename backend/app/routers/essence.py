"""
Essence & Item Shop API endpoints.

Handles:
- GET /balance - Get user's essence balance
- GET /shop - Browse item catalog with filters
- POST /buy - Purchase an item
- POST /gift - Gift an item to a partner
- GET /inventory - Get user's owned items
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.room import (
    EssenceBalance,
    GiftPurchaseRequest,
    GiftPurchaseResponse,
    InventoryItem,
    PurchaseRequest,
    ShopItem,
)
from app.services.essence_service import EssenceService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_essence_service() -> EssenceService:
    return EssenceService()


def get_user_service() -> UserService:
    return UserService()


@router.get("/balance", response_model=EssenceBalance)
async def get_essence_balance(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    essence_service: EssenceService = Depends(get_essence_service),
) -> EssenceBalance:
    """Get current user's essence balance."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return essence_service.get_balance(profile.id)


@router.get("/shop", response_model=list[ShopItem])
async def get_shop_catalog(
    request: Request,
    category: Optional[str] = None,
    tier: Optional[str] = None,
    user: AuthUser = Depends(require_auth_from_state),
    essence_service: EssenceService = Depends(get_essence_service),
) -> list[ShopItem]:
    """Get available shop items with optional category and tier filters."""
    return essence_service.get_shop_items(category=category, tier=tier)


@router.post("/buy", response_model=InventoryItem)
@limiter.limit("10/minute")
async def purchase_item(
    request: Request,
    purchase_request: PurchaseRequest,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    essence_service: EssenceService = Depends(get_essence_service),
) -> InventoryItem:
    """Purchase an item from the shop."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return essence_service.buy_item(user_id=profile.id, item_id=purchase_request.item_id)


@router.post("/gift", response_model=GiftPurchaseResponse)
@limiter.limit("5/minute")
async def gift_item(
    request: Request,
    gift_request: GiftPurchaseRequest,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    essence_service: EssenceService = Depends(get_essence_service),
) -> GiftPurchaseResponse:
    """Buy an item as a gift for a partner."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return essence_service.gift_item(
        sender_id=profile.id,
        recipient_id=gift_request.recipient_id,
        item_id=gift_request.item_id,
        gift_message=gift_request.gift_message,
    )


@router.get("/inventory", response_model=list[InventoryItem])
async def get_user_inventory(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    essence_service: EssenceService = Depends(get_essence_service),
) -> list[InventoryItem]:
    """Get all items owned by the current user."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return essence_service.get_inventory(profile.id)
