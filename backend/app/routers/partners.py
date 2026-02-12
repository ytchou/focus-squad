"""
Accountability partners API endpoints.

Handles:
- GET / - List accepted partners
- GET /requests - List pending partnership requests
- GET /search - Search users by query
- POST /request - Send a partner request
- POST /request/{partnership_id}/respond - Accept or decline a request
- DELETE /{partnership_id} - Remove a partner
"""

import logging

from fastapi import APIRouter, Depends, Query, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.partner import (
    PartnerListResponse,
    PartnerRemoveResponse,
    PartnerRequestCreate,
    PartnerRequestRespond,
    PartnerRequestResponse,
    PartnerRequestsResponse,
    PartnerRespondResponse,
    UserSearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_partner_service():
    """Dependency to get PartnerService instance."""
    from app.services.partner_service import PartnerService

    return PartnerService()


# =============================================================================
# Static Routes (MUST come before parameterized routes)
# =============================================================================


@router.get("/", response_model=PartnerListResponse)
@limiter.limit("60/minute")
async def list_partners(
    request: Request,
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> PartnerListResponse:
    """List all accepted accountability partners for the current user."""
    return partner_service.list_partners(auth_user.user_id)


@router.get("/requests", response_model=PartnerRequestsResponse)
@limiter.limit("60/minute")
async def list_requests(
    request: Request,
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> PartnerRequestsResponse:
    """List pending partnership requests (both sent and received)."""
    return partner_service.list_requests(auth_user.user_id)


@router.get("/search", response_model=UserSearchResponse)
@limiter.limit("60/minute")
async def search_users(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> UserSearchResponse:
    """Search users by username or display name to send partner requests."""
    return partner_service.search_users(q, auth_user.user_id)


@router.post("/request", response_model=PartnerRequestResponse)
@limiter.limit("10/minute")
async def send_request(
    request: Request,
    body: PartnerRequestCreate,
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> PartnerRequestResponse:
    """Send an accountability partner request to another user."""
    return partner_service.send_request(auth_user.user_id, body.addressee_id)


# =============================================================================
# Parameterized Routes
# =============================================================================


@router.post("/request/{partnership_id}/respond", response_model=PartnerRespondResponse)
@limiter.limit("10/minute")
async def respond_to_request(
    request: Request,
    partnership_id: str,
    body: PartnerRequestRespond,
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> PartnerRespondResponse:
    """Accept or decline a pending partnership request."""
    return partner_service.respond_to_request(partnership_id, auth_user.user_id, body.accept)


@router.delete("/{partnership_id}", response_model=PartnerRemoveResponse)
@limiter.limit("10/minute")
async def remove_partner(
    request: Request,
    partnership_id: str,
    auth_user: AuthUser = Depends(require_auth_from_state),
    partner_service=Depends(get_partner_service),
) -> PartnerRemoveResponse:
    """Remove an existing accountability partner."""
    return partner_service.remove_partner(partnership_id, auth_user.user_id)
