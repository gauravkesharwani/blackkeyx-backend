"""
Enhanced extraction schemas for investor brief PDF processing.

These schemas define the structured output format for AI extraction
from investor brief PDFs. They match the database schema for storage.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PropertyDetailsExtraction(BaseModel):
    """Property location and physical details."""

    address: Optional[str] = Field(None, description="Street address of the property")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State abbreviation (e.g., IL, TX)")
    zip_code: Optional[str] = Field(None, description="ZIP code")
    total_square_feet: Optional[int] = Field(
        None, description="Total building square footage"
    )
    year_built: Optional[int] = Field(None, description="Year the property was built")
    year_renovated: Optional[int] = Field(
        None, description="Most recent renovation year"
    )
    parking_spaces: Optional[int] = Field(None, description="Number of parking spaces")


class InvestmentMetricsExtraction(BaseModel):
    """Investment return targets and metrics."""

    target_irr_min: Optional[float] = Field(
        None, description="Minimum target IRR percentage (e.g., 15.0 for 15%)"
    )
    target_irr_max: Optional[float] = Field(
        None, description="Maximum target IRR percentage (e.g., 20.0 for 20%)"
    )
    target_equity_multiple: Optional[float] = Field(
        None, description="Target equity multiple (e.g., 1.8 for 1.8x)"
    )
    target_cash_on_cash: Optional[float] = Field(
        None, description="Target cash-on-cash return percentage"
    )
    cap_rate_going_in: Optional[float] = Field(
        None, description="Going-in cap rate percentage"
    )
    cap_rate_exit: Optional[float] = Field(
        None, description="Projected exit cap rate percentage"
    )
    preferred_return: Optional[float] = Field(
        None, description="Preferred return percentage (e.g., 8.0 for 8%)"
    )
    return_from_cash_flow_pct: Optional[float] = Field(
        None, description="Percentage of total return from cash flow"
    )
    return_from_sale_pct: Optional[float] = Field(
        None, description="Percentage of total return from sale/reversion"
    )
    return_profile: Optional[str] = Field(
        None, description="Return profile category (e.g., 'cash-flow-heavy', 'appreciation', 'balanced')"
    )


class FinancingExtraction(BaseModel):
    """Loan and financing details."""

    loan_amount: Optional[float] = Field(None, description="Total loan amount in USD")
    ltv_ratio: Optional[float] = Field(
        None, description="Loan-to-value ratio percentage"
    )
    interest_rate: Optional[float] = Field(
        None, description="Interest rate percentage"
    )
    loan_term_years: Optional[int] = Field(None, description="Loan term in years")
    amortization_years: Optional[int] = Field(
        None, description="Amortization period in years"
    )
    lender_name: Optional[str] = Field(None, description="Name of the lender")
    loan_type: Optional[str] = Field(
        None,
        description="Type of loan (e.g., fixed-rate, floating, bridge, permanent)",
    )


class TenantExtraction(BaseModel):
    """Major tenant information from rent roll."""

    tenant_name: str = Field(..., description="Name of the tenant")
    square_feet: Optional[int] = Field(None, description="Leased square footage")
    annual_rent: Optional[float] = Field(None, description="Annual rent in USD")
    lease_expiration: Optional[str] = Field(
        None, description="Lease expiration date or term"
    )
    tenant_type: Optional[str] = Field(
        None, description="Tenant type (e.g., national, regional, local)"
    )


class MarketAnalysisExtraction(BaseModel):
    """Market and submarket analysis data."""

    market_name: Optional[str] = Field(None, description="Primary market name")
    submarket: Optional[str] = Field(None, description="Submarket name")
    population_growth: Optional[str] = Field(
        None, description="Population growth statistics or trends"
    )
    employment_drivers: List[str] = Field(
        default_factory=list, description="Major employment drivers in the market"
    )
    market_vacancy_rate: Optional[float] = Field(
        None, description="Market vacancy rate percentage"
    )
    market_rent_growth: Optional[str] = Field(
        None, description="Market rent growth statistics or trends"
    )
    comparable_sales: Optional[str] = Field(
        None, description="Recent comparable sales information"
    )
    new_construction_pct: Optional[float] = Field(
        None, description="New construction as percentage of existing inventory"
    )
    absorption_rate: Optional[float] = Field(
        None, description="Net absorption rate (square feet or units)"
    )
    landlord_pricing_power: Optional[str] = Field(
        None, description="Landlord pricing power assessment (e.g., 'strong', 'moderate', 'weak')"
    )


class AnnualProjectionExtraction(BaseModel):
    """Year-by-year financial projection."""

    year: int = Field(..., description="Projection year (1, 2, 3, etc.)")
    gross_revenue: Optional[float] = Field(None, description="Gross revenue in USD")
    effective_gross_income: Optional[float] = Field(
        None, description="Effective gross income in USD"
    )
    operating_expenses: Optional[float] = Field(
        None, description="Operating expenses in USD"
    )
    noi: Optional[float] = Field(None, description="Net operating income in USD")
    cash_flow: Optional[float] = Field(None, description="Cash flow in USD")
    cash_on_cash_return: Optional[float] = Field(
        None, description="Cash-on-cash return percentage for this year"
    )
    irr_through_year: Optional[float] = Field(
        None, description="Cumulative IRR through this year"
    )


# ========================================
# New: Sponsor Fees & Waterfall Extraction
# ========================================


class SponsorFeesExtraction(BaseModel):
    """Sponsor fee structure extracted from investor brief."""

    acquisition_fee_pct: Optional[float] = Field(
        None, description="Acquisition fee percentage"
    )
    acquisition_fee_amount: Optional[float] = Field(
        None, description="Acquisition fee flat amount in USD"
    )
    asset_management_fee_pct: Optional[float] = Field(
        None, description="Asset management fee percentage"
    )
    property_management_fee_pct: Optional[float] = Field(
        None, description="Property management fee percentage"
    )
    construction_supervision_fee_pct: Optional[float] = Field(
        None, description="Construction supervision fee percentage"
    )
    disposition_fee_pct: Optional[float] = Field(
        None, description="Disposition fee percentage"
    )
    guarantee_fee_pct: Optional[float] = Field(
        None, description="Guarantee fee percentage"
    )


class WaterfallStructureExtraction(BaseModel):
    """Waterfall / promote structure extracted from investor brief."""

    preferred_return_pct: Optional[float] = Field(
        None, description="Preferred return percentage"
    )
    promote_tier_1_pct: Optional[float] = Field(
        None, description="Tier 1 promote percentage to sponsor"
    )
    promote_tier_1_hurdle: Optional[float] = Field(
        None, description="Tier 1 IRR hurdle percentage"
    )
    promote_tier_2_pct: Optional[float] = Field(
        None, description="Tier 2 promote percentage to sponsor"
    )
    promote_tier_2_hurdle: Optional[float] = Field(
        None, description="Tier 2 IRR hurdle percentage"
    )
    sponsor_coinvest_pct: Optional[float] = Field(
        None, description="Sponsor co-investment percentage"
    )
    sponsor_coinvest_amount: Optional[float] = Field(
        None, description="Sponsor co-investment dollar amount"
    )


class ReserveExtraction(BaseModel):
    """Reserve account extracted from investor brief."""

    reserve_type: str = Field(
        ..., description="Type of reserve (e.g., 'capex', 'tenant_improvement', 'operating', 'interest')"
    )
    reserve_amount: Optional[float] = Field(
        None, description="Reserve amount in USD"
    )
    reserve_purpose: Optional[str] = Field(
        None, description="Purpose or description of the reserve"
    )
    release_conditions: Optional[str] = Field(
        None, description="Conditions under which reserves are released"
    )
    lender_controlled: Optional[bool] = Field(
        None, description="Whether the reserve is lender-controlled"
    )


class InvestorBriefExtraction(BaseModel):
    """
    Complete investor brief extraction schema.

    This is the primary output from AI extraction of investor brief PDFs.
    Maps directly to the database schema for storage.
    """

    # Core deal information
    deal_name: str = Field(..., description="Name of the deal or property")
    property_type: str = Field(
        ..., description="Property type (e.g., industrial, multifamily, office, retail)"
    )
    deal_structure: Optional[str] = Field(
        None, description="Deal structure (e.g., LP/GP, JV, REIT)"
    )

    # Narratives
    executive_summary: Optional[str] = Field(
        None, description="Executive summary of the investment opportunity"
    )
    investment_thesis: Optional[str] = Field(
        None, description="Core investment thesis and rationale"
    )
    value_add_strategy: Optional[str] = Field(
        None, description="Value-add or business plan strategy"
    )

    # Financials
    purchase_price: Optional[float] = Field(
        None, description="Purchase price in USD"
    )
    total_capitalization: Optional[float] = Field(
        None, description="Total capitalization in USD"
    )
    equity_required: Optional[float] = Field(
        None, description="Total equity required in USD"
    )
    minimum_investment: Optional[int] = Field(
        None, description="Minimum investment amount in USD"
    )
    hold_period_years: Optional[str] = Field(
        None, description="Expected hold period (e.g., '5-7 years')"
    )
    price_per_sf: Optional[float] = Field(
        None, description="Price per square foot"
    )
    replacement_cost_per_sf: Optional[float] = Field(
        None, description="Replacement cost per square foot"
    )
    discount_to_replacement_pct: Optional[float] = Field(
        None, description="Discount to replacement cost percentage"
    )

    # Risk and fit
    risk_factors: List[str] = Field(
        default_factory=list, description="Key risk factors"
    )
    ideal_investor_profile: Optional[str] = Field(
        None, description="Description of ideal investor"
    )

    # Sponsor
    sponsor_name: Optional[str] = Field(None, description="Name of the sponsor/GP")
    sponsor_track_record: Optional[str] = Field(
        None, description="Sponsor's track record and experience"
    )

    # Nested objects - common
    property_details: Optional[PropertyDetailsExtraction] = Field(
        None, description="Property location and physical details"
    )
    investment_metrics: Optional[InvestmentMetricsExtraction] = Field(
        None, description="Investment return targets"
    )
    financing: Optional[FinancingExtraction] = Field(
        None, description="Financing details"
    )
    major_tenants: List[TenantExtraction] = Field(
        default_factory=list, description="Major tenant information"
    )
    market_analysis: Optional[MarketAnalysisExtraction] = Field(
        None, description="Market analysis data"
    )
    annual_projections: List[AnnualProjectionExtraction] = Field(
        default_factory=list, description="Year-by-year projections"
    )

    # Deal structure
    sponsor_fees: Optional[SponsorFeesExtraction] = Field(
        None, description="Sponsor fee structure"
    )
    waterfall_structure: Optional[WaterfallStructureExtraction] = Field(
        None, description="Waterfall / promote structure"
    )
    reserves: List[ReserveExtraction] = Field(
        default_factory=list, description="Reserve accounts"
    )

    # Extraction metadata
    confidence_score: float = Field(
        ..., description="Confidence score 0-1 for extraction quality"
    )
    extraction_notes: Optional[str] = Field(
        None, description="Notes about extraction issues or uncertainties"
    )
