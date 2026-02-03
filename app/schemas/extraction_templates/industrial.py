"""Industrial asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class IndustrialDetailsExtraction(BaseModel):
    """Industrial-specific property details."""

    clear_height_min: Optional[float] = Field(None, description="Minimum clear height in feet")
    clear_height_max: Optional[float] = Field(None, description="Maximum clear height in feet")
    loading_docks: Optional[int] = Field(None, description="Number of loading docks")
    drive_in_doors: Optional[int] = Field(None, description="Number of drive-in doors")
    dock_height: Optional[float] = Field(None, description="Dock height in feet")
    truck_court_depth: Optional[float] = Field(None, description="Truck court depth in feet")
    column_spacing: Optional[str] = Field(None, description="Column spacing (e.g., '50x50')")
    rail_access: Optional[bool] = Field(None, description="Whether property has rail access")
    power_amps: Optional[int] = Field(None, description="Electrical service amperage")
    power_voltage: Optional[int] = Field(None, description="Electrical service voltage")
    crane_capacity: Optional[float] = Field(None, description="Crane capacity in tons")
    sprinkler_system: Optional[str] = Field(None, description="Sprinkler system type (e.g., 'ESFR', 'wet', 'dry')")
    office_pct: Optional[float] = Field(None, description="Percentage of building that is office space")
    trailer_parking: Optional[int] = Field(None, description="Number of trailer parking spaces")
    cross_dock: Optional[bool] = Field(None, description="Whether building is cross-dock capable")
    freezer_cooler_sf: Optional[int] = Field(None, description="Freezer/cooler square footage")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class IndustrialTenantExtraction(BaseModel):
    """Industrial tenant details."""

    tenant_name: str = Field(..., description="Tenant name")
    square_feet: Optional[int] = Field(None, description="Leased square footage")
    annual_rent: Optional[float] = Field(None, description="Annual rent in USD")
    rent_per_sf: Optional[float] = Field(None, description="Rent per square foot")
    lease_start: Optional[str] = Field(None, description="Lease start date")
    lease_expiration: Optional[str] = Field(None, description="Lease expiration date")
    renewal_options: Optional[str] = Field(None, description="Renewal option terms")
    renewal_option_terms: Optional[str] = Field(None, description="Detailed renewal terms")
    credit_rating: Optional[str] = Field(None, description="Tenant credit rating")
    years_at_location: Optional[int] = Field(None, description="Years at this location")
    is_mission_critical: Optional[bool] = Field(None, description="Whether facility is mission-critical to tenant")
    distance_from_hq: Optional[str] = Field(None, description="Distance from tenant's headquarters")
    tenant_type: Optional[str] = Field(None, description="Tenant type (national, regional, local)")


class IndustrialExtraction(InvestorBriefExtraction):
    """Industrial asset extraction schema extending base."""

    industrial_details: Optional[IndustrialDetailsExtraction] = Field(
        None, description="Industrial-specific property details"
    )
    industrial_tenants: List[IndustrialTenantExtraction] = Field(
        default_factory=list, description="Industrial tenant roll"
    )
