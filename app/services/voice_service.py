"""Voice service for call management operations."""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository
from app.models.voice import CallSession
from app.services.livekit_dispatcher import get_livekit_dispatcher

logger = logging.getLogger(__name__)


def _compute_duration_from_history(history: list[dict[str, Any]]) -> Optional[int]:
    """Compute call duration in seconds from history timestamps."""
    timestamps: list[float] = []

    for item in history:
        if item.get("type") != "message":
            continue
        metrics = item.get("metrics", {})
        started = metrics.get("started_speaking_at")
        stopped = metrics.get("stopped_speaking_at")

        if started is not None:
            timestamps.append(started)
        if stopped is not None:
            timestamps.append(stopped)

    if len(timestamps) >= 2:
        return int(max(timestamps) - min(timestamps))
    return None


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
        duration: Optional[int] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> Optional[CallSession]:
        """
        Complete a call session - save transcript and update investor stage.

        Returns the updated CallSession or None if not found.
        """
        # Compute duration from history if not provided
        if duration is None and history:
            duration = _compute_duration_from_history(history)

        # Save transcript and mark call completed
        call = await self.call_repo.save_transcript(
            room_name=room_name,
            transcript=transcript,
            duration=duration or 0,
        )

        if not call:
            logger.warning(f"Call not found for room: {room_name}")
            return None

        # Save detailed transcript segments from history
        if history:
            await self._save_transcript_segments(call.id, history)

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

    async def _save_transcript_segments(
        self,
        call_id: Any,
        history: list[dict[str, Any]],
    ) -> None:
        """Parse history items and save as transcript segments."""
        for item in history:
            if item.get("type") != "message":
                continue

            role = item.get("role", "")
            content_list = item.get("content", [])
            content = " ".join(c for c in content_list if isinstance(c, str))

            if not content:
                continue

            # Map role to speaker
            speaker = "agent" if role == "assistant" else "investor"

            # Extract metrics
            metrics = item.get("metrics", {})
            start_time = metrics.get("started_speaking_at")
            end_time = metrics.get("stopped_speaking_at")
            confidence = item.get("transcript_confidence")

            await self.call_repo.add_transcript_segment(
                call_session_id=call_id,
                speaker=speaker,
                content=content,
                start_time=start_time,
                end_time=end_time,
                confidence=confidence,
            )

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
