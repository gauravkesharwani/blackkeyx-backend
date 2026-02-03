"""
Financial models for investor brief data extraction.

These models store structured financial data extracted from investor briefs:
- InvestmentMetrics: IRR, cap rates, equity multiples
- Financing: Loan details, LTV, terms
- AnnualProjection: Year-by-year financial projections
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Deal


class InvestmentMetrics(Base, UUIDMixin, TimestampMixin):
    """Investment metrics extracted from investor briefs. 1:1 with Deal."""

    __tablename__ = "investment_metrics"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    target_irr_min: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    target_irr_max: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    target_equity_multiple: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    target_cash_on_cash: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    cap_rate_going_in: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    cap_rate_exit: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    preferred_return: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # New fields from schema redesign
    return_from_cash_flow_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    return_from_sale_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    return_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    property: Mapped["Deal"] = relationship(back_populates="investment_metrics")


class Financing(Base, UUIDMixin, TimestampMixin):
    """Financing details extracted from investor briefs. 1:1 with Deal."""

    __tablename__ = "financing"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    loan_amount: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    ltv_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    interest_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    loan_term_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amortization_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    lender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    loan_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    property: Mapped["Deal"] = relationship(back_populates="financing")


class AnnualProjection(Base, UUIDMixin, TimestampMixin):
    """Year-by-year financial projections. 1:N with Deal."""

    __tablename__ = "annual_projections"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_revenue: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    effective_gross_income: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    operating_expenses: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    noi: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # New fields from schema redesign
    cash_on_cash_return: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    irr_through_year: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    property: Mapped["Deal"] = relationship(back_populates="annual_projections")
