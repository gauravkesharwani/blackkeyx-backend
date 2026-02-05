"""
Matching API endpoints.

Provides endpoints for:
- Getting matched deals for an investor
- Getting matched investors for a deal
- Triggering matching runs
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.matching import DealMatch
from app.services.matching_service import MatchingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/matching", tags=["matching"])


# ==================== Response Models ====================


class ScoreBreakdownResponse(BaseModel):
    """Score breakdown response."""

    return_match: float = 0.0
    risk_match: float = 0.0
    geography_match: float = 0.0
    structure_match: float = 0.0
    hold_period_match: float = 0.0
    strategy_match: float = 0.0
    capacity_fit: float = 0.0


class MatchResponse(BaseModel):
    """Match result response."""

    id: str
    investorId: str = Field(..., validation_alias="investor_id")
    propertyId: str = Field(..., validation_alias="property_id")
    investorName: Optional[str] = Field(None, validation_alias="investor_name")
    investorPhone: Optional[str] = Field(None, validation_alias="investor_phone")
    dealName: Optional[str] = Field(None, validation_alias="deal_name")
    finalScore: float = Field(..., validation_alias="final_score")
    softScore: Optional[float] = Field(None, validation_alias="soft_score")
    semanticScore: Optional[float] = Field(None, validation_alias="semantic_score")
    matchReasons: List[str] = Field(default_factory=list, validation_alias="match_reasons")
    concerns: List[str] = Field(default_factory=list, validation_alias="concerns")
    scoreBreakdown: Optional[dict] = Field(None, validation_alias="score_breakdown")
    status: str
    createdAt: str = Field(..., validation_alias="created_at")

    class Config:
        populate_by_name = True
        from_attributes = True


class MatchListResponse(BaseModel):
    """List of matches response."""

    matches: List[MatchResponse]
    total: int


class MatchingRunRequest(BaseModel):
    """Request to trigger matching run."""

    investorId: Optional[str] = Field(None, alias="investor_id")
    propertyId: Optional[str] = Field(None, alias="property_id")
    minScore: float = Field(30.0, alias="min_score")
    limit: int = 50

    class Config:
        populate_by_name = True


class MatchingRunResponse(BaseModel):
    """Response from matching run."""

    matchesCreated: int = Field(..., validation_alias="matches_created")
    propertiesEvaluated: Optional[int] = Field(None, validation_alias="properties_evaluated")
    investorsEvaluated: Optional[int] = Field(None, validation_alias="investors_evaluated")
    message: str

    class Config:
        populate_by_name = True


# ==================== Endpoints ====================


@router.get("/investors/{investor_id}/matches", response_model=MatchListResponse)
async def get_investor_matches(
    investor_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: float = Query(0.0, description="Minimum score filter"),
    limit: int = Query(50, le=100, description="Maximum results"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get matched deals for an investor.

    Returns deals that have been matched to this investor,
    sorted by final score descending.
    """
    query = (
        select(DealMatch)
        .where(DealMatch.investor_id == investor_id)
        .options(selectinload(DealMatch.matched_property))
    )

    if status:
        query = query.where(DealMatch.status == status)

    if min_score > 0:
        query = query.where(DealMatch.final_score >= min_score)

    query = query.order_by(DealMatch.final_score.desc()).limit(limit)

    result = await session.execute(query)
    matches = result.scalars().all()

    return MatchListResponse(
        matches=[
            MatchResponse(
                id=str(m.id),
                investor_id=str(m.investor_id),
                property_id=str(m.property_id),
                deal_name=m.matched_property.name if m.matched_property else None,
                final_score=float(m.final_score or m.similarity_score * 100),
                soft_score=float(m.soft_score) if m.soft_score else None,
                semantic_score=float(m.semantic_score) if m.semantic_score else None,
                match_reasons=m.match_reasons or [],
                concerns=m.concerns or [],
                score_breakdown=m.score_breakdown,
                status=m.status,
                created_at=m.created_at.isoformat(),
            )
            for m in matches
        ],
        total=len(matches),
    )


@router.get("/properties/{property_id}/matches", response_model=MatchListResponse)
async def get_property_matches(
    property_id: UUID,
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: float = Query(0.0, description="Minimum score filter"),
    limit: int = Query(50, le=100, description="Maximum results"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get matched investors for a deal.

    Returns investors that have been matched to this property,
    sorted by final score descending.
    """
    query = (
        select(DealMatch)
        .where(DealMatch.property_id == property_id)
        .options(selectinload(DealMatch.investor))
    )

    if status:
        query = query.where(DealMatch.status == status)

    if min_score > 0:
        query = query.where(DealMatch.final_score >= min_score)

    query = query.order_by(DealMatch.final_score.desc()).limit(limit)

    result = await session.execute(query)
    matches = result.scalars().all()

    return MatchListResponse(
        matches=[
            MatchResponse(
                id=str(m.id),
                investor_id=str(m.investor_id),
                property_id=str(m.property_id),
                investor_name=m.investor.name if m.investor else None,
                investor_phone=m.investor.phone if m.investor else None,
                final_score=float(m.final_score or m.similarity_score * 100),
                soft_score=float(m.soft_score) if m.soft_score else None,
                semantic_score=float(m.semantic_score) if m.semantic_score else None,
                match_reasons=m.match_reasons or [],
                concerns=m.concerns or [],
                score_breakdown=m.score_breakdown,
                status=m.status,
                created_at=m.created_at.isoformat(),
            )
            for m in matches
        ],
        total=len(matches),
    )


@router.get("/all", response_model=MatchListResponse)
async def get_all_matches(
    status: Optional[str] = Query(None, description="Filter by status"),
    min_score: float = Query(0.0, description="Minimum score filter"),
    limit: int = Query(100, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get all matches across the platform.

    Returns matches with both investor and deal details loaded,
    sorted by final score descending. Used by the admin matches dashboard.
    """
    query = select(DealMatch).options(
        selectinload(DealMatch.investor),
        selectinload(DealMatch.matched_property),
    )

    if status:
        query = query.where(DealMatch.status == status)

    if min_score > 0:
        query = query.where(DealMatch.final_score >= min_score)

    query = query.order_by(DealMatch.final_score.desc()).offset(offset).limit(limit)

    result = await session.execute(query)
    matches = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(DealMatch)
    if status:
        count_query = count_query.where(DealMatch.status == status)
    if min_score > 0:
        count_query = count_query.where(DealMatch.final_score >= min_score)
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    return MatchListResponse(
        matches=[
            MatchResponse(
                id=str(m.id),
                investor_id=str(m.investor_id),
                property_id=str(m.property_id),
                investor_name=m.investor.name if m.investor else None,
                investor_phone=m.investor.phone if m.investor else None,
                deal_name=m.matched_property.name if m.matched_property else None,
                final_score=float(m.final_score or m.similarity_score * 100),
                soft_score=float(m.soft_score) if m.soft_score else None,
                semantic_score=float(m.semantic_score) if m.semantic_score else None,
                match_reasons=m.match_reasons or [],
                concerns=m.concerns or [],
                score_breakdown=m.score_breakdown,
                status=m.status,
                created_at=m.created_at.isoformat(),
            )
            for m in matches
        ],
        total=total,
    )


@router.post("/run", response_model=MatchingRunResponse)
async def run_matching(
    request: MatchingRunRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Trigger a matching run.

    Can match:
    - A specific investor against all active properties
    - A specific property against all qualified investors
    - All properties against all investors (full run)
    """
    service = MatchingService(session)

    try:
        if request.investorId:
            # Match investor to properties
            results = await service.match_investor_to_properties(
                investor_id=UUID(request.investorId),
                min_score=request.minScore,
                limit=request.limit,
                save_matches=True,
            )
            await session.commit()

            return MatchingRunResponse(
                matches_created=len(results),
                message=f"Matched investor to {len(results)} properties",
            )

        elif request.propertyId:
            # Match property to investors
            results = await service.match_property_to_investors(
                property_id=UUID(request.propertyId),
                min_score=request.minScore,
                limit=request.limit,
                save_matches=True,
            )
            await session.commit()

            return MatchingRunResponse(
                matches_created=len(results),
                message=f"Matched property to {len(results)} investors",
            )

        else:
            # Full matching run
            stats = await service.run_full_matching(
                min_score=request.minScore,
                save_matches=True,
            )
            await session.commit()

            return MatchingRunResponse(
                matches_created=stats["matches_found"],
                properties_evaluated=stats["properties_evaluated"],
                investors_evaluated=stats["investors_evaluated"],
                message="Full matching run complete",
            )

    except Exception as e:
        logger.error(f"Matching run failed: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Matching failed: {str(e)}")


class MatchStatusUpdateRequest(BaseModel):
    """Request to update match status."""

    status: str
    investorResponse: Optional[str] = Field(None, validation_alias="investor_response")

    class Config:
        populate_by_name = True


@router.patch("/matches/{match_id}/status")
async def update_match_status(
    match_id: UUID,
    body: MatchStatusUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Update the status of a match.

    Valid statuses: pending, presented, accepted, rejected
    """
    valid_statuses = ["pending", "presented", "accepted", "rejected"]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}",
        )

    result = await session.execute(
        select(DealMatch).where(DealMatch.id == match_id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match.status = body.status
    if body.investorResponse:
        match.investor_response = body.investorResponse

    # Track presentation time
    if body.status == "presented" and not match.presented_at:
        from datetime import datetime

        match.presented_at = datetime.utcnow()

    if body.status in ["accepted", "rejected"]:
        match.investor_response = body.status

    await session.commit()

    return {"status": "updated", "match_id": str(match_id), "new_status": body.status}


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """Get details of a specific match."""
    result = await session.execute(
        select(DealMatch).where(DealMatch.id == match_id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return MatchResponse(
        id=str(match.id),
        investor_id=str(match.investor_id),
        property_id=str(match.property_id),
        final_score=float(match.final_score or match.similarity_score * 100),
        soft_score=float(match.soft_score) if match.soft_score else None,
        semantic_score=float(match.semantic_score) if match.semantic_score else None,
        match_reasons=match.match_reasons or [],
        concerns=match.concerns or [],
        score_breakdown=match.score_breakdown,
        status=match.status,
        created_at=match.created_at.isoformat(),
    )
