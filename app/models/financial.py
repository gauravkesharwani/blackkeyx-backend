"""
Financial models for investor brief data extraction.

These models store structured financial data extracted from investor briefs:
- InvestmentMetrics: IRR, cap rates, equity multiples
- Financing: Loan details, LTV, terms
- Tenant: Major tenant rent roll data
- AnnualProjection: Year-by-year financial projections
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.property import Property


class InvestmentMetrics(Base, UUIDMixin, TimestampMixin):
    """
    Investment metrics extracted from investor briefs.
    One-to-one relationship with Property.
    """

    __tablename__ = "investment_metrics"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Return targets
    target_irr_min: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    target_irr_max: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    target_equity_multiple: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    target_cash_on_cash: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Cap rates
    cap_rate_going_in: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    cap_rate_exit: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Returns structure
    preferred_return: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="investment_metrics")


class Financing(Base, UUIDMixin, TimestampMixin):
    """
    Financing details extracted from investor briefs.
    One-to-one relationship with Property.
    """

    __tablename__ = "financing"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Loan details
    loan_amount: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    ltv_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    interest_rate: Mapped[Optional[float]] = mapped_column(Numeric(5, 3), nullable=True)
    loan_term_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    amortization_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Lender info
    lender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    loan_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="financing")


class Tenant(Base, UUIDMixin, TimestampMixin):
    """
    Major tenant information extracted from investor briefs.
    One-to-many relationship with Property.
    """

    __tablename__ = "tenants"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Tenant details
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annual_rent: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    lease_expiration: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tenant_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="tenants")


class AnnualProjection(Base, UUIDMixin, TimestampMixin):
    """
    Year-by-year financial projections extracted from investor briefs.
    One-to-many relationship with Property.
    """

    __tablename__ = "annual_projections"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Year indicator
    year: Mapped[int] = mapped_column(Integer, nullable=False)

    # Income
    gross_revenue: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    effective_gross_income: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Expenses
    operating_expenses: Mapped[Optional[float]] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # Net operating income
    noi: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # Cash flow
    cash_flow: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="annual_projections")
