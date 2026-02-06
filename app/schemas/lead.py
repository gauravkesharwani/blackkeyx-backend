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
    Qualification answers from chatbot.

    The frontend sends raw answers only. Score and bucket are
    computed server-side by lead_service.calculate_qualification_score().
    """

    investorType: str = Field(..., alias="investor_type")
    capacity: str
    fit: str
    process: str
    timing: str

    class Config:
        populate_by_name = True


class LeadSubmissionRequest(BaseModel):
    """
    Lead submission request from chatbot.

    Maps to leadSchema from frontend validation.ts:
    - name: user's name (required)
    - phoneNumber: validated phone string
    - consent: must be true
    - timestamp: ISO string
    - qualification: optional InvestorQualification
    """

    name: str = Field(..., min_length=1, max_length=255)
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
