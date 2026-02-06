"""
LiveKit service for room management and token generation.

Handles:
- Room creation with audio-only configuration
- Room deletion after sessions end
- Mode-aware token generation (Forced Audio vs Quiet Mode)
- Room state queries for health checks
"""

from datetime import timedelta
from typing import Optional

from livekit import api

from app.core.config import get_settings
from app.core.constants import DISCONNECT_GRACE_PERIOD_SECONDS, MAX_PARTICIPANTS
from app.models.session import TableMode


class LiveKitServiceError(Exception):
    """Base exception for LiveKit service errors."""

    pass


class RoomNotFoundError(LiveKitServiceError):
    """Room does not exist."""

    pass


class LiveKitService:
    """Service for LiveKit room management and token generation."""

    def __init__(self):
        self._settings = get_settings()
        self._api: Optional[api.LiveKitAPI] = None

    @property
    def is_configured(self) -> bool:
        """Check if LiveKit credentials are configured."""
        return bool(
            self._settings.livekit_api_key
            and self._settings.livekit_api_key != "your-livekit-api-key"
            and self._settings.livekit_api_secret
            and self._settings.livekit_url
        )

    def _get_api(self) -> api.LiveKitAPI:
        """Get or create LiveKitAPI instance."""
        if self._api is None:
            if not self.is_configured:
                raise LiveKitServiceError("LiveKit credentials not configured")

            self._api = api.LiveKitAPI(
                self._settings.livekit_url,
                self._settings.livekit_api_key,
                self._settings.livekit_api_secret,
            )
        return self._api

    async def create_room(
        self,
        room_name: str,
        mode: TableMode = TableMode.FORCED_AUDIO,
    ) -> dict:
        """
        Create a LiveKit room with audio-only configuration.

        Args:
            room_name: Unique room identifier
            mode: Table mode (affects empty timeout behavior)

        Returns:
            Room info dict with name, sid, creation_time

        Raises:
            LiveKitServiceError: If room creation fails
        """
        if not self.is_configured:
            # Return mock response for dev mode
            return {
                "name": room_name,
                "sid": f"dev-{room_name}",
                "creation_time": 0,
                "mode": mode.value,
            }

        try:
            lk_api = self._get_api()
            room = await lk_api.room.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    max_participants=MAX_PARTICIPANTS,
                    empty_timeout=DISCONNECT_GRACE_PERIOD_SECONDS,
                    # Room metadata stores mode for webhook handlers
                    metadata=f'{{"mode": "{mode.value}"}}',
                )
            )

            return {
                "name": room.name,
                "sid": room.sid,
                "creation_time": room.creation_time,
                "mode": mode.value,
            }
        except Exception as e:
            raise LiveKitServiceError(f"Failed to create room: {e}") from e

    async def delete_room(self, room_name: str) -> bool:
        """
        Delete a LiveKit room.

        Args:
            room_name: Room name to delete

        Returns:
            True if deleted successfully

        Raises:
            LiveKitServiceError: If deletion fails
        """
        if not self.is_configured:
            return True  # No-op in dev mode

        try:
            lk_api = self._get_api()
            await lk_api.room.delete_room(api.DeleteRoomRequest(room=room_name))
            return True
        except Exception as e:
            raise LiveKitServiceError(f"Failed to delete room: {e}") from e

    async def get_room(self, room_name: str) -> Optional[dict]:
        """
        Get room information.

        Args:
            room_name: Room name to query

        Returns:
            Room info dict or None if not found
        """
        if not self.is_configured:
            return None  # No-op in dev mode

        try:
            lk_api = self._get_api()
            response = await lk_api.room.list_rooms(api.ListRoomsRequest(names=[room_name]))
            if response.rooms:
                room = response.rooms[0]
                return {
                    "name": room.name,
                    "sid": room.sid,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                }
            return None
        except Exception as e:
            raise LiveKitServiceError(f"Failed to get room: {e}") from e

    async def close(self) -> None:
        """Close the API client and release resources."""
        if self._api is not None:
            await self._api.aclose()
            self._api = None

    def generate_token(
        self,
        room_name: str,
        participant_identity: str,
        participant_name: str,
        mode: TableMode = TableMode.FORCED_AUDIO,
    ) -> str:
        """
        Generate a LiveKit access token for a participant.

        Token permissions are based on table mode:
        - Forced Audio: canPublish=True (must have mic on)
        - Quiet Mode: canPublish=False (muted by default, can request to speak)

        Args:
            room_name: LiveKit room name
            participant_identity: Unique participant identifier (user_id)
            participant_name: Display name for the participant
            mode: Table mode determining publish permissions

        Returns:
            JWT access token string
        """
        if not self.is_configured:
            return "dev-placeholder-token"

        token = api.AccessToken(
            self._settings.livekit_api_key,
            self._settings.livekit_api_secret,
        )

        token.with_identity(participant_identity)
        token.with_name(participant_name)

        # Mode determines whether participant can publish audio
        # Quiet Mode: Start muted, can request to speak (handled client-side)
        can_publish = mode == TableMode.FORCED_AUDIO

        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_publish_data=True,  # Allow data channel for chat/timer sync
                can_subscribe=True,
            )
        )

        # Set token expiry (2 hours, covers full session + buffer)
        token.with_ttl(timedelta(hours=2))

        return token.to_jwt()
