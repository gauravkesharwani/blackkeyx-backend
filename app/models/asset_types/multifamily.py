"""Multifamily asset-type models."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class MultifamilyDetails(Base, UUIDMixin, TimestampMixin):
    """Property metrics for multifamily. 1:1 with deals."""

    __tablename__ = "multifamily_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    unit_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_unit_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_rent_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    avg_rent_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    in_place_occupancy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    market_rent_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    loss_to_lease_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    amenities: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    washer_dryer: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    vintage: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    recent_renovations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    renovation_premium: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    concessions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    turnover_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    expense_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="multifamily_details")


class MultifamilyUnitMix(Base, UUIDMixin, TimestampMixin):
    """Unit mix breakdown for multifamily. 1:N with deals."""

    __tablename__ = "multifamily_unit_mix"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_type: Mapped[str] = mapped_column(String(50), nullable=False)
    unit_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_rent: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    market_rent: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="multifamily_unit_mix")
