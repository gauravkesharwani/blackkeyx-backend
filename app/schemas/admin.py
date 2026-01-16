"""
Admin dashboard schemas.

Maps to frontend API response shapes from:
- /api/admin/stats
- /api/admin/leads filters
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ActivityItem(BaseModel):
    """Single activity item for recent activity feed."""

    id: str
    type: str  # 'new_lead', 'stage_change', 'deal_matched', etc.
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminStatsResponse(BaseModel):
    """
    Admin dashboard statistics response.

    Maps to mock response from /api/admin/stats:
    {
      totalLeads: number,
      byStage: Record<PipelineStage, number>,
      averageScore: number,
      totalDeals: number,
      recentActivity: ActivityItem[]
    }
    """

    totalLeads: int
    byStage: Dict[str, int]
    averageScore: float
    totalDeals: int
    recentActivity: List[ActivityItem]


class LeadFilters(BaseModel):
    """
    Lead filter parameters.

    Maps to LeadFilters from frontend:
    interface LeadFilters {
      stage?: PipelineStage
      scoreMin?: number
      scoreMax?: number
      capitalMin?: number
      capitalMax?: number
      dateFrom?: string
      dateTo?: string
      search?: string
      sortBy?: 'created_at' | 'lead_score' | 'capital_available'
      sortOrder?: 'asc' | 'desc'
      page?: number
      pageSize?: number
    }
    """

    stage: Optional[str] = None
    scoreMin: Optional[int] = Field(None, alias="score_min")
    scoreMax: Optional[int] = Field(None, alias="score_max")
    capitalMin: Optional[int] = Field(None, alias="capital_min")
    capitalMax: Optional[int] = Field(None, alias="capital_max")
    dateFrom: Optional[str] = Field(None, alias="date_from")
    dateTo: Optional[str] = Field(None, alias="date_to")
    search: Optional[str] = None
    sortBy: str = Field("created_at", alias="sort_by")
    sortOrder: str = Field("desc", alias="sort_order")
    page: int = 1
    pageSize: int = Field(20, alias="page_size")

    model_config = ConfigDict(populate_by_name=True)


class AuthRequest(BaseModel):
    """Admin authentication request."""

    password: str


class AuthResponse(BaseModel):
    """Admin authentication response."""

    success: bool
    message: str
