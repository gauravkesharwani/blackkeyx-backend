"""Mixed-use asset-type models."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class MixedUseDetails(Base, UUIDMixin, TimestampMixin):
    """Component breakdown for mixed-use. 1:1 with deals."""

    __tablename__ = "mixed_use_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    component_types: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    retail_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    office_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    residential_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    parking_structure: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    shared_amenities: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    master_lease: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    ground_floor_use: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    synergy_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="mixed_use_details")


class MixedUseComponent(Base, UUIDMixin, TimestampMixin):
    """Individual component metrics for mixed-use. 1:N with deals."""

    __tablename__ = "mixed_use_components"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    component_type: Mapped[str] = mapped_column(String(50), nullable=False)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    noi: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    occupancy: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="mixed_use_components")
