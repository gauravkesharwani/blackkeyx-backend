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

    # Nested objects
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

    # Extraction metadata
    confidence_score: float = Field(
        ..., description="Confidence score 0-1 for extraction quality"
    )
    extraction_notes: Optional[str] = Field(
        None, description="Notes about extraction issues or uncertainties"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "deal_name": "Barber Greene Industrial Portfolio",
                "property_type": "industrial",
                "deal_structure": "LP/GP",
                "executive_summary": "Acquisition of a 500,000 SF industrial portfolio...",
                "investment_thesis": "Strong fundamentals with value-add opportunity...",
                "value_add_strategy": "Mark-to-market rents and operational improvements...",
                "total_capitalization": 45000000,
                "equity_required": 15000000,
                "minimum_investment": 100000,
                "hold_period_years": "5-7 years",
                "risk_factors": ["Market risk", "Interest rate risk"],
                "ideal_investor_profile": "Accredited investors seeking stable cash flow",
                "sponsor_name": "ABC Capital Partners",
                "sponsor_track_record": "15+ years experience, $2B deployed",
                "property_details": {
                    "address": "123 Industrial Way",
                    "city": "Chicago",
                    "state": "IL",
                    "zip_code": "60601",
                    "total_square_feet": 500000,
                },
                "investment_metrics": {
                    "target_irr_min": 15.0,
                    "target_irr_max": 20.0,
                    "target_equity_multiple": 1.8,
                    "cap_rate_going_in": 6.5,
                    "preferred_return": 8.0,
                },
                "financing": {
                    "loan_amount": 30000000,
                    "ltv_ratio": 65.0,
                    "interest_rate": 5.5,
                    "loan_term_years": 5,
                },
                "major_tenants": [
                    {
                        "tenant_name": "Amazon",
                        "square_feet": 200000,
                        "annual_rent": 1600000,
                        "lease_expiration": "2028",
                        "tenant_type": "national",
                    }
                ],
                "market_analysis": {
                    "market_name": "Chicago",
                    "submarket": "O'Hare",
                    "employment_drivers": ["E-commerce", "Manufacturing"],
                    "market_vacancy_rate": 4.5,
                },
                "confidence_score": 0.92,
                "extraction_notes": None,
            }
        }
