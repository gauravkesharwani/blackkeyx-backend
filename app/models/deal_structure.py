"""Deal structure models - sponsor fees, waterfall structure, and reserves."""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class SponsorFees(Base, UUIDMixin, TimestampMixin):
    """Sponsor fee structure. 1:1 with deals."""

    __tablename__ = "sponsor_fees"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    acquisition_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    acquisition_fee_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    asset_management_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    property_management_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    construction_supervision_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    disposition_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    guarantee_fee_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="sponsor_fees")


class WaterfallStructure(Base, UUIDMixin, TimestampMixin):
    """Distribution waterfall and promote structure. 1:1 with deals."""

    __tablename__ = "waterfall_structure"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    preferred_return_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    promote_tier_1_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    promote_tier_1_hurdle: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    promote_tier_2_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    promote_tier_2_hurdle: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sponsor_coinvest_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    sponsor_coinvest_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="waterfall_structure")


class Reserve(Base, UUIDMixin, TimestampMixin):
    """Lender reserves and escrows. 1:N with deals."""

    __tablename__ = "reserves"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reserve_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reserve_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    reserve_purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    release_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lender_controlled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="reserves")
