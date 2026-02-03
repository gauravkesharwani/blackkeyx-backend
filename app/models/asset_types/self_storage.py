"""Self-storage asset-type models."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class SelfStorageDetails(Base, UUIDMixin, TimestampMixin):
    """Facility metrics for self-storage. 1:1 with deals."""

    __tablename__ = "self_storage_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    total_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    net_rentable_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    climate_controlled_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    climate_controlled_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    drive_up_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_rent_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    economic_occupancy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    physical_occupancy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    management_platform: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rv_boat_parking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_length_of_stay: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    street_rate_growth: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    ecri_potential: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="self_storage_details")


class SelfStorageUnitMix(Base, UUIDMixin, TimestampMixin):
    """Unit mix by size for self-storage. 1:N with deals."""

    __tablename__ = "self_storage_unit_mix"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    unit_size: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    occupancy_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    climate_controlled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="self_storage_unit_mix")
