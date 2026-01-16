"""
Lead submission schemas.

Maps to frontend validation.ts:
- leadSchema
- qualificationSchema
"""

from typing import Optional

from pydantic import BaseModel, Field


class QualificationData(BaseModel):
    """
    Qualification data from chatbot.

    Maps to InvestorQualification from frontend:
    - investorType: 'hnw' | 'family_office' | 'other:...'
    - capacity: '$100K-$250K' | '$250K-$500K' | '$500K-$1M' | '$1M+' | 'other:...'
    - fit: 'high_priority' | 'medium_priority' | 'open_to_exploring' | 'not_a_focus' | 'other:...'
    - process: 'toe_in' | 'meaningful_first' | 'full_commitment' | 'other:...'
    - timing: 'actively_deploying' | 'possibly_evaluating' | 'just_researching' | 'other:...'
    - score: 0-100
    - bucket: 'active_intro' | 'nurture' | 'not_qualified'
    """

    investorType: str = Field(..., alias="investor_type")
    capacity: str
    fit: str
    process: str
    timing: str
    score: int = Field(..., ge=0, le=100)
    bucket: str

    class Config:
        populate_by_name = True


class LeadSubmissionRequest(BaseModel):
    """
    Lead submission request from chatbot.

    Maps to leadSchema from frontend validation.ts:
    - phoneNumber: validated phone string
    - consent: must be true
    - timestamp: ISO string
    - qualification: optional InvestorQualification
    """

    phoneNumber: str = Field(..., min_length=10, alias="phone_number")
    consent: bool = Field(..., description="Must be true for TCPA compliance")
    timestamp: str
    qualification: Optional[QualificationData] = None

    # Optional context from chatbot
    investmentTimeline: Optional[str] = Field(None, alias="investment_timeline")
    capitalAvailable: Optional[str] = Field(None, alias="capital_available")
    investmentPreferences: Optional[list[str]] = Field(
        None, alias="investment_preferences"
    )

    class Config:
        populate_by_name = True


class LeadSubmissionResponse(BaseModel):
    """Response after successful lead submission."""

    success: bool
    message: str
    leadId: str = Field(..., alias="lead_id")

    class Config:
        populate_by_name = True
        from_attributes = True
