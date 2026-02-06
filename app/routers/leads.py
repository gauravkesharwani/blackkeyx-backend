"""
Lead submission router.

Handles POST /api/v1/submit-lead from chatbot.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.config import get_settings
from app.dependencies import get_lead_service
from app.middleware.rate_limit import limiter
from app.schemas.lead import LeadSubmissionRequest, LeadSubmissionResponse
from app.services.lead_service import LeadService

router = APIRouter()
settings = get_settings()


@router.post("/submit-lead", response_model=LeadSubmissionResponse)
@limiter.limit(settings.rate_limit_lead)
async def submit_lead(
    request: Request,
    lead_data: LeadSubmissionRequest,
    lead_service: LeadService = Depends(get_lead_service),
    x_forwarded_for: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
) -> LeadSubmissionResponse:
    """
    Accept lead from chatbot and create investor record.

    This endpoint:
    1. Validates consent (must be true)
    2. Creates investor profile with qualification data
    3. Stores TCPA consent record
    4. Records initial stage history

    Returns lead_id for tracking.
    """
    # Validate consent
    if not lead_data.consent:
        raise HTTPException(
            status_code=400,
            detail="Consent is required for lead submission",
        )

    # Get IP address
    ip_address = x_forwarded_for or (
        request.client.host if request.client else None
    )

    # Build qualification dict if present
    qualification = None
    if lead_data.qualification:
        qualification = {
            "investorType": lead_data.qualification.investorType,
            "capacity": lead_data.qualification.capacity,
            "fit": lead_data.qualification.fit,
            "process": lead_data.qualification.process,
            "timing": lead_data.qualification.timing,
            "bucket": lead_data.qualification.bucket,
            "score": lead_data.qualification.score,
        }

    # Submit lead via service
    investor, is_new = await lead_service.submit_lead(
        phone=lead_data.phoneNumber,
        consent=lead_data.consent,
        name=lead_data.name,
        timeline=lead_data.investmentTimeline,
        capital_available=lead_data.capitalAvailable,
        investment_preferences=lead_data.investmentPreferences,
        qualification=qualification,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if is_new:
        return LeadSubmissionResponse(
            success=True,
            message="Lead submitted successfully",
            leadId=str(investor.id),
        )
    else:
        return LeadSubmissionResponse(
            success=True,
            message="Lead already exists",
            leadId=str(investor.id),
        )
