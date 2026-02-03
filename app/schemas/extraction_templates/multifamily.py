"""Multifamily asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class MultifamilyDetailsExtraction(BaseModel):
    """Multifamily-specific property details."""

    unit_count: Optional[int] = Field(None, description="Total number of units")
    avg_unit_size: Optional[float] = Field(None, description="Average unit size in SF")
    avg_rent_per_unit: Optional[float] = Field(None, description="Average rent per unit")
    avg_rent_per_sf: Optional[float] = Field(None, description="Average rent per SF")
    in_place_occupancy: Optional[float] = Field(None, description="In-place occupancy percentage")
    market_rent_per_unit: Optional[float] = Field(None, description="Market rent per unit")
    loss_to_lease_pct: Optional[float] = Field(None, description="Loss-to-lease percentage")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    washer_dryer: Optional[str] = Field(None, description="Washer/dryer configuration (in-unit, hookups, shared)")
    vintage: Optional[str] = Field(None, description="Property vintage (e.g., '1980s', 'Class B')")
    recent_renovations: Optional[str] = Field(None, description="Description of recent renovations")
    renovation_premium: Optional[float] = Field(None, description="Rent premium for renovated units")
    concessions: Optional[str] = Field(None, description="Current concessions offered")
    turnover_rate: Optional[float] = Field(None, description="Annual turnover rate percentage")
    expense_ratio: Optional[float] = Field(None, description="Operating expense ratio percentage")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class MultifamilyUnitMixExtraction(BaseModel):
    """Multifamily unit mix entry."""

    unit_type: str = Field(..., description="Unit type (e.g., 'Studio', '1BR', '2BR/2BA')")
    unit_count: Optional[int] = Field(None, description="Number of this unit type")
    avg_sf: Optional[float] = Field(None, description="Average square footage")
    current_rent: Optional[float] = Field(None, description="Current rent")
    market_rent: Optional[float] = Field(None, description="Market rent")


class MultifamilyExtraction(InvestorBriefExtraction):
    """Multifamily asset extraction schema extending base."""

    multifamily_details: Optional[MultifamilyDetailsExtraction] = Field(
        None, description="Multifamily-specific property details"
    )
    multifamily_unit_mix: List[MultifamilyUnitMixExtraction] = Field(
        default_factory=list, description="Unit mix breakdown"
    )
