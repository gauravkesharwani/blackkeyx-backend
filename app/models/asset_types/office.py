"""Office asset-type models."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class OfficeDetails(Base, UUIDMixin, TimestampMixin):
    """Building specs for office. 1:1 with deals."""

    __tablename__ = "office_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    building_class: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    floor_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    typical_floor_plate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nra: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tenant_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    walt_years: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    avg_rent_psf_nnn: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    avg_rent_psf_fsg: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    ti_allowance_psf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    parking_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    building_amenities: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    leed_certification: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    energy_star_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    largest_tenant_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    near_term_expirations_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sublease_space_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="office_details")


class OfficeTenant(Base, UUIDMixin, TimestampMixin):
    """Tenant rent roll for office. 1:N with deals."""

    __tablename__ = "office_tenants"

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
    ti_allowance: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    credit_rating: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="office_tenants")
