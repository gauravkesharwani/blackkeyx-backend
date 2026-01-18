"""
Properties/Deals router.

Handles:
- GET /api/v1/properties - List deals
- POST /api/v1/properties - Create deal
- GET /api/v1/properties/{id} - Get deal
- PUT /api/v1/properties/{id} - Update deal
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
    DealCreateRequest,
    DealExtractionResponse,
    DealListResponse,
    DealMemoExtraction,
    DealMemoResponse,
    DealUpdateRequest,
    DealUploadResponse,
)
from app.services.property_service import PropertyService

router = APIRouter()


@router.get("", response_model=DealListResponse)
async def list_deals(
    property_service: PropertyService = Depends(get_property_service),
    status: Optional[str] = None,
) -> DealListResponse:
    """Get list of deals."""
    deals, total = await property_service.list_deals(status=status)
    deal_responses = [_property_to_response(deal) for deal in deals]
    return DealListResponse(deals=deal_responses, total=total)


@router.post("", response_model=DealMemoResponse)
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


@router.get("/{deal_id}", response_model=DealMemoResponse)
async def get_deal(
    deal_id: uuid.UUID,
    property_service: PropertyService = Depends(get_property_service),
) -> DealMemoResponse:
    """Get single deal by ID."""
    deal = await property_service.get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _property_to_response(deal)


@router.put("/{deal_id}", response_model=DealMemoResponse)
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


@router.post("/extract", response_model=DealExtractionResponse)
async def extract_document(
    upload_id: str = Form(...),
    property_service: PropertyService = Depends(get_property_service),
) -> DealExtractionResponse:
    """
    Extract deal data from uploaded document using AI.

    Requires uploadId from previous upload.
    Uses OpenAI structured outputs for extraction.
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
