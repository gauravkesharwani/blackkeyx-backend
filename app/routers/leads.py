"""
Lead submission router.

Handles POST /api/v1/submit-lead from chatbot.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.investor_repo import InvestorRepository
from app.db.session import get_db
from app.models.consent import StageHistory
from app.models.investor import InvestorProfile
from app.schemas.lead import LeadSubmissionRequest, LeadSubmissionResponse

router = APIRouter()


def parse_capital(capital_str: Optional[str]) -> Optional[int]:
    """Parse capital string like '$250K-$500K' to integer (midpoint)."""
    if not capital_str:
        return None

    # Handle 'other:...' format
    if capital_str.startswith("other:"):
        return None

    # Map known values to midpoint
    capital_map = {
        "$100K-$250K": 175000,
        "$250K-$500K": 375000,
        "$500K-$1M": 750000,
        "$1M+": 1500000,
    }

    return capital_map.get(capital_str)


@router.post("/submit-lead", response_model=LeadSubmissionResponse)
async def submit_lead(
    request: Request,
    lead_data: LeadSubmissionRequest,
    session: AsyncSession = Depends(get_db),
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

    repo = InvestorRepository(session)

    # Check if phone already exists
    existing = await repo.get_by_phone(lead_data.phoneNumber)
    if existing:
        # Return existing lead_id instead of creating duplicate
        return LeadSubmissionResponse(
            success=True,
            message="Lead already exists",
            leadId=str(existing.id),
        )

    # Parse capital from qualification
    capital_available = None
    if lead_data.qualification:
        capital_available = parse_capital(lead_data.qualification.capacity)
    elif lead_data.capitalAvailable:
        capital_available = parse_capital(lead_data.capitalAvailable)

    # Parse investment preferences
    investment_preferences = lead_data.investmentPreferences or []

    # Create investor profile
    investor = InvestorProfile(
        id=uuid.uuid4(),
        phone=lead_data.phoneNumber,
        timeline=lead_data.investmentTimeline,
        capital_available=capital_available,
        investment_preferences=investment_preferences,
        stage="new_lead",
        source="web",
    )

    # Add qualification data if present
    if lead_data.qualification:
        q = lead_data.qualification
        investor.investor_type = q.investorType
        investor.capacity = q.capacity
        investor.fit = q.fit
        investor.process = q.process
        investor.timing = q.timing
        investor.qualification_bucket = q.bucket
        investor.qualification_score = q.score
        investor.lead_score = q.score

    # Save investor
    investor = await repo.create(investor)

    # Store consent record
    ip_address = x_forwarded_for or (
        request.client.host if request.client else None
    )
    await repo.add_consent(
        investor_id=investor.id,
        consent_text="TCPA consent granted via web chatbot",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Record initial stage
    stage_change = StageHistory(
        investor_id=investor.id,
        from_stage=None,
        to_stage="new_lead",
        changed_by="system",
        notes="Lead submitted via chatbot",
    )
    session.add(stage_change)

    return LeadSubmissionResponse(
        success=True,
        message="Lead submitted successfully",
        leadId=str(investor.id),
    )
