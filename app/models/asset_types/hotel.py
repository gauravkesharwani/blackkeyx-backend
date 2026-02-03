"""Hotel asset-type models."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class HotelDetails(Base, UUIDMixin, TimestampMixin):
    """Operations metrics for hotel. 1:1 with deals."""

    __tablename__ = "hotel_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    room_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_room_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    adr: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    revpar: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    occupancy_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    franchise_brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    franchise_expiration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    management_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fnb_revenue: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    fnb_revenue_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    meeting_space_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    star_rating: Mapped[Optional[float]] = mapped_column(Numeric(3, 1), nullable=True)
    trip_advisor_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 1), nullable=True)
    pip_required: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    pip_cost: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    goppar: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    comp_set_penetration: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="hotel_details")


class HotelRoomMix(Base, UUIDMixin, TimestampMixin):
    """Room type breakdown for hotel. 1:N with deals."""

    __tablename__ = "hotel_room_mix"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    room_type: Mapped[str] = mapped_column(String(50), nullable=False)
    room_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_size_sf: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="hotel_room_mix")
