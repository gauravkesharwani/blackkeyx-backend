"""
DealMatch model - maps to DealMatch from frontend types/lead.ts

Frontend type:
interface DealMatch {
  id: string
  dealMemoId: string
  dealName: string
  similarityScore: number
  matchReasons: string[]
  status: 'pending' | 'presented' | 'accepted' | 'rejected'
  createdAt: string
}
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile
    from app.models.property import Property


class DealMatch(Base, UUIDMixin):
    """
    Match between an investor and a property/deal.

    Maps to DealMatch from frontend:
    interface DealMatch {
      id: string
      dealMemoId: string
      dealName: string
      similarityScore: number
      matchReasons: string[]
      status: 'pending' | 'presented' | 'accepted' | 'rejected'
      createdAt: string
    }
    """

    __tablename__ = "deal_matches"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Match scoring
    similarity_score: Mapped[float] = mapped_column(
        Numeric(5, 4), default=0.0, nullable=False
    )
    match_reasons: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )

    # Status: 'pending' | 'presented' | 'accepted' | 'rejected'
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Optional notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    investor: Mapped["InvestorProfile"] = relationship(back_populates="matches")
    matched_property: Mapped["Property"] = relationship(back_populates="matches")

    @property
    def deal_memo_id(self) -> str:
        """Alias for property_id to match frontend naming."""
        return str(self.property_id)

    @property
    def deal_name(self) -> str:
        """Get the property name for frontend compatibility."""
        return self.matched_property.name if self.matched_property else ""
