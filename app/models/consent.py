"""
Consent, LeadNote, and StageHistory models.

Maps to frontend types:
- LeadNote from types/lead.ts
- StageChange from types/lead.ts
- Consent for TCPA compliance
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile


class Consent(Base, UUIDMixin):
    """
    TCPA consent record.
    Stores consent given by investor for phone contact.
    """

    __tablename__ = "consents"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Consent details
    consent_text: Mapped[str] = mapped_column(Text, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="consents")


class LeadNote(Base, UUIDMixin):
    """
    Note/comment from admin on a lead.

    Maps to LeadNote from frontend:
    interface LeadNote {
      id: string
      content: string
      createdBy: string
      createdAt: string
    }
    """

    __tablename__ = "lead_notes"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="admin", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="notes")


class StageHistory(Base, UUIDMixin):
    """
    Stage transition history for a lead.

    Maps to StageChange from frontend:
    interface StageChange {
      id: string
      fromStage: PipelineStage | null
      toStage: PipelineStage
      changedBy: string
      notes?: string
      changedAt: string
    }
    """

    __tablename__ = "stage_history"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    from_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="stage_history")
