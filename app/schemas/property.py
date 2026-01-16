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

    uploadId: str = Field(..., alias="upload_id")
    filename: str
    status: str

    class Config:
        populate_by_name = True


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
