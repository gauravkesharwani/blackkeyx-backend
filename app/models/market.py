"""Market analysis model for investor brief data extraction."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class MarketAnalysis(Base, UUIDMixin, TimestampMixin):
    """Market analysis data extracted from investor briefs. 1:1 with Deal."""

    __tablename__ = "market_analysis"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    market_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submarket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    population_growth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    employment_drivers: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    market_vacancy_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    market_rent_growth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # New fields from schema redesign
    new_construction_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    absorption_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    landlord_pricing_power: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    comparable_sales: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    property: Mapped["Deal"] = relationship(back_populates="market_analysis")
