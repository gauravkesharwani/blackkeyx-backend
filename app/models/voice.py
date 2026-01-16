"""
Voice/Call models - maps to CallRecord from frontend types/lead.ts

Frontend type:
interface CallRecord {
  id: string
  status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed'
  duration?: number
  transcript?: string
  recordingUrl?: string
  initiatedAt: string
  completedAt?: string
}
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
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
      status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed'
      duration?: number
      transcript?: string
      recordingUrl?: string
      initiatedAt: string
      completedAt?: string
    }
    """

    __tablename__ = "call_sessions"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Call status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed'
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

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="calls")


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
