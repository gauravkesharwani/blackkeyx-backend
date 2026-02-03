"""DealMatch model - matches investors to deals."""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile
    from app.models.property import Deal


class DealMatch(Base, UUIDMixin):
    """Match between an investor and a deal."""

    __tablename__ = "deal_matches"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )

    similarity_score: Mapped[float] = mapped_column(
        Numeric(5, 4), default=0.0, nullable=False
    )
    match_reasons: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    hard_filter_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    soft_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    semantic_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    final_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    concerns: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    score_breakdown: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    presented_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    investor_response: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    investor: Mapped["InvestorProfile"] = relationship(back_populates="matches")
    matched_property: Mapped["Deal"] = relationship(back_populates="matches")

    @property
    def deal_memo_id(self) -> str:
        return str(self.property_id)

    @property
    def deal_name(self) -> str:
        return self.matched_property.name if self.matched_property else ""
