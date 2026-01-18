"""
Admin dashboard router.

Handles:
- GET /api/v1/admin/stats
- GET /api/v1/admin/leads
- GET /api/v1/admin/leads/{id}
- PATCH /api/v1/admin/leads/{id}/stage
- POST /api/v1/admin/leads/{id}/notes
- POST /api/v1/admin/auth (login)
- DELETE /api/v1/admin/auth (logout)
"""

import logging
import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.config import get_settings
from app.dependencies import get_admin_service
from app.schemas.admin import (
    ActivityItem,
    AdminStatsResponse,
    AuthRequest,
    AuthResponse,
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
from app.services.admin_service import AdminService

logger = logging.getLogger(__name__)

router = APIRouter()
settings = get_settings()

# Valid pipeline stages
VALID_STAGES = [
    "new_lead",
    "call_dispatched",
    "call_completed",
    "insights_extracted",
    "deals_matched",
    "under_review",
    "closed",
]


@router.post("/auth", response_model=AuthResponse)
async def login(
    auth_data: AuthRequest,
    response: Response,
) -> AuthResponse:
    """Admin login with password."""
    if auth_data.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid password")

    # Set session cookie (same pattern as frontend)
    session_token = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        secure=False,  # Set True in production
        samesite="lax",
        max_age=86400,  # 24 hours
    )

    return AuthResponse(success=True, message="Login successful")


@router.delete("/auth", response_model=AuthResponse)
async def logout(response: Response) -> AuthResponse:
    """Admin logout - clear session cookie."""
    response.delete_cookie("admin_session")
    return AuthResponse(success=True, message="Logged out")


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    admin_service: AdminService = Depends(get_admin_service),
) -> AdminStatsResponse:
    """
    Get admin dashboard statistics.

    Returns:
    - totalLeads: Total number of leads
    - byStage: Count per pipeline stage
    - averageScore: Average lead score
    - totalDeals: Total active deals
    - recentActivity: Recent activity items
    """
    stats = await admin_service.get_dashboard_stats()
    recent_leads = await admin_service.get_recent_leads(limit=5)

    recent_activity = [
        ActivityItem(
            id=str(lead.id),
            type="new_lead",
            message=f"New lead from {lead.phone[:6]}***",
            timestamp=lead.created_at,
        )
        for lead in recent_leads
    ]

    return AdminStatsResponse(
        totalLeads=stats["total_leads"],
        byStage=stats["by_stage"],
        averageScore=round(stats["average_score"], 1),
        totalDeals=stats["total_deals"],
        recentActivity=recent_activity,
    )


@router.get("/leads", response_model=LeadListResponse)
async def list_leads(
    admin_service: AdminService = Depends(get_admin_service),
    stage: Optional[str] = Query(None),
    score_min: Optional[int] = Query(None, alias="scoreMin"),
    score_max: Optional[int] = Query(None, alias="scoreMax"),
    capital_min: Optional[int] = Query(None, alias="capitalMin"),
    capital_max: Optional[int] = Query(None, alias="capitalMax"),
    date_from: Optional[str] = Query(None, alias="dateFrom"),
    date_to: Optional[str] = Query(None, alias="dateTo"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at", alias="sortBy"),
    sort_order: str = Query("desc", alias="sortOrder"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> LeadListResponse:
    """
    Get paginated list of leads with filters.

    Query Parameters:
    - stage: Filter by pipeline stage
    - scoreMin/Max: Lead score range
    - capitalMin/Max: Capital available range
    - dateFrom/To: Created date range (ISO format)
    - search: Search phone numbers
    - sortBy: Sort field (created_at, lead_score, capital_available)
    - sortOrder: asc or desc
    - page: Page number (1-indexed)
    - pageSize: Items per page (max 100)
    """
    # Parse dates
    date_from_dt = None
    date_to_dt = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            pass
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Calculate offset
    skip = (page - 1) * page_size

    # Search
    leads, total = await admin_service.search_leads(
        stage=stage,
        score_min=score_min,
        score_max=score_max,
        capital_min=capital_min,
        capital_max=capital_max,
        date_from=date_from_dt,
        date_to=date_to_dt,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=page_size,
    )

    # Convert to response format
    lead_responses = [_investor_to_response(lead) for lead in leads]

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return LeadListResponse(
        leads=lead_responses,
        total=total,
        page=page,
        pageSize=page_size,
        totalPages=total_pages,
    )


@router.get("/leads/{lead_id}", response_model=LeadWithDetailsResponse)
async def get_lead(
    lead_id: uuid.UUID,
    admin_service: AdminService = Depends(get_admin_service),
) -> LeadWithDetailsResponse:
    """Get single lead with full details."""
    lead = await admin_service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return _investor_to_response(lead)


@router.patch("/leads/{lead_id}/stage", response_model=LeadWithDetailsResponse)
async def update_lead_stage(
    lead_id: uuid.UUID,
    stage_data: StageUpdateRequest,
    admin_service: AdminService = Depends(get_admin_service),
) -> LeadWithDetailsResponse:
    """
    Update lead pipeline stage.

    Validates stage is a valid PipelineStage value.
    Records stage change in history.

    When stage changes to 'call_dispatched', automatically dispatches
    an outbound call to the investor via LiveKit.
    """
    if stage_data.stage not in VALID_STAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage. Must be one of: {VALID_STAGES}",
        )

    try:
        lead = await admin_service.update_lead_stage(
            lead_id=lead_id,
            new_stage=stage_data.stage,
            notes=stage_data.notes,
        )
    except Exception as e:
        logger.error(f"Failed to update stage or dispatch call: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Stage update failed: {str(e)}",
        )

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return _investor_to_response(lead)


@router.post("/leads/{lead_id}/notes", response_model=LeadNoteResponse)
async def add_lead_note(
    lead_id: uuid.UUID,
    note_data: AddNoteRequest,
    admin_service: AdminService = Depends(get_admin_service),
) -> LeadNoteResponse:
    """Add a note to a lead."""
    note = await admin_service.add_lead_note(
        lead_id=lead_id,
        content=note_data.content,
    )

    if not note:
        raise HTTPException(status_code=404, detail="Lead not found")

    return LeadNoteResponse(
        id=str(note.id),
        content=note.content,
        createdBy=note.created_by,
        createdAt=note.created_at,
    )


def _investor_to_response(lead) -> LeadWithDetailsResponse:
    """Convert InvestorProfile model to response schema."""
    # Build qualification if present
    qualification = None
    if lead.investor_type and lead.qualification_bucket:
        qualification = InvestorQualificationResponse(
            investorType=lead.investor_type,
            capacity=lead.capacity or "",
            fit=lead.fit or "",
            process=lead.process or "",
            timing=lead.timing or "",
            score=lead.qualification_score or lead.lead_score,
            bucket=lead.qualification_bucket,
        )

    # Convert calls
    calls = [
        CallRecordResponse(
            id=str(call.id),
            status=call.status,
            duration=call.duration,
            transcript=call.transcript,
            recordingUrl=call.recording_url,
            initiatedAt=call.initiated_at,
            completedAt=call.completed_at,
        )
        for call in (lead.calls or [])
    ]

    # Convert matches
    matches = [
        DealMatchResponse(
            id=str(match.id),
            dealMemoId=str(match.property_id),
            dealName=match.property.name if match.property else "",
            similarityScore=float(match.similarity_score),
            matchReasons=match.match_reasons or [],
            status=match.status,
            createdAt=match.created_at,
        )
        for match in (lead.matches or [])
    ]

    # Convert notes
    notes = [
        LeadNoteResponse(
            id=str(note.id),
            content=note.content,
            createdBy=note.created_by,
            createdAt=note.created_at,
        )
        for note in (lead.notes or [])
    ]

    # Convert stage history
    stage_history = [
        StageChangeResponse(
            id=str(change.id),
            fromStage=change.from_stage,
            toStage=change.to_stage,
            changedBy=change.changed_by,
            notes=change.notes,
            changedAt=change.changed_at,
        )
        for change in (lead.stage_history or [])
    ]

    return LeadWithDetailsResponse(
        id=str(lead.id),
        name=lead.name,
        phone=lead.phone,
        timeline=lead.timeline,
        capitalAvailable=lead.capital_available,
        investmentPreferences=lead.investment_preferences or [],
        investmentThesis=lead.investment_thesis,
        riskTolerance=lead.risk_tolerance,
        stage=lead.stage,
        leadScore=lead.lead_score,
        source=lead.source,
        createdAt=lead.created_at,
        updatedAt=lead.updated_at,
        calls=calls,
        matches=matches,
        notes=notes,
        stageHistory=stage_history,
        qualification=qualification,
    )
