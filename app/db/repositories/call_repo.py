"""
Call session repository for voice call data access.
"""

import uuid
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.base import BaseRepository
from app.models.voice import CallbackRequest, CallSession, CallTranscript


class CallRepository(BaseRepository[CallSession]):
    """Repository for call session operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(CallSession, session)

    async def get_by_room_name(self, room_name: str) -> Optional[CallSession]:
        """Get call session by LiveKit room name."""
        result = await self.session.execute(
            select(CallSession).where(CallSession.room_name == room_name)
        )
        return result.scalar_one_or_none()

    async def get_by_investor(
        self, investor_id: uuid.UUID, limit: int = 10
    ) -> Sequence[CallSession]:
        """Get call sessions for an investor, ordered by most recent."""
        result = await self.session.execute(
            select(CallSession)
            .where(CallSession.investor_id == investor_id)
            .order_by(CallSession.initiated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_call(
        self,
        investor_id: uuid.UUID,
        room_name: str,
        status: str = "initiated",
    ) -> CallSession:
        """Create a new call session record."""
        call = CallSession(
            id=uuid.uuid4(),
            investor_id=investor_id,
            room_name=room_name,
            status=status,
            initiated_at=datetime.utcnow(),
        )
        self.session.add(call)
        await self.session.flush()
        await self.session.refresh(call)
        return call

    async def update_status(
        self,
        call_id: uuid.UUID,
        status: str,
        completed_at: Optional[datetime] = None,
    ) -> Optional[CallSession]:
        """Update call status."""
        await self.session.execute(
            update(CallSession)
            .where(CallSession.id == call_id)
            .values(status=status, completed_at=completed_at)
        )
        return await self.get(call_id)

    async def save_transcript(
        self,
        room_name: str,
        transcript: str,
        duration: int,
    ) -> Optional[CallSession]:
        """
        Save transcript and complete a call session.

        Called by the LiveKit agent when session ends.
        """
        call = await self.get_by_room_name(room_name)
        if not call:
            return None

        await self.session.execute(
            update(CallSession)
            .where(CallSession.room_name == room_name)
            .values(
                transcript=transcript,
                duration=duration,
                status="completed",
                completed_at=datetime.utcnow(),
            )
        )

        return await self.get_by_room_name(room_name)

    async def add_transcript_segment(
        self,
        call_session_id: uuid.UUID,
        speaker: str,
        content: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> CallTranscript:
        """Add a transcript segment to a call session."""
        segment = CallTranscript(
            id=uuid.uuid4(),
            call_session_id=call_session_id,
            speaker=speaker,
            content=content,
            start_time=start_time,
            end_time=end_time,
            confidence=confidence,
        )
        self.session.add(segment)
        await self.session.flush()
        await self.session.refresh(segment)
        return segment

    async def get_transcripts(
        self, call_session_id: uuid.UUID
    ) -> Sequence[CallTranscript]:
        """Get all transcript segments for a call session."""
        result = await self.session.execute(
            select(CallTranscript)
            .where(CallTranscript.call_session_id == call_session_id)
            .order_by(CallTranscript.start_time)
        )
        return result.scalars().all()

    async def create_callback_request(
        self,
        investor_id: uuid.UUID,
        call_session_id: uuid.UUID,
        requested_datetime_raw: str,
        requested_datetime: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> CallbackRequest:
        """Create a callback request record."""
        callback = CallbackRequest(
            id=uuid.uuid4(),
            investor_id=investor_id,
            call_session_id=call_session_id,
            requested_datetime_raw=requested_datetime_raw,
            requested_datetime=requested_datetime,
            notes=notes,
            status="pending",
        )
        self.session.add(callback)
        await self.session.flush()
        await self.session.refresh(callback)
        return callback

    async def get_pending_callbacks(
        self, investor_id: Optional[uuid.UUID] = None
    ) -> Sequence[CallbackRequest]:
        """Get pending callback requests, optionally filtered by investor."""
        query = select(CallbackRequest).where(CallbackRequest.status == "pending")
        if investor_id:
            query = query.where(CallbackRequest.investor_id == investor_id)
        query = query.order_by(CallbackRequest.requested_datetime.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_callback_status(
        self,
        callback_id: uuid.UUID,
        status: str,
        completed_at: Optional[datetime] = None,
    ) -> Optional[CallbackRequest]:
        """Update callback request status."""
        await self.session.execute(
            update(CallbackRequest)
            .where(CallbackRequest.id == callback_id)
            .values(status=status, completed_at=completed_at)
        )
        result = await self.session.execute(
            select(CallbackRequest).where(CallbackRequest.id == callback_id)
        )
        return result.scalar_one_or_none()
