"""
Properties/Deals router.

Handles:
- GET /api/v1/properties - List deals
- POST /api/v1/properties - Create deal
- GET /api/v1/properties/{id} - Get deal
- PUT /api/v1/properties/{id} - Update deal
- DELETE /api/v1/properties/{id} - Delete deal
- POST /api/v1/properties/upload - Upload document to S3
- POST /api/v1/properties/extract - Extract data from document
"""

import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from typing import Optional

from app.dependencies import get_property_service
from app.models.property import Property
from app.schemas.property import (
    AnnualProjectionResponse,
    DealCreateRequest,
    DealDocumentDownloadResponse,
    DealExtractionResponse,
    DealListResponse,
    DealMemoExtraction,
    DealMemoResponse,
    DealUpdateRequest,
    DealUploadResponse,
    FinancingResponse,
    FullDealResponse,
    FullExtractionResponse,
    FullExtractionResponseWrapper,
    InvestmentMetricsResponse,
    MarketAnalysisResponse,
    PropertyDetailsResponse,
    TenantResponse,
)
from app.services.property_service import PropertyService

router = APIRouter()


@router.get("", response_model=DealListResponse, response_model_by_alias=False)
async def list_deals(
    property_service: PropertyService = Depends(get_property_service),
    status: Optional[str] = None,
) -> DealListResponse:
    """Get list of deals."""
    deals, total = await property_service.list_deals(status=status)
    deal_responses = [_property_to_response(deal) for deal in deals]
    return DealListResponse(deals=deal_responses, total=total)


@router.post("", response_model=DealMemoResponse, response_model_by_alias=False)
async def create_deal(
    deal_data: DealCreateRequest,
    property_service: PropertyService = Depends(get_property_service),
) -> DealMemoResponse:
    """Create a new deal from extracted data."""
    property_obj = await property_service.create_deal(
        name=deal_data.name,
        deal_type=deal_data.dealType,
        summary=deal_data.summary,
        thesis=deal_data.thesis,
        minimum_investment=deal_data.minimumInvestment,
        target_return=deal_data.targetReturn,
        risk_factors=deal_data.riskFactors,
        ideal_investor_profile=deal_data.idealInvestorProfile,
        structure=deal_data.structure,
        timeline=deal_data.timeline,
    )
    return _property_to_response(property_obj)


@router.get("/{deal_id}", response_model=DealMemoResponse, response_model_by_alias=False)
async def get_deal(
    deal_id: uuid.UUID,
    property_service: PropertyService = Depends(get_property_service),
) -> DealMemoResponse:
    """Get single deal by ID."""
    deal = await property_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _property_to_response(deal)


@router.get("/{deal_id}/full", response_model=FullDealResponse, response_model_by_alias=False)
async def get_deal_full(
    deal_id: uuid.UUID,
    property_service: PropertyService = Depends(get_property_service),
) -> FullDealResponse:
    """
    Get single deal by ID with all related data.

    Returns complete deal data including:
    - Basic deal info
    - Investment metrics
    - Financing details
    - Major tenants
    - Annual projections
    - Market analysis
    - Property details
    """
    deal = await property_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _property_to_full_response(deal)


@router.get("/{deal_id}/document", response_model=DealDocumentDownloadResponse)
async def get_deal_document(
    deal_id: uuid.UUID,
    property_service: PropertyService = Depends(get_property_service),
) -> DealDocumentDownloadResponse:
    """
    Get a presigned URL to download the deal's source document from S3.

    Returns a time-limited URL (1 hour expiration) that can be used to
    download the original PDF/DOCX document that was uploaded for this deal.
    """
    deal = await property_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if not deal.document_s3_key:
        raise HTTPException(status_code=404, detail="No document associated with this deal")

    try:
        expiration = 3600  # 1 hour
        download_url = property_service.generate_presigned_url(
            deal.document_s3_key, expiration=expiration
        )
        return DealDocumentDownloadResponse(
            downloadUrl=download_url,
            filename=deal.document_filename or "document",
            expiresIn=expiration,
        )
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate download URL: {str(e)}",
        )


@router.put("/{deal_id}", response_model=DealMemoResponse, response_model_by_alias=False)
async def update_deal(
    deal_id: uuid.UUID,
    deal_data: DealUpdateRequest,
    property_service: PropertyService = Depends(get_property_service),
) -> DealMemoResponse:
    """Update an existing deal."""
    deal = await property_service.update_deal(
        deal_id=deal_id,
        name=deal_data.name,
        deal_type=deal_data.dealType,
        summary=deal_data.summary,
        thesis=deal_data.thesis,
        minimum_investment=deal_data.minimumInvestment,
        target_return=deal_data.targetReturn,
        risk_factors=deal_data.riskFactors,
        ideal_investor_profile=deal_data.idealInvestorProfile,
        structure=deal_data.structure,
        timeline=deal_data.timeline,
        status=deal_data.status,
    )

    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return _property_to_response(deal)


@router.delete("/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: uuid.UUID,
    property_service: PropertyService = Depends(get_property_service),
) -> None:
    """Delete a deal by ID."""
    deleted = await property_service.delete_deal(deal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Deal not found")


@router.post("/upload", response_model=DealUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    property_service: PropertyService = Depends(get_property_service),
) -> DealUploadResponse:
    """
    Upload a deal document (PDF or DOCX) to S3.

    Returns uploadId for subsequent extraction.
    """
    # Read file content
    content = await file.read()

    # Validate file
    error = property_service.validate_file(
        content_type=file.content_type or "",
        size=len(content),
    )
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Upload to S3
    try:
        upload_id = await property_service.upload_document(
            filename=file.filename or "document",
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload to S3: {str(e)}",
        )

    return DealUploadResponse(
        uploadId=upload_id,
        filename=file.filename or "document",
        status="uploaded",
    )


@router.post("/extract", response_model=DealExtractionResponse, response_model_by_alias=False)
async def extract_document(
    upload_id: str = Form(...),
    property_service: PropertyService = Depends(get_property_service),
) -> DealExtractionResponse:
    """
    Extract deal data from uploaded document using AI.

    Requires uploadId from previous upload.
    Uses OpenAI structured outputs for extraction.

    Note: This endpoint only extracts and returns data. To create a deal with
    all related data (financing, tenants, projections, etc.), use the
    POST /api/v1/properties/create-from-upload endpoint instead.
    """
    extracted = await property_service.extract_document(upload_id)

    extraction = DealMemoExtraction(
        name=extracted["name"],
        dealType=extracted["deal_type"],
        summary=extracted["summary"],
        thesis=extracted["thesis"],
        minimumInvestment=extracted["minimum_investment"],
        targetReturn=extracted["target_return"],
        riskFactors=extracted["risk_factors"],
        idealInvestorProfile=extracted["ideal_investor_profile"],
        structure=extracted["structure"],
        timeline=extracted["timeline"],
        confidence=extracted["confidence"],
        rawText=extracted.get("raw_text", ""),
    )

    return DealExtractionResponse(
        extraction=extraction,
        rawText=extracted.get("raw_text", "[Full document text]"),
    )


@router.post("/extract-full", response_model=FullExtractionResponseWrapper, response_model_by_alias=False)
async def extract_document_full(
    upload_id: str = Form(...),
    property_service: PropertyService = Depends(get_property_service),
) -> FullExtractionResponseWrapper:
    """
    Extract FULL deal data from uploaded document using AI.

    Returns complete extraction including:
    - Basic deal info (name, type, summary, thesis)
    - Investment metrics (IRR, cap rates, equity multiples)
    - Financing details (loan amount, LTV, interest rate)
    - Major tenants (rent roll data)
    - Annual projections (year-by-year financials)
    - Market analysis (market data, vacancy, rent growth)
    - Property details (address, square footage)
    - Sponsor information

    Use this endpoint when you want to preview all extracted data before saving.
    After preview/edit, call POST /create-from-upload with the same uploadId to save.
    """
    full_extraction = await property_service.extract_document_full(upload_id)

    # Convert to response schemas
    property_details = None
    if full_extraction.property_details:
        property_details = PropertyDetailsResponse(
            address=full_extraction.property_details.address,
            city=full_extraction.property_details.city,
            state=full_extraction.property_details.state,
            zipCode=full_extraction.property_details.zip_code,
            totalSquareFeet=full_extraction.property_details.total_square_feet,
            yearBuilt=full_extraction.property_details.year_built,
            yearRenovated=full_extraction.property_details.year_renovated,
            parkingSpaces=full_extraction.property_details.parking_spaces,
        )

    investment_metrics = None
    if full_extraction.investment_metrics:
        investment_metrics = InvestmentMetricsResponse(
            targetIrrMin=full_extraction.investment_metrics.target_irr_min,
            targetIrrMax=full_extraction.investment_metrics.target_irr_max,
            targetEquityMultiple=full_extraction.investment_metrics.target_equity_multiple,
            targetCashOnCash=full_extraction.investment_metrics.target_cash_on_cash,
            capRateGoingIn=full_extraction.investment_metrics.cap_rate_going_in,
            capRateExit=full_extraction.investment_metrics.cap_rate_exit,
            preferredReturn=full_extraction.investment_metrics.preferred_return,
        )

    financing = None
    if full_extraction.financing:
        financing = FinancingResponse(
            loanAmount=full_extraction.financing.loan_amount,
            ltvRatio=full_extraction.financing.ltv_ratio,
            interestRate=full_extraction.financing.interest_rate,
            loanTermYears=full_extraction.financing.loan_term_years,
            amortizationYears=full_extraction.financing.amortization_years,
            lenderName=full_extraction.financing.lender_name,
            loanType=full_extraction.financing.loan_type,
        )

    major_tenants = [
        TenantResponse(
            tenantName=t.tenant_name,
            squareFeet=t.square_feet,
            annualRent=t.annual_rent,
            leaseExpiration=t.lease_expiration,
            tenantType=t.tenant_type,
        )
        for t in full_extraction.major_tenants
    ]

    market_analysis = None
    if full_extraction.market_analysis:
        market_analysis = MarketAnalysisResponse(
            marketName=full_extraction.market_analysis.market_name,
            submarket=full_extraction.market_analysis.submarket,
            populationGrowth=full_extraction.market_analysis.population_growth,
            employmentDrivers=full_extraction.market_analysis.employment_drivers or [],
            marketVacancyRate=full_extraction.market_analysis.market_vacancy_rate,
            marketRentGrowth=full_extraction.market_analysis.market_rent_growth,
            comparableSales=full_extraction.market_analysis.comparable_sales,
        )

    annual_projections = [
        AnnualProjectionResponse(
            year=p.year,
            grossRevenue=p.gross_revenue,
            effectiveGrossIncome=p.effective_gross_income,
            operatingExpenses=p.operating_expenses,
            noi=p.noi,
            cashFlow=p.cash_flow,
        )
        for p in full_extraction.annual_projections
    ]

    # Build target return string
    target_return_parts = []
    if full_extraction.investment_metrics:
        metrics = full_extraction.investment_metrics
        if metrics.target_irr_min and metrics.target_irr_max:
            target_return_parts.append(f"{metrics.target_irr_min}-{metrics.target_irr_max}% IRR")
        elif metrics.target_irr_min:
            target_return_parts.append(f"{metrics.target_irr_min}% IRR")
        elif metrics.target_irr_max:
            target_return_parts.append(f"{metrics.target_irr_max}% IRR")
        if metrics.target_equity_multiple:
            target_return_parts.append(f"{metrics.target_equity_multiple}x Equity Multiple")
    target_return = ", ".join(target_return_parts) if target_return_parts else "TBD"

    full_response = FullExtractionResponse(
        dealName=full_extraction.deal_name,
        propertyType=full_extraction.property_type,
        dealStructure=full_extraction.deal_structure,
        executiveSummary=full_extraction.executive_summary,
        investmentThesis=full_extraction.investment_thesis,
        valueAddStrategy=full_extraction.value_add_strategy,
        totalCapitalization=full_extraction.total_capitalization,
        equityRequired=full_extraction.equity_required,
        minimumInvestment=full_extraction.minimum_investment,
        holdPeriodYears=full_extraction.hold_period_years,
        riskFactors=full_extraction.risk_factors or [],
        idealInvestorProfile=full_extraction.ideal_investor_profile,
        sponsorName=full_extraction.sponsor_name,
        sponsorTrackRecord=full_extraction.sponsor_track_record,
        propertyDetails=property_details,
        investmentMetrics=investment_metrics,
        financing=financing,
        majorTenants=major_tenants,
        marketAnalysis=market_analysis,
        annualProjections=annual_projections,
        confidenceScore=full_extraction.confidence_score,
        extractionNotes=full_extraction.extraction_notes,
        uploadId=upload_id,
    )

    # Also provide legacy format for backward compatibility
    legacy = DealMemoExtraction(
        name=full_extraction.deal_name,
        dealType=full_extraction.property_type,
        summary=full_extraction.executive_summary or "",
        thesis=full_extraction.investment_thesis or "",
        minimumInvestment=full_extraction.minimum_investment or 0,
        targetReturn=target_return,
        riskFactors=full_extraction.risk_factors or [],
        idealInvestorProfile=full_extraction.ideal_investor_profile or "",
        structure=full_extraction.deal_structure or "LP/GP",
        timeline=full_extraction.hold_period_years or "5-7 years",
        confidence=full_extraction.confidence_score,
        rawText=f"[Extracted from PDF - Confidence: {full_extraction.confidence_score}]",
    )

    return FullExtractionResponseWrapper(
        extraction=full_response,
        legacyExtraction=legacy,
    )


@router.post("/create-from-upload", response_model=DealMemoResponse, response_model_by_alias=False)
async def create_deal_from_upload(
    upload_id: str = Form(...),
    property_service: PropertyService = Depends(get_property_service),
) -> DealMemoResponse:
    """
    Extract deal data from uploaded document and create the deal in one step.

    This is the recommended endpoint for creating deals as it:
    1. Extracts ALL data from the PDF (not just basic fields)
    2. Creates the Property with all related tables populated:
       - InvestmentMetrics (IRR, cap rates, equity multiples)
       - Financing (loan amount, LTV, interest rate, terms)
       - Tenants (rent roll data)
       - AnnualProjections (year-by-year financials)
       - MarketAnalysis (market data)
       - PropertyDocument (document reference)
    3. Generates embeddings for semantic search/matching

    Requires uploadId from previous POST /upload.
    """
    try:
        property_obj = await property_service.extract_and_create_deal(upload_id)
        return _property_to_response(property_obj)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create deal from upload: {str(e)}",
        )


def _property_to_response(deal: Property) -> DealMemoResponse:
    """Convert Property model to response schema."""
    return DealMemoResponse(
        id=str(deal.id),
        name=deal.name,
        dealType=deal.deal_type,
        summary=deal.summary,
        thesis=deal.thesis,
        minimumInvestment=deal.minimum_investment,
        targetReturn=deal.target_return,
        riskFactors=deal.risk_factors or [],
        idealInvestorProfile=deal.ideal_investor_profile,
        structure=deal.structure,
        timeline=deal.timeline,
        status=deal.status,
        createdAt=deal.created_at,
        updatedAt=deal.updated_at,
    )


def _property_to_full_response(deal: Property) -> FullDealResponse:
    """Convert Property model to full response schema with all related data."""
    # Build property details from Property and PropertyFeature
    property_details = None
    if deal.address or deal.city or deal.state or deal.zip_code or deal.square_feet:
        year_built = None
        year_renovated = None
        parking_spaces = None
        if deal.features:
            year_built = deal.features.year_built
            year_renovated = deal.features.year_renovated
            parking_spaces = deal.features.parking_spaces
        property_details = PropertyDetailsResponse(
            address=deal.address,
            city=deal.city,
            state=deal.state,
            zipCode=deal.zip_code,
            totalSquareFeet=deal.square_feet,
            yearBuilt=year_built,
            yearRenovated=year_renovated,
            parkingSpaces=parking_spaces,
        )

    # Build investment metrics
    investment_metrics = None
    if deal.investment_metrics:
        m = deal.investment_metrics
        investment_metrics = InvestmentMetricsResponse(
            targetIrrMin=m.target_irr_min,
            targetIrrMax=m.target_irr_max,
            targetEquityMultiple=m.target_equity_multiple,
            targetCashOnCash=m.target_cash_on_cash,
            capRateGoingIn=m.cap_rate_going_in,
            capRateExit=m.cap_rate_exit,
            preferredReturn=m.preferred_return,
        )

    # Build financing
    financing = None
    if deal.financing:
        f = deal.financing
        financing = FinancingResponse(
            loanAmount=f.loan_amount,
            ltvRatio=f.ltv_ratio,
            interestRate=f.interest_rate,
            loanTermYears=f.loan_term_years,
            amortizationYears=f.amortization_years,
            lenderName=f.lender_name,
            loanType=f.loan_type,
        )

    # Build tenants list
    major_tenants = []
    if deal.tenants:
        major_tenants = [
            TenantResponse(
                tenantName=t.tenant_name,
                squareFeet=t.square_feet,
                annualRent=t.annual_rent,
                leaseExpiration=t.lease_expiration,
                tenantType=t.tenant_type,
            )
            for t in deal.tenants
        ]

    # Build market analysis
    market_analysis = None
    if deal.market_analysis:
        ma = deal.market_analysis
        market_analysis = MarketAnalysisResponse(
            marketName=ma.market_name,
            submarket=ma.submarket,
            populationGrowth=ma.population_growth,
            employmentDrivers=ma.employment_drivers or [],
            marketVacancyRate=ma.market_vacancy_rate,
            marketRentGrowth=ma.market_rent_growth,
            comparableSales=ma.comparable_sales,
        )

    # Build annual projections
    annual_projections = []
    if deal.annual_projections:
        annual_projections = [
            AnnualProjectionResponse(
                year=p.year,
                grossRevenue=p.gross_revenue,
                effectiveGrossIncome=p.effective_gross_income,
                operatingExpenses=p.operating_expenses,
                noi=p.noi,
                cashFlow=p.cash_flow,
            )
            for p in deal.annual_projections
        ]

    return FullDealResponse(
        id=str(deal.id),
        name=deal.name,
        dealType=deal.deal_type,
        summary=deal.summary,
        thesis=deal.thesis,
        minimumInvestment=deal.minimum_investment,
        targetReturn=deal.target_return,
        riskFactors=deal.risk_factors or [],
        idealInvestorProfile=deal.ideal_investor_profile,
        structure=deal.structure,
        timeline=deal.timeline,
        status=deal.status,
        createdAt=deal.created_at,
        updatedAt=deal.updated_at,
        valueAddStrategy=deal.value_add_strategy,
        totalCapitalization=float(deal.total_capitalization) if deal.total_capitalization else None,
        sponsorName=deal.sponsor_name,
        sponsorTrackRecord=deal.sponsor_track_record,
        extractionConfidence=float(deal.extraction_confidence) if deal.extraction_confidence else None,
        extractionNotes=deal.extraction_notes,
        propertyDetails=property_details,
        investmentMetrics=investment_metrics,
        financing=financing,
        majorTenants=major_tenants,
        marketAnalysis=market_analysis,
        annualProjections=annual_projections,
    )
