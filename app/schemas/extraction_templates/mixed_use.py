"""Mixed-use asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class MixedUseDetailsExtraction(BaseModel):
    """Mixed-use-specific property details."""

    component_types: List[str] = Field(default_factory=list, description="Component types (e.g., 'retail', 'office', 'residential')")
    retail_pct: Optional[float] = Field(None, description="Retail percentage of total")
    office_pct: Optional[float] = Field(None, description="Office percentage of total")
    residential_pct: Optional[float] = Field(None, description="Residential percentage of total")
    parking_structure: Optional[str] = Field(None, description="Parking structure type")
    shared_amenities: List[str] = Field(default_factory=list, description="Shared amenities")
    master_lease: Optional[bool] = Field(None, description="Whether property has a master lease")
    ground_floor_use: Optional[str] = Field(None, description="Ground floor use type")
    synergy_description: Optional[str] = Field(None, description="Description of component synergies")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class MixedUseComponentExtraction(BaseModel):
    """Mixed-use component entry."""

    component_type: str = Field(..., description="Component type (e.g., 'retail', 'office', 'residential')")
    square_feet: Optional[int] = Field(None, description="Component square footage")
    noi: Optional[float] = Field(None, description="Component NOI in USD")
    occupancy: Optional[float] = Field(None, description="Component occupancy percentage")


class MixedUseExtraction(InvestorBriefExtraction):
    """Mixed-use asset extraction schema extending base."""

    mixed_use_details: Optional[MixedUseDetailsExtraction] = Field(
        None, description="Mixed-use-specific property details"
    )
    mixed_use_components: List[MixedUseComponentExtraction] = Field(
        default_factory=list, description="Component breakdown"
    )
