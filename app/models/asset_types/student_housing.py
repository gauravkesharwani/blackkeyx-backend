"""Student housing asset-type models."""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class StudentHousingDetails(Base, UUIDMixin, TimestampMixin):
    """Property metrics for student housing. 1:1 with deals."""

    __tablename__ = "student_housing_details"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    total_beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_units: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    beds_per_unit_avg: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    rent_per_bed: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    rent_per_unit: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    distance_to_campus: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    affiliated_university: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    university_enrollment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preleasing_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    preleasing_velocity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    furnished: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    utilities_included: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    individual_leases: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    on_campus_competition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="student_housing_details")
