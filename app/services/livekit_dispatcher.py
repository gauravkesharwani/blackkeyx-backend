"""
LiveKit dispatcher service for voice AI calls.

Handles dispatching outbound calls to investors via LiveKit Agents.
"""

import json
import random
import logging
from typing import Optional

from livekit import api

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LiveKitDispatcher:
    """Dispatches LiveKit voice agents for investor calls."""

    def __init__(self):
        self._api: Optional[api.LiveKitAPI] = None

    @property
    def api(self) -> api.LiveKitAPI:
        """Lazy initialization of LiveKit API client."""
        if self._api is None:
            if not settings.livekit_url or not settings.livekit_api_key:
                raise RuntimeError("LiveKit credentials not configured")

            self._api = api.LiveKitAPI(
                settings.livekit_url,
                settings.livekit_api_key,
                settings.livekit_api_secret,
            )
        return self._api

    async def dispatch_outbound_call(
        self,
        phone_number: str,
        investor_context: dict,
    ) -> str:
        """
        Dispatch agent to make outbound call to investor.

        Args:
            phone_number: Phone number to dial (E.164 format, e.g. +15105550123)
            investor_context: Context data to pass to the agent (name, capital, etc.)

        Returns:
            str: Room name where the call is taking place

        Raises:
            RuntimeError: If LiveKit credentials are not configured
            api.TwirpError: If the API call fails
        """
        # Generate unique room name
        room_name = f"outbound-{''.join(str(random.randint(0, 9)) for _ in range(10))}"

        logger.info(f"Dispatching outbound call to {phone_number} in room {room_name}")

        # Dispatch agent to new room with investor context
        await self.api.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name="blackkeyx-advisor",
                room=room_name,
                metadata=json.dumps({**investor_context, "outbound": True}),
            )
        )

        # Create SIP participant to dial out
        if settings.livekit_sip_trunk_id:
            try:
                request = api.CreateSIPParticipantRequest(
                    room_name=room_name,
                    sip_trunk_id=settings.livekit_sip_trunk_id,
                    sip_call_to=phone_number,
                    participant_identity=phone_number,
                    wait_until_answered=True,
                )
                # Add caller ID if configured
                if settings.livekit_sip_number:
                    request.sip_number = settings.livekit_sip_number

                await self.api.sip.create_sip_participant(request)
                logger.info(f"SIP participant created for {phone_number}")
            except api.TwirpError as e:
                logger.error(
                    f"Error creating SIP participant: {e.message}, "
                    f"SIP status: {e.metadata.get('sip_status_code')} "
                    f"{e.metadata.get('sip_status')}"
                )
                raise
        else:
            logger.warning("SIP trunk not configured, skipping dial out")

        return room_name

    async def get_room_status(self, room_name: str) -> Optional[dict]:
        """
        Get status of a room.

        Args:
            room_name: Name of the room to check

        Returns:
            Optional[dict]: Room info if exists, None otherwise
        """
        try:
            rooms = await self.api.room.list_rooms(
                api.ListRoomsRequest(names=[room_name])
            )
            if rooms.rooms:
                room = rooms.rooms[0]
                return {
                    "name": room.name,
                    "num_participants": room.num_participants,
                    "creation_time": room.creation_time,
                }
        except Exception as e:
            logger.error(f"Error getting room status: {e}")

        return None

    async def end_call(self, room_name: str) -> bool:
        """
        End a call by deleting the room.

        Args:
            room_name: Name of the room to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            await self.api.room.delete_room(
                api.DeleteRoomRequest(room=room_name)
            )
            logger.info(f"Room {room_name} deleted")
            return True
        except Exception as e:
            logger.error(f"Error deleting room {room_name}: {e}")
            return False


# Singleton instance
_dispatcher: Optional[LiveKitDispatcher] = None


def get_livekit_dispatcher() -> LiveKitDispatcher:
    """Get or create the LiveKit dispatcher singleton."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = LiveKitDispatcher()
    return _dispatcher
