"""Land asset-type models."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class LandDetails(Base, UUIDMixin, TimestampMixin):
    """Entitlements and development info for land. 1:1 with deals."""

    __tablename__ = "land_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    acreage: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    zoning: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entitled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    entitlement_status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_density: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    approved_use: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    topography: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    utilities_available: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    environmental_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    flood_zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    development_timeline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comparable_land_sales: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    impact_fees: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    infrastructure_costs: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    absorption_projection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="land_details")
