"""
Property/Deal schemas for API responses.

Maps to frontend types/deal.ts:
- DealMemo
- DealMemoExtraction
- DealUploadResponse
- DealExtractionResponse
- DealListResponse
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer


class DealMemoResponse(BaseModel):
    """
    Deal memo response.

    Maps to DealMemo from frontend:
    interface DealMemo {
      id: string
      name: string
      dealType: string
      summary: string
      thesis: string
      minimumInvestment: number
      targetReturn: string
      riskFactors: string[]
      idealInvestorProfile: string
      structure: string
      timeline: string
      status: 'active' | 'closed' | 'paused'
      createdAt: string
      updatedAt: string
    }
    """

    id: str
    name: str
    dealType: str = Field(..., alias="deal_type")
    summary: Optional[str] = None
    thesis: Optional[str] = None
    minimumInvestment: Optional[int] = Field(None, alias="minimum_investment")
    targetReturn: Optional[str] = Field(None, alias="target_return")
    riskFactors: List[str] = Field(default_factory=list, alias="risk_factors")
    idealInvestorProfile: Optional[str] = Field(None, alias="ideal_investor_profile")
    structure: Optional[str] = None
    timeline: Optional[str] = None
    status: str
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: datetime = Field(..., alias="updated_at")

    @field_serializer("createdAt", "updatedAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    class Config:
        populate_by_name = True
        from_attributes = True


class DealMemoExtraction(BaseModel):
    """
    AI extraction result from document.

    Maps to DealMemoExtraction from frontend:
    interface DealMemoExtraction {
      name: string
      dealType: string
      summary: string
      thesis: string
      minimumInvestment: number
      targetReturn: string
      riskFactors: string[]
      idealInvestorProfile: string
      structure: string
      timeline: string
      confidence: number
      rawText: string
    }
    """

    name: str
    dealType: str = Field(..., alias="deal_type")
    summary: str
    thesis: str
    minimumInvestment: int = Field(..., alias="minimum_investment")
    targetReturn: str = Field(..., alias="target_return")
    riskFactors: List[str] = Field(..., alias="risk_factors")
    idealInvestorProfile: str = Field(..., alias="ideal_investor_profile")
    structure: str
    timeline: str
    confidence: float
    rawText: str = Field(..., alias="raw_text")

    class Config:
        populate_by_name = True


class DealUploadResponse(BaseModel):
    """
    Upload response.

    Maps to DealUploadResponse from frontend:
    interface DealUploadResponse {
      uploadId: string
      filename: string
      status: 'uploaded' | 'processing' | 'error'
    }
    """

    uploadId: str
    filename: str
    status: str


class DealDocumentDownloadResponse(BaseModel):
    """
    Document download response with presigned URL.

    Maps to DealDocumentDownloadResponse from frontend:
    interface DealDocumentDownloadResponse {
      downloadUrl: string
      filename: string
      expiresIn: number
    }
    """

    downloadUrl: str
    filename: str
    expiresIn: int = Field(description="URL expiration time in seconds")


class DealExtractionResponse(BaseModel):
    """
    Extraction response.

    Maps to DealExtractionResponse from frontend:
    interface DealExtractionResponse {
      extraction: DealMemoExtraction
      rawText: string
    }
    """

    extraction: DealMemoExtraction
    rawText: str = Field(..., alias="raw_text")

    class Config:
        populate_by_name = True


class DealListResponse(BaseModel):
    """
    Deal list response.

    Maps to DealListResponse from frontend:
    interface DealListResponse {
      deals: DealMemo[]
      total: number
    }
    """

    deals: List[DealMemoResponse]
    total: int


class DealCreateRequest(BaseModel):
    """Request to create a new deal from extraction."""

    name: str
    dealType: str = Field(..., alias="deal_type")
    summary: Optional[str] = None
    thesis: Optional[str] = None
    minimumInvestment: Optional[int] = Field(None, alias="minimum_investment")
    targetReturn: Optional[str] = Field(None, alias="target_return")
    riskFactors: List[str] = Field(default_factory=list, alias="risk_factors")
    idealInvestorProfile: Optional[str] = Field(None, alias="ideal_investor_profile")
    structure: Optional[str] = None
    timeline: Optional[str] = None

    class Config:
        populate_by_name = True


class DealUpdateRequest(BaseModel):
    """Request to update an existing deal."""

    name: Optional[str] = None
    dealType: Optional[str] = Field(None, alias="deal_type")
    summary: Optional[str] = None
    thesis: Optional[str] = None
    minimumInvestment: Optional[int] = Field(None, alias="minimum_investment")
    targetReturn: Optional[str] = Field(None, alias="target_return")
    riskFactors: Optional[List[str]] = Field(None, alias="risk_factors")
    idealInvestorProfile: Optional[str] = Field(None, alias="ideal_investor_profile")
    structure: Optional[str] = None
    timeline: Optional[str] = None
    status: Optional[str] = None

    class Config:
        populate_by_name = True


# ============================================
# Full Extraction Response Schemas
# Maps to frontend InvestorBriefExtraction
# ============================================


class PropertyDetailsResponse(BaseModel):
    """Property location and physical details."""

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = Field(None, alias="zip_code")
    totalSquareFeet: Optional[int] = Field(None, alias="total_square_feet")
    yearBuilt: Optional[int] = Field(None, alias="year_built")
    yearRenovated: Optional[int] = Field(None, alias="year_renovated")
    parkingSpaces: Optional[int] = Field(None, alias="parking_spaces")

    class Config:
        populate_by_name = True


class InvestmentMetricsResponse(BaseModel):
    """Investment return targets and metrics."""

    targetIrrMin: Optional[float] = Field(None, alias="target_irr_min")
    targetIrrMax: Optional[float] = Field(None, alias="target_irr_max")
    targetEquityMultiple: Optional[float] = Field(None, alias="target_equity_multiple")
    targetCashOnCash: Optional[float] = Field(None, alias="target_cash_on_cash")
    capRateGoingIn: Optional[float] = Field(None, alias="cap_rate_going_in")
    capRateExit: Optional[float] = Field(None, alias="cap_rate_exit")
    preferredReturn: Optional[float] = Field(None, alias="preferred_return")

    class Config:
        populate_by_name = True


class FinancingResponse(BaseModel):
    """Loan and financing details."""

    loanAmount: Optional[float] = Field(None, alias="loan_amount")
    ltvRatio: Optional[float] = Field(None, alias="ltv_ratio")
    interestRate: Optional[float] = Field(None, alias="interest_rate")
    loanTermYears: Optional[int] = Field(None, alias="loan_term_years")
    amortizationYears: Optional[int] = Field(None, alias="amortization_years")
    lenderName: Optional[str] = Field(None, alias="lender_name")
    loanType: Optional[str] = Field(None, alias="loan_type")

    class Config:
        populate_by_name = True


class TenantResponse(BaseModel):
    """Major tenant information."""

    tenantName: str = Field(..., alias="tenant_name")
    squareFeet: Optional[int] = Field(None, alias="square_feet")
    annualRent: Optional[float] = Field(None, alias="annual_rent")
    leaseExpiration: Optional[str] = Field(None, alias="lease_expiration")
    tenantType: Optional[str] = Field(None, alias="tenant_type")

    class Config:
        populate_by_name = True


class MarketAnalysisResponse(BaseModel):
    """Market analysis data."""

    marketName: Optional[str] = Field(None, alias="market_name")
    submarket: Optional[str] = None
    populationGrowth: Optional[str] = Field(None, alias="population_growth")
    employmentDrivers: List[str] = Field(default_factory=list, alias="employment_drivers")
    marketVacancyRate: Optional[float] = Field(None, alias="market_vacancy_rate")
    marketRentGrowth: Optional[str] = Field(None, alias="market_rent_growth")
    comparableSales: Optional[str] = Field(None, alias="comparable_sales")

    class Config:
        populate_by_name = True


class AnnualProjectionResponse(BaseModel):
    """Year-by-year financial projection."""

    year: int
    grossRevenue: Optional[float] = Field(None, alias="gross_revenue")
    effectiveGrossIncome: Optional[float] = Field(None, alias="effective_gross_income")
    operatingExpenses: Optional[float] = Field(None, alias="operating_expenses")
    noi: Optional[float] = None
    cashFlow: Optional[float] = Field(None, alias="cash_flow")

    class Config:
        populate_by_name = True


class FullExtractionResponse(BaseModel):
    """
    Full extraction response with all investor brief data.

    Maps to frontend InvestorBriefExtraction interface.
    """

    # Core deal information
    dealName: str = Field(..., alias="deal_name")
    propertyType: str = Field(..., alias="property_type")
    dealStructure: Optional[str] = Field(None, alias="deal_structure")

    # Narratives
    executiveSummary: Optional[str] = Field(None, alias="executive_summary")
    investmentThesis: Optional[str] = Field(None, alias="investment_thesis")
    valueAddStrategy: Optional[str] = Field(None, alias="value_add_strategy")

    # Financials
    totalCapitalization: Optional[float] = Field(None, alias="total_capitalization")
    equityRequired: Optional[float] = Field(None, alias="equity_required")
    minimumInvestment: Optional[int] = Field(None, alias="minimum_investment")
    holdPeriodYears: Optional[str] = Field(None, alias="hold_period_years")

    # Risk and fit
    riskFactors: List[str] = Field(default_factory=list, alias="risk_factors")
    idealInvestorProfile: Optional[str] = Field(None, alias="ideal_investor_profile")

    # Sponsor
    sponsorName: Optional[str] = Field(None, alias="sponsor_name")
    sponsorTrackRecord: Optional[str] = Field(None, alias="sponsor_track_record")

    # Nested objects
    propertyDetails: Optional[PropertyDetailsResponse] = Field(None, alias="property_details")
    investmentMetrics: Optional[InvestmentMetricsResponse] = Field(None, alias="investment_metrics")
    financing: Optional[FinancingResponse] = None
    majorTenants: List[TenantResponse] = Field(default_factory=list, alias="major_tenants")
    marketAnalysis: Optional[MarketAnalysisResponse] = Field(None, alias="market_analysis")
    annualProjections: List[AnnualProjectionResponse] = Field(default_factory=list, alias="annual_projections")

    # Extraction metadata
    confidenceScore: float = Field(..., alias="confidence_score")
    extractionNotes: Optional[str] = Field(None, alias="extraction_notes")

    # Upload reference for saving
    uploadId: str = Field(..., alias="upload_id")

    class Config:
        populate_by_name = True


class FullExtractionResponseWrapper(BaseModel):
    """Wrapper for full extraction response."""

    extraction: FullExtractionResponse
    legacyExtraction: DealMemoExtraction = Field(..., alias="legacy_extraction")

    class Config:
        populate_by_name = True


class FullDealResponse(BaseModel):
    """
    Full deal response with all related data.

    Used for viewing saved deal details including all financial,
    tenant, projection, and market data.
    """

    # Core deal information (from DealMemoResponse)
    id: str
    name: str
    dealType: str = Field(..., alias="deal_type")
    summary: Optional[str] = None
    thesis: Optional[str] = None
    minimumInvestment: Optional[int] = Field(None, alias="minimum_investment")
    targetReturn: Optional[str] = Field(None, alias="target_return")
    riskFactors: List[str] = Field(default_factory=list, alias="risk_factors")
    idealInvestorProfile: Optional[str] = Field(None, alias="ideal_investor_profile")
    structure: Optional[str] = None
    timeline: Optional[str] = None
    status: str
    createdAt: datetime = Field(..., alias="created_at")
    updatedAt: datetime = Field(..., alias="updated_at")

    # Extended fields from Property model
    valueAddStrategy: Optional[str] = Field(None, alias="value_add_strategy")
    totalCapitalization: Optional[float] = Field(None, alias="total_capitalization")
    sponsorName: Optional[str] = Field(None, alias="sponsor_name")
    sponsorTrackRecord: Optional[str] = Field(None, alias="sponsor_track_record")
    extractionConfidence: Optional[float] = Field(None, alias="extraction_confidence")
    extractionNotes: Optional[str] = Field(None, alias="extraction_notes")

    # Property details (from Property and PropertyFeature)
    propertyDetails: Optional[PropertyDetailsResponse] = Field(None, alias="property_details")

    # Nested related data
    investmentMetrics: Optional[InvestmentMetricsResponse] = Field(None, alias="investment_metrics")
    financing: Optional[FinancingResponse] = None
    majorTenants: List[TenantResponse] = Field(default_factory=list, alias="major_tenants")
    marketAnalysis: Optional[MarketAnalysisResponse] = Field(None, alias="market_analysis")
    annualProjections: List[AnnualProjectionResponse] = Field(default_factory=list, alias="annual_projections")

    @field_serializer("createdAt", "updatedAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    class Config:
        populate_by_name = True
        from_attributes = True
