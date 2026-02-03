"""Retail asset-type models."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class RetailDetails(Base, UUIDMixin, TimestampMixin):
    """Property metrics for retail. 1:1 with deals."""

    __tablename__ = "retail_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    gla: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    anchor_pct_gla: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    inline_tenant_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_inline_rent_psf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    cam_rate_psf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    percentage_rent_tenants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    traffic_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sales_psf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    parking_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    pad_sites: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    outparcels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    grocery_anchored: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    nnn_vs_gross: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    below_market_leases: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="retail_details")


class RetailTenant(Base, UUIDMixin, TimestampMixin):
    """Tenant rent roll for retail. 1:N with deals."""

    __tablename__ = "retail_tenants"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annual_rent: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    rent_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    lease_expiration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    renewal_options: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    percentage_rent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sales_psf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    co_tenancy_clause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="retail_tenants")
