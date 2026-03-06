"""
Voice/Call models - maps to CallRecord from frontend types/lead.ts

Frontend type:
interface CallRecord {
  id: string
  status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed' | 'voicemail'
  duration?: number
  transcript?: string
  recordingUrl?: string
  initiatedAt: string
  completedAt?: string
  voicemailDetected?: boolean
  voicemailConfidence?: number
  voicemailMessageLeft?: boolean
  retryCount?: number
}
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile


class CallSession(Base, UUIDMixin):
    """
    Voice call record from LiveKit.

    Maps to CallRecord from frontend:
    interface CallRecord {
      id: string
      status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed' | 'voicemail'
      duration?: number
      transcript?: string
      recordingUrl?: string
      initiatedAt: string
      completedAt?: string
      voicemailDetected?: boolean
      voicemailConfidence?: number
      voicemailMessageLeft?: boolean
      retryCount?: number
    }
    """

    __tablename__ = "call_sessions"

    investor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for unknown inbound callers
    )

    # Call direction: 'inbound' | 'outbound'
    direction: Mapped[str] = mapped_column(
        String(20), default="outbound", server_default="outbound", nullable=False
    )

    # Caller phone (for inbound calls — the phone number that called in)
    caller_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Call status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed' | 'voicemail'
    status: Mapped[str] = mapped_column(String(50), default="initiated", nullable=False)

    # Call details
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recording_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # LiveKit room info (for tracking)
    room_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    livekit_participant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timestamps
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Voicemail detection
    voicemail_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    voicemail_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    voicemail_message_left: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Extraction status tracking
    extraction_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'pending', 'completed', 'failed'
    extraction_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )  # 0.00 - 1.00
    extraction_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationship
    investor: Mapped[Optional["InvestorProfile"]] = relationship(back_populates="calls")


class CallbackRequest(Base, UUIDMixin):
    """
    Callback request record when investor is busy and wants a follow-up call.
    Linked to the call session that generated it and the investor.
    """

    __tablename__ = "callback_requests"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    call_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Callback scheduling
    requested_datetime_raw: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Original natural language (e.g., "Tuesday at 2pm")

    requested_datetime: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Parsed datetime (may be null if unparseable)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status: pending, completed, cancelled
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    investor: Mapped["InvestorProfile"] = relationship(back_populates="callback_requests")
    call_session: Mapped["CallSession"] = relationship()


class CallTranscript(Base, UUIDMixin):
    """
    Detailed transcript storage for call sessions.
    Stores transcript segments with timestamps for detailed analysis.
    """

    __tablename__ = "call_transcripts"

    call_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("call_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Speaker identification
    speaker: Mapped[str] = mapped_column(String(50), nullable=False)  # 'agent' or 'investor'

    # Transcript content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Timing
    start_time: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # ms from start
    end_time: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    # Confidence score from STT
    confidence: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
