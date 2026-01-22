"""
Market analysis model for investor brief data extraction.

Stores market and submarket data extracted from investor briefs:
- Market name and submarket
- Demographics (population growth)
- Employment drivers
- Market vacancy and rent growth
- Comparable sales data
"""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Property


class MarketAnalysis(Base, UUIDMixin, TimestampMixin):
    """
    Market analysis data extracted from investor briefs.
    One-to-one relationship with Property.
    """

    __tablename__ = "market_analysis"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Market identification
    market_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submarket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Demographics
    population_growth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Employment
    employment_drivers: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )

    # Market metrics
    market_vacancy_rate: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    market_rent_growth: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Comparables
    comparable_sales: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="market_analysis")
