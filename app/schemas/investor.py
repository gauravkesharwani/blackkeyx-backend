"""
Investor/Lead schemas for API responses.

Maps to frontend types/lead.ts:
- LeadWithDetails
- CallRecord
- DealMatch
- LeadNote
- StageChange
- LeadListResponse
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_serializer


class InvestorQualificationResponse(BaseModel):
    """Qualification data in response format."""

    investorType: str
    capacity: str
    fit: str
    process: str
    timing: str
    score: int
    bucket: str


class CallRecordResponse(BaseModel):
    """
    Call record response.

    Maps to CallRecord from frontend:
    interface CallRecord {
      id: string
      status: 'initiated' | 'ringing' | 'answered' | 'completed' | 'failed'
      duration?: number
      transcript?: string
      recordingUrl?: string
      initiatedAt: string
      completedAt?: string
    }
    """

    id: str
    status: str
    duration: Optional[int] = None
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    initiatedAt: datetime
    completedAt: Optional[datetime] = None

    @field_serializer("initiatedAt", "completedAt")
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None


class DealMatchResponse(BaseModel):
    """
    Deal match response.

    Maps to DealMatch from frontend:
    interface DealMatch {
      id: string
      dealMemoId: string
      dealName: string
      similarityScore: number
      matchReasons: string[]
      status: 'pending' | 'presented' | 'accepted' | 'rejected'
      createdAt: string
    }
    """

    id: str
    dealMemoId: str
    dealName: str
    similarityScore: float
    matchReasons: List[str]
    status: str
    createdAt: datetime

    @field_serializer("createdAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class LeadNoteResponse(BaseModel):
    """
    Lead note response.

    Maps to LeadNote from frontend:
    interface LeadNote {
      id: string
      content: string
      createdBy: string
      createdAt: string
    }
    """

    id: str
    content: str
    createdBy: str
    createdAt: datetime

    @field_serializer("createdAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class StageChangeResponse(BaseModel):
    """
    Stage change response.

    Maps to StageChange from frontend:
    interface StageChange {
      id: string
      fromStage: PipelineStage | null
      toStage: PipelineStage
      changedBy: string
      notes?: string
      changedAt: string
    }
    """

    id: str
    fromStage: Optional[str] = None
    toStage: str
    changedBy: str
    notes: Optional[str] = None
    changedAt: datetime

    @field_serializer("changedAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class LeadWithDetailsResponse(BaseModel):
    """
    Full lead details response.

    Maps to LeadWithDetails from frontend:
    interface LeadWithDetails {
      id: string
      phone: string
      timeline: string
      capitalAvailable: number
      investmentPreferences: string[]
      investmentThesis?: string
      riskTolerance?: string
      stage: PipelineStage
      leadScore: number
      source: string
      createdAt: string
      updatedAt: string
      calls: CallRecord[]
      matches: DealMatch[]
      notes: LeadNote[]
      stageHistory: StageChange[]
      qualification?: InvestorQualification
    }
    """

    id: str
    name: str
    phone: str
    timeline: Optional[str] = None
    capitalAvailable: Optional[int] = None
    investmentPreferences: List[str] = Field(default_factory=list)
    investmentThesis: Optional[str] = None
    riskTolerance: Optional[str] = None
    stage: str
    leadScore: int
    source: str
    createdAt: datetime
    updatedAt: datetime
    calls: List[CallRecordResponse] = Field(default_factory=list)
    matches: List[DealMatchResponse] = Field(default_factory=list)
    notes: List[LeadNoteResponse] = Field(default_factory=list)
    stageHistory: List[StageChangeResponse] = Field(default_factory=list)
    qualification: Optional[InvestorQualificationResponse] = None

    @field_serializer("createdAt", "updatedAt")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()


class LeadListResponse(BaseModel):
    """
    Paginated lead list response.

    Maps to LeadListResponse from frontend:
    interface LeadListResponse {
      leads: LeadWithDetails[]
      total: number
      page: number
      pageSize: number
      totalPages: number
    }
    """

    leads: List[LeadWithDetailsResponse]
    total: int
    page: int
    pageSize: int
    totalPages: int


class StageUpdateRequest(BaseModel):
    """Request to update lead stage."""

    stage: str
    notes: Optional[str] = None


class AddNoteRequest(BaseModel):
    """Request to add a note to a lead."""

    content: str
