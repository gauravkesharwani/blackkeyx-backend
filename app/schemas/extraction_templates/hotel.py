"""Hotel asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class HotelDetailsExtraction(BaseModel):
    """Hotel-specific property details."""

    room_count: Optional[int] = Field(None, description="Total number of rooms")
    avg_room_size: Optional[float] = Field(None, description="Average room size in SF")
    adr: Optional[float] = Field(None, description="Average daily rate")
    revpar: Optional[float] = Field(None, description="Revenue per available room")
    occupancy_rate: Optional[float] = Field(None, description="Occupancy rate percentage")
    franchise_brand: Optional[str] = Field(None, description="Franchise/brand name")
    franchise_expiration: Optional[str] = Field(None, description="Franchise agreement expiration")
    management_company: Optional[str] = Field(None, description="Management company name")
    fnb_revenue: Optional[float] = Field(None, description="Food & beverage revenue in USD")
    fnb_pct: Optional[float] = Field(None, description="F&B as percentage of total revenue")
    meeting_space_sf: Optional[int] = Field(None, description="Meeting/event space in SF")
    star_rating: Optional[float] = Field(None, description="Star rating (1-5)")
    trip_advisor_score: Optional[float] = Field(None, description="TripAdvisor score")
    pip_required: Optional[bool] = Field(None, description="Whether a PIP is required")
    pip_cost: Optional[float] = Field(None, description="PIP cost in USD")
    goppar: Optional[float] = Field(None, description="Gross operating profit per available room")
    comp_set_penetration: Optional[float] = Field(None, description="Competitive set penetration index")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class HotelRoomMixExtraction(BaseModel):
    """Hotel room mix entry."""

    room_type: str = Field(..., description="Room type (e.g., 'Standard King', 'Suite')")
    room_count: Optional[int] = Field(None, description="Number of rooms of this type")
    avg_size_sf: Optional[float] = Field(None, description="Average room size in SF")
    rate: Optional[float] = Field(None, description="Rack rate for this room type")


class HotelExtraction(InvestorBriefExtraction):
    """Hotel asset extraction schema extending base."""

    hotel_details: Optional[HotelDetailsExtraction] = Field(
        None, description="Hotel-specific property details"
    )
    hotel_room_mix: List[HotelRoomMixExtraction] = Field(
        default_factory=list, description="Room mix breakdown"
    )
