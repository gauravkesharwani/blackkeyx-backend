"""Student housing asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class StudentHousingDetailsExtraction(BaseModel):
    """Student-housing-specific property details."""

    total_beds: Optional[int] = Field(None, description="Total number of beds")
    total_units: Optional[int] = Field(None, description="Total number of units")
    beds_per_unit_avg: Optional[float] = Field(None, description="Average beds per unit")
    rent_per_bed: Optional[float] = Field(None, description="Monthly rent per bed")
    rent_per_unit: Optional[float] = Field(None, description="Monthly rent per unit")
    distance_to_campus: Optional[str] = Field(None, description="Distance to campus")
    affiliated_university: Optional[str] = Field(None, description="Affiliated university name")
    university_enrollment: Optional[int] = Field(None, description="University enrollment count")
    preleasing_pct: Optional[float] = Field(None, description="Pre-leasing percentage")
    preleasing_velocity: Optional[str] = Field(None, description="Pre-leasing velocity description")
    amenities: List[str] = Field(default_factory=list, description="Property amenities")
    furnished: Optional[bool] = Field(None, description="Whether units are furnished")
    utilities_included: Optional[bool] = Field(None, description="Whether utilities are included")
    individual_leases: Optional[bool] = Field(None, description="Whether leases are by-the-bed")
    on_campus_competition: Optional[str] = Field(None, description="Description of on-campus competition")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class StudentHousingExtraction(InvestorBriefExtraction):
    """Student housing asset extraction schema extending base."""

    student_housing_details: Optional[StudentHousingDetailsExtraction] = Field(
        None, description="Student-housing-specific property details"
    )
