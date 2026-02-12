"""
Partner messaging API endpoints.

Handles:
- GET / - List user's conversations
- POST / - Create a new conversation (direct or group)
- POST /reactions/{message_id} - Toggle reaction on a message
- DELETE /msg/{message_id} - Soft-delete a message
- GET /{conversation_id}/messages - Get paginated messages
- POST /{conversation_id}/messages - Send a message
- PUT /{conversation_id}/read - Mark conversation as read
- POST /{conversation_id}/members - Add member to group
- DELETE /{conversation_id}/leave - Leave a group conversation
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.message import (
    AddGroupMemberRequest,
    AddGroupMemberResponse,
    ConversationCreatedResponse,
    ConversationListResponse,
    CreateConversationRequest,
    DeleteMessageResponse,
    LeaveGroupResponse,
    MarkReadResponse,
    MessagesResponse,
    SendMessageRequest,
    SendMessageResponse,
    ToggleReactionRequest,
    ToggleReactionResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_message_service():
    """Dependency to get MessageService instance."""
    from app.services.message_service import MessageService

    return MessageService()


# =============================================================================
# Static Routes (MUST come before parameterized routes)
# =============================================================================


@router.get("/", response_model=ConversationListResponse)
@limiter.limit("60/minute")
async def list_conversations(
    request: Request,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> ConversationListResponse:
    """List all conversations for the current user."""
    conversations = message_service.list_conversations(auth_user.user_id)
    return ConversationListResponse(conversations=conversations)


@router.post("/", response_model=ConversationCreatedResponse)
@limiter.limit("10/minute")
async def create_conversation(
    request: Request,
    body: CreateConversationRequest,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> ConversationCreatedResponse:
    """Create a new direct or group conversation."""
    if body.type.value == "direct":
        if len(body.member_ids) != 1:
            from app.models.message import GroupSizeError

            raise GroupSizeError("Direct conversations require exactly one partner")
        conversation = message_service.create_direct_conversation(
            auth_user.user_id, body.member_ids[0]
        )
    else:
        if not body.name:
            from app.models.message import GroupSizeError

            raise GroupSizeError("Group conversations require a name")
        conversation = message_service.create_group_conversation(
            auth_user.user_id, body.member_ids, body.name
        )
    return ConversationCreatedResponse(conversation=conversation)


@router.post("/reactions/{message_id}", response_model=ToggleReactionResponse)
@limiter.limit("30/minute")
async def toggle_reaction(
    request: Request,
    message_id: str,
    body: ToggleReactionRequest,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> ToggleReactionResponse:
    """Toggle a reaction emoji on a message."""
    result = message_service.toggle_reaction(message_id, auth_user.user_id, body.emoji)
    return ToggleReactionResponse(**result)


@router.delete("/msg/{message_id}", response_model=DeleteMessageResponse)
@limiter.limit("10/minute")
async def delete_message(
    request: Request,
    message_id: str,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> DeleteMessageResponse:
    """Soft-delete a message (sender only)."""
    message_service.delete_message(message_id, auth_user.user_id)
    return DeleteMessageResponse(message_id=message_id)


# =============================================================================
# Parameterized Routes
# =============================================================================


@router.get("/{conversation_id}/messages", response_model=MessagesResponse)
@limiter.limit("60/minute")
async def get_messages(
    request: Request,
    conversation_id: str,
    cursor: Optional[str] = Query(None, description="Pagination cursor (created_at timestamp)"),
    limit: int = Query(50, ge=1, le=100, description="Messages per page"),
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> MessagesResponse:
    """Get paginated messages for a conversation (newest first)."""
    result = message_service.get_messages(
        conversation_id, auth_user.user_id, cursor=cursor, limit=limit
    )
    return MessagesResponse(**result)


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conversation_id: str,
    body: SendMessageRequest,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> SendMessageResponse:
    """Send a message to a conversation."""
    message = message_service.send_message(conversation_id, auth_user.user_id, body.content)
    return SendMessageResponse(message=message)


@router.put("/{conversation_id}/read", response_model=MarkReadResponse)
@limiter.limit("60/minute")
async def mark_read(
    request: Request,
    conversation_id: str,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> MarkReadResponse:
    """Mark a conversation as read."""
    result = message_service.mark_read(conversation_id, auth_user.user_id)
    return MarkReadResponse(**result)


@router.post("/{conversation_id}/members", response_model=AddGroupMemberResponse)
@limiter.limit("10/minute")
async def add_group_member(
    request: Request,
    conversation_id: str,
    body: AddGroupMemberRequest,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> AddGroupMemberResponse:
    """Add a member to a group conversation."""
    message_service.add_group_member(conversation_id, auth_user.user_id, body.user_id)
    return AddGroupMemberResponse(conversation_id=conversation_id, user_id=body.user_id)


@router.delete("/{conversation_id}/leave", response_model=LeaveGroupResponse)
@limiter.limit("10/minute")
async def leave_group(
    request: Request,
    conversation_id: str,
    auth_user: AuthUser = Depends(require_auth_from_state),
    message_service=Depends(get_message_service),
) -> LeaveGroupResponse:
    """Leave a group conversation."""
    message_service.leave_group(conversation_id, auth_user.user_id)
    return LeaveGroupResponse()
