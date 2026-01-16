"""Pydantic schemas for API request/response validation."""

from app.schemas.admin import (
    ActivityItem,
    AdminStatsResponse,
    AuthRequest,
    AuthResponse,
    LeadFilters,
)
from app.schemas.investor import (
    AddNoteRequest,
    CallRecordResponse,
    DealMatchResponse,
    InvestorQualificationResponse,
    LeadListResponse,
    LeadNoteResponse,
    LeadWithDetailsResponse,
    StageChangeResponse,
    StageUpdateRequest,
)
from app.schemas.lead import (
    LeadSubmissionRequest,
    LeadSubmissionResponse,
    QualificationData,
)
from app.schemas.property import (
    DealCreateRequest,
    DealExtractionResponse,
    DealListResponse,
    DealMemoExtraction,
    DealMemoResponse,
    DealUpdateRequest,
    DealUploadResponse,
)

__all__ = [
    # Lead
    "QualificationData",
    "LeadSubmissionRequest",
    "LeadSubmissionResponse",
    # Investor
    "InvestorQualificationResponse",
    "CallRecordResponse",
    "DealMatchResponse",
    "LeadNoteResponse",
    "StageChangeResponse",
    "LeadWithDetailsResponse",
    "LeadListResponse",
    "StageUpdateRequest",
    "AddNoteRequest",
    # Property
    "DealMemoResponse",
    "DealMemoExtraction",
    "DealUploadResponse",
    "DealExtractionResponse",
    "DealListResponse",
    "DealCreateRequest",
    "DealUpdateRequest",
    # Admin
    "ActivityItem",
    "AdminStatsResponse",
    "LeadFilters",
    "AuthRequest",
    "AuthResponse",
]
