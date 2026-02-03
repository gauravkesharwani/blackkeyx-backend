"""Land asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class LandDetailsExtraction(BaseModel):
    """Land-specific property details."""

    acreage: Optional[float] = Field(None, description="Total acreage")
    zoning: Optional[str] = Field(None, description="Current zoning designation")
    entitled: Optional[bool] = Field(None, description="Whether the land is entitled")
    entitlement_status: Optional[str] = Field(None, description="Entitlement status description")
    approved_density: Optional[str] = Field(None, description="Approved density (units/acre or FAR)")
    approved_use: Optional[str] = Field(None, description="Approved use description")
    topography: Optional[str] = Field(None, description="Topography description")
    utilities_available: List[str] = Field(default_factory=list, description="Available utilities")
    environmental_status: Optional[str] = Field(None, description="Environmental assessment status")
    flood_zone: Optional[str] = Field(None, description="Flood zone designation")
    development_timeline: Optional[str] = Field(None, description="Expected development timeline")
    comparable_land_sales: Optional[str] = Field(None, description="Comparable land sales data")
    impact_fees: Optional[float] = Field(None, description="Impact fees in USD")
    infrastructure_costs: Optional[float] = Field(None, description="Infrastructure costs in USD")
    absorption_projection: Optional[str] = Field(None, description="Absorption projection narrative")


class LandExtraction(InvestorBriefExtraction):
    """Land asset extraction schema extending base."""

    land_details: Optional[LandDetailsExtraction] = Field(
        None, description="Land-specific property details"
    )
