"""
Call session repository for voice call data access.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select, update
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
        retry_count: int = 0,
    ) -> CallSession:
        """Create a new call session record."""
        call = CallSession(
            id=uuid.uuid4(),
            investor_id=investor_id,
            room_name=room_name,
            direction="outbound",
            status=status,
            retry_count=retry_count,
            initiated_at=datetime.now(timezone.utc),
        )
        self.session.add(call)
        await self.session.flush()
        await self.session.refresh(call)
        return call

    async def create_inbound_call(
        self,
        room_name: str,
        caller_phone: str,
        investor_id: Optional[uuid.UUID] = None,
    ) -> CallSession:
        """Create a call session record for an inbound call."""
        call = CallSession(
            id=uuid.uuid4(),
            investor_id=investor_id,
            room_name=room_name,
            caller_phone=caller_phone,
            direction="inbound",
            status="initiated",
            initiated_at=datetime.now(timezone.utc),
        )
        self.session.add(call)
        await self.session.flush()
        await self.session.refresh(call)
        return call

    async def update_inbound_caller(
        self,
        call_id: uuid.UUID,
        caller_phone: str,
        investor_id: uuid.UUID,
    ) -> None:
        """Patch caller_phone and investor_id on an inbound call that was stored with 'unknown'."""
        await self.session.execute(
            update(CallSession)
            .where(CallSession.id == call_id)
            .values(caller_phone=caller_phone, investor_id=investor_id)
        )

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
                completed_at=datetime.now(timezone.utc),
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

    async def get_due_callbacks(
        self, grace_window_minutes: int = 2
    ) -> Sequence[CallbackRequest]:
        """Get pending callbacks whose requested_datetime is due (within grace window)."""
        cutoff = datetime.now(timezone.utc) + timedelta(minutes=grace_window_minutes)
        query = (
            select(CallbackRequest)
            .where(CallbackRequest.status == "pending")
            .where(CallbackRequest.requested_datetime.isnot(None))
            .where(CallbackRequest.requested_datetime <= cutoff)
            .order_by(CallbackRequest.requested_datetime.asc())
        )
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

    # --- Voicemail methods ---

    async def update_voicemail_fields(
        self,
        call_id: uuid.UUID,
        voicemail_detected: bool,
        voicemail_confidence: float,
        voicemail_message_left: bool,
    ) -> None:
        """Update voicemail detection fields on a call session."""
        await self.session.execute(
            update(CallSession)
            .where(CallSession.id == call_id)
            .values(
                voicemail_detected=voicemail_detected,
                voicemail_confidence=voicemail_confidence,
                voicemail_message_left=voicemail_message_left,
            )
        )

    async def count_voicemail_attempts(self, investor_id: uuid.UUID) -> int:
        """Count calls with voicemail_detected=True for this investor."""
        result = await self.session.execute(
            select(func.count())
            .select_from(CallSession)
            .where(CallSession.investor_id == investor_id)
            .where(CallSession.voicemail_detected.is_(True))
        )
        return result.scalar_one()

    async def create_voicemail_retry(
        self,
        investor_id: uuid.UUID,
        original_call_id: uuid.UUID,
        retry_at: datetime,
    ) -> CallbackRequest:
        """Create a CallbackRequest for a voicemail retry."""
        callback = CallbackRequest(
            id=uuid.uuid4(),
            investor_id=investor_id,
            call_session_id=original_call_id,
            requested_datetime_raw="voicemail_retry",
            requested_datetime=retry_at,
            notes="Auto-scheduled voicemail retry",
            status="pending",
        )
        self.session.add(callback)
        await self.session.flush()
        return callback

    async def get_due_voicemail_retries(
        self, grace_window_minutes: int = 2
    ) -> Sequence[CallbackRequest]:
        """Get voicemail retries that are due."""
        cutoff = datetime.now(timezone.utc) + timedelta(minutes=grace_window_minutes)
        query = (
            select(CallbackRequest)
            .where(CallbackRequest.status == "pending")
            .where(CallbackRequest.requested_datetime_raw == "voicemail_retry")
            .where(CallbackRequest.requested_datetime.isnot(None))
            .where(CallbackRequest.requested_datetime <= cutoff)
            .order_by(CallbackRequest.requested_datetime.asc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()
