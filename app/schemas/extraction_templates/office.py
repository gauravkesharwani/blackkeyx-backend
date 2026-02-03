"""Office asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class OfficeDetailsExtraction(BaseModel):
    """Office-specific property details."""

    building_class: Optional[str] = Field(None, description="Building class (A, B, C)")
    floor_count: Optional[int] = Field(None, description="Number of floors")
    typical_floor_plate: Optional[int] = Field(None, description="Typical floor plate size in SF")
    nra: Optional[int] = Field(None, description="Net rentable area in SF")
    tenant_count: Optional[int] = Field(None, description="Total number of tenants")
    walt_years: Optional[float] = Field(None, description="Weighted average lease term in years")
    avg_rent_psf_nnn: Optional[float] = Field(None, description="Average rent per SF (NNN)")
    avg_rent_psf_fsg: Optional[float] = Field(None, description="Average rent per SF (Full Service Gross)")
    ti_allowance_psf: Optional[float] = Field(None, description="Tenant improvement allowance per SF")
    parking_ratio: Optional[float] = Field(None, description="Parking ratio (spaces per 1000 SF)")
    building_amenities: List[str] = Field(default_factory=list, description="Building amenities")
    leed_certification: Optional[str] = Field(None, description="LEED certification level")
    energy_star_score: Optional[int] = Field(None, description="Energy Star score")
    largest_tenant_pct: Optional[float] = Field(None, description="Largest tenant as percentage of NRA")
    near_term_expirations_pct: Optional[float] = Field(None, description="Percentage of leases expiring within 2 years")
    sublease_space_sf: Optional[int] = Field(None, description="Sublease space in SF")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class OfficeTenantExtraction(BaseModel):
    """Office tenant details."""

    tenant_name: str = Field(..., description="Tenant name")
    square_feet: Optional[int] = Field(None, description="Leased square footage")
    annual_rent: Optional[float] = Field(None, description="Annual rent in USD")
    rent_per_sf: Optional[float] = Field(None, description="Rent per SF")
    lease_start: Optional[str] = Field(None, description="Lease start date")
    lease_expiration: Optional[str] = Field(None, description="Lease expiration date")
    renewal_options: Optional[str] = Field(None, description="Renewal option terms")
    ti_allowance: Optional[float] = Field(None, description="TI allowance per SF")
    credit_rating: Optional[str] = Field(None, description="Tenant credit rating")


class OfficeExtraction(InvestorBriefExtraction):
    """Office asset extraction schema extending base."""

    office_details: Optional[OfficeDetailsExtraction] = Field(
        None, description="Office-specific property details"
    )
    office_tenants: List[OfficeTenantExtraction] = Field(
        default_factory=list, description="Office tenant roll"
    )
