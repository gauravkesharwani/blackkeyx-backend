"""Self-storage asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class SelfStorageDetailsExtraction(BaseModel):
    """Self-storage-specific property details."""

    total_units: Optional[int] = Field(None, description="Total number of units")
    net_rentable_sf: Optional[int] = Field(None, description="Net rentable square footage")
    climate_controlled_pct: Optional[float] = Field(None, description="Percentage of units that are climate-controlled")
    climate_controlled_units: Optional[int] = Field(None, description="Number of climate-controlled units")
    drive_up_units: Optional[int] = Field(None, description="Number of drive-up units")
    avg_rent_per_sf: Optional[float] = Field(None, description="Average rent per SF")
    economic_occupancy: Optional[float] = Field(None, description="Economic occupancy percentage")
    physical_occupancy: Optional[float] = Field(None, description="Physical occupancy percentage")
    management_platform: Optional[str] = Field(None, description="Management platform/software")
    rv_boat_parking: Optional[bool] = Field(None, description="Whether facility has RV/boat parking")
    avg_length_of_stay: Optional[float] = Field(None, description="Average length of stay in months")
    street_rate_growth: Optional[float] = Field(None, description="Street rate growth percentage")
    ecri_potential: Optional[float] = Field(None, description="Existing customer rate increase potential percentage")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class SelfStorageUnitMixExtraction(BaseModel):
    """Self-storage unit mix entry."""

    unit_size: str = Field(..., description="Unit size (e.g., '5x5', '10x10', '10x20')")
    unit_count: Optional[int] = Field(None, description="Number of this unit type")
    rate_per_unit: Optional[float] = Field(None, description="Monthly rate per unit")
    occupancy_pct: Optional[float] = Field(None, description="Occupancy percentage for this size")
    climate_controlled: Optional[bool] = Field(None, description="Whether units are climate-controlled")


class SelfStorageExtraction(InvestorBriefExtraction):
    """Self-storage asset extraction schema extending base."""

    self_storage_details: Optional[SelfStorageDetailsExtraction] = Field(
        None, description="Self-storage-specific property details"
    )
    self_storage_unit_mix: List[SelfStorageUnitMixExtraction] = Field(
        default_factory=list, description="Unit mix breakdown"
    )
