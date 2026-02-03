"""Industrial asset-type models."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class IndustrialDetails(Base, UUIDMixin, TimestampMixin):
    """Building specs for industrial properties. 1:1 with deals."""

    __tablename__ = "industrial_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    clear_height_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clear_height_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    loading_docks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    drive_in_doors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dock_height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    truck_court_depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_spacing: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rail_access: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    power_amps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    power_voltage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crane_capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sprinkler_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    office_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    trailer_parking: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cross_dock: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    freezer_cooler_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="industrial_details")


class IndustrialTenant(Base, UUIDMixin, TimestampMixin):
    """Tenant rent roll for industrial properties. 1:N with deals."""

    __tablename__ = "industrial_tenants"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annual_rent: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    rent_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    lease_start: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    lease_expiration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    renewal_options: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    renewal_option_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credit_rating: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    years_at_location: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_mission_critical: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    distance_from_hq: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tenant_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="industrial_tenants")
