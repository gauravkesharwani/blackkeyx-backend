"""Voice service for call management operations."""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository
from app.models.voice import CallSession
from app.services.livekit_dispatcher import get_livekit_dispatcher

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for voice/call operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.call_repo = CallRepository(session)
        self.investor_repo = InvestorRepository(session)
        self.livekit = get_livekit_dispatcher()

    async def complete_session(
        self,
        room_name: str,
        transcript: str,
        duration: int,
    ) -> Optional[CallSession]:
        """
        Complete a call session - save transcript and update investor stage.

        Returns the updated CallSession or None if not found.
        """
        # Save transcript and mark call completed
        call = await self.call_repo.save_transcript(
            room_name=room_name,
            transcript=transcript,
            duration=duration,
        )

        if not call:
            logger.warning(f"Call not found for room: {room_name}")
            return None

        # Update investor stage to "call_completed"
        await self.investor_repo.update_stage(
            investor_id=call.investor_id,
            new_stage="call_completed",
            changed_by="system",
            notes="Call completed automatically",
        )

        await self.session.commit()
        logger.info(f"Session completed for call: {call.id}")
        return call

    async def get_call_status(self, room_name: str) -> Optional[CallSession]:
        """Get call status by room name."""
        return await self.call_repo.get_by_room_name(room_name)

    async def check_room_active(self, room_name: str) -> dict:
        """Check if a LiveKit room is still active."""
        room_info = await self.livekit.get_room_status(room_name)
        return {
            "active": room_info is not None,
            "participants": room_info.get("num_participants", 0) if room_info else 0,
        }

    async def end_call(self, room_name: str) -> bool:
        """Force end a call by deleting the room."""
        return await self.livekit.end_call(room_name)
