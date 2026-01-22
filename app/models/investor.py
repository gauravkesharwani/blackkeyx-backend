"""
Investor models - maps to LeadWithDetails from frontend types/lead.ts

Frontend type:
interface LeadWithDetails {
  id: string
  phone: string
  timeline: string
  capitalAvailable: number
  investmentPreferences: string[]
  investmentThesis?: string
  riskTolerance?: string
  stage: PipelineStage
  leadScore: number
  source: string
  createdAt: string
  updatedAt: string
  calls: CallRecord[]
  matches: DealMatch[]
  notes: LeadNote[]
  stageHistory: StageChange[]
  qualification?: InvestorQualification
}
"""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.consent import Consent, LeadNote, StageHistory
    from app.models.embeddings import InvestorEmbedding
    from app.models.matching import DealMatch
    from app.models.voice import CallbackRequest, CallSession


class InvestorProfile(Base, UUIDMixin, TimestampMixin):
    """
    Core investor/lead record.
    Maps to LeadWithDetails from frontend.
    """

    __tablename__ = "investor_profiles"

    # Basic contact info
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Investment profile (from chatbot or phone agent)
    timeline: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    capital_available: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investment_preferences: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    investment_thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_tolerance: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Pipeline tracking
    # PipelineStage: new_lead, call_dispatched, call_completed, insights_extracted,
    #                deals_matched, under_review, closed
    stage: Mapped[str] = mapped_column(String(50), default="new_lead", nullable=False)
    lead_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="web", nullable=False)

    # Qualification from chatbot (InvestorQualification)
    # investor_type: 'hnw' | 'family_office' | 'other:...'
    investor_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # capacity: '$100K-$250K' | '$250K-$500K' | '$500K-$1M' | '$1M+' | 'other:...'
    capacity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # fit: 'high_priority' | 'medium_priority' | 'open_to_exploring' | 'not_a_focus' | 'other:...'
    fit: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # process: 'toe_in' | 'meaningful_first' | 'full_commitment' | 'other:...'
    process: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # timing: 'actively_deploying' | 'possibly_evaluating' | 'just_researching' | 'other:...'
    timing: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # bucket: 'active_intro' | 'nurture' | 'not_qualified'
    qualification_bucket: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    qualification_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    calls: Mapped[List["CallSession"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    matches: Mapped[List["DealMatch"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    notes: Mapped[List["LeadNote"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LeadNote.created_at.desc()",
    )
    stage_history: Mapped[List["StageHistory"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="StageHistory.changed_at.desc()",
    )
    consents: Mapped[List["Consent"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    callback_requests: Mapped[List["CallbackRequest"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CallbackRequest.created_at.desc()",
    )

    # NEW: Investor preferences (detailed from phone discovery)
    preferences: Mapped[Optional["InvestorPreferences"]] = relationship(
        back_populates="investor",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # NEW: Embeddings for semantic matching
    embeddings: Mapped[List["InvestorEmbedding"]] = relationship(
        back_populates="investor",
        cascade="all, delete-orphan",
        lazy="noload",  # Don't load by default (expensive)
    )


class InvestorPreferences(Base, UUIDMixin, TimestampMixin):
    """
    Detailed investor preferences gathered from phone discovery calls.
    One-to-one relationship with InvestorProfile.

    This captures more detailed preferences than the basic InvestorProfile fields,
    enabling more sophisticated matching.
    """

    __tablename__ = "investor_preferences"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Property type preferences
    property_types: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )

    # Geographic preferences
    preferred_markets: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    excluded_markets: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )

    # Return expectations
    target_irr_min: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    target_irr_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Risk profile
    # 'conservative' | 'moderate' | 'aggressive'
    risk_tolerance_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Investment strategy preferences
    # 'core' | 'core_plus' | 'value_add' | 'opportunistic'
    investment_strategy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Hold period preferences (years)
    hold_period_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hold_period_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Experience level
    # 'first_time' | 'some_experience' | 'experienced' | 'sophisticated'
    investment_experience: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Specific concerns or requirements (free text)
    specific_concerns: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Deal structure preferences
    preferred_structures: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="preferences")
