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
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repositories.property_repo import PropertyRepository
from app.db.session import get_db
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

router = APIRouter()
settings = get_settings()

# Allowed file types
ALLOWED_CONTENT_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def get_s3_client():
    """Get boto3 S3 client."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


@router.get("", response_model=DealListResponse)
async def list_deals(
    session: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
) -> DealListResponse:
    """Get list of deals."""
    repo = PropertyRepository(session)

    if status:
        deals = await repo.get_by_status(status)
        total = len(deals)
    else:
        deals, total = await repo.get_active_deals()

    deal_responses = [_property_to_response(deal) for deal in deals]

    return DealListResponse(deals=deal_responses, total=total)


@router.post("", response_model=DealMemoResponse)
async def create_deal(
    deal_data: DealCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> DealMemoResponse:
    """Create a new deal from extracted data."""
    repo = PropertyRepository(session)

    property_obj = Property(
        id=uuid.uuid4(),
        name=deal_data.name,
        deal_type=deal_data.dealType,
        summary=deal_data.summary,
        thesis=deal_data.thesis,
        minimum_investment=deal_data.minimumInvestment,
        target_return=deal_data.targetReturn,
        risk_factors=deal_data.riskFactors or [],
        ideal_investor_profile=deal_data.idealInvestorProfile,
        structure=deal_data.structure,
        timeline=deal_data.timeline,
        status="active",
    )

    property_obj = await repo.create(property_obj)

    return _property_to_response(property_obj)


@router.get("/{deal_id}", response_model=DealMemoResponse)
async def get_deal(
    deal_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DealMemoResponse:
    """Get single deal by ID."""
    repo = PropertyRepository(session)

    deal = await repo.get(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return _property_to_response(deal)


@router.put("/{deal_id}", response_model=DealMemoResponse)
async def update_deal(
    deal_id: uuid.UUID,
    deal_data: DealUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> DealMemoResponse:
    """Update an existing deal."""
    repo = PropertyRepository(session)

    deal = await repo.get(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Update fields if provided
    if deal_data.name is not None:
        deal.name = deal_data.name
    if deal_data.dealType is not None:
        deal.deal_type = deal_data.dealType
    if deal_data.summary is not None:
        deal.summary = deal_data.summary
    if deal_data.thesis is not None:
        deal.thesis = deal_data.thesis
    if deal_data.minimumInvestment is not None:
        deal.minimum_investment = deal_data.minimumInvestment
    if deal_data.targetReturn is not None:
        deal.target_return = deal_data.targetReturn
    if deal_data.riskFactors is not None:
        deal.risk_factors = deal_data.riskFactors
    if deal_data.idealInvestorProfile is not None:
        deal.ideal_investor_profile = deal_data.idealInvestorProfile
    if deal_data.structure is not None:
        deal.structure = deal_data.structure
    if deal_data.timeline is not None:
        deal.timeline = deal_data.timeline
    if deal_data.status is not None:
        deal.status = deal_data.status

    deal = await repo.update(deal)

    return _property_to_response(deal)


@router.post("/upload", response_model=DealUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
) -> DealUploadResponse:
    """
    Upload a deal document (PDF or DOCX) to S3.

    Returns uploadId for subsequent extraction.
    """
    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: PDF, DOCX",
        )

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Generate upload ID and S3 key
    upload_id = str(uuid.uuid4())
    s3_key = f"uploads/{upload_id}/{file.filename}"

    # Upload to S3
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=settings.aws_s3_bucket,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type,
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
    session: AsyncSession = Depends(get_db),
) -> DealExtractionResponse:
    """
    Extract deal data from uploaded document using AI.

    Requires uploadId from previous upload.
    Uses OpenAI structured outputs for extraction.
    """
    # For now, return a mock extraction
    # TODO: Implement actual PDF parsing and OpenAI extraction

    # Mock extraction response
    extraction = DealMemoExtraction(
        name="Sample Deal",
        dealType="multifamily",
        summary="This is a sample deal extracted from the document.",
        thesis="Strong fundamentals with value-add opportunity.",
        minimumInvestment=100000,
        targetReturn="15-18% IRR",
        riskFactors=["Market risk", "Interest rate risk", "Occupancy risk"],
        idealInvestorProfile="Accredited investors seeking stable cash flow",
        structure="LP/GP",
        timeline="5-7 years",
        confidence=0.85,
        rawText="[Document text would be extracted here]",
    )

    return DealExtractionResponse(
        extraction=extraction,
        rawText="[Full document text]",
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
