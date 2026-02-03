"""Retail asset extraction schema."""

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.extraction import InvestorBriefExtraction


class RetailDetailsExtraction(BaseModel):
    """Retail-specific property details."""

    gla: Optional[int] = Field(None, description="Gross leasable area in SF")
    anchor_pct_gla: Optional[float] = Field(None, description="Anchor tenant percentage of GLA")
    inline_tenant_count: Optional[int] = Field(None, description="Number of inline tenants")
    avg_inline_rent_psf: Optional[float] = Field(None, description="Average inline rent per SF")
    cam_rate_psf: Optional[float] = Field(None, description="CAM rate per SF")
    percentage_rent_tenants: Optional[int] = Field(None, description="Number of tenants paying percentage rent")
    traffic_count: Optional[int] = Field(None, description="Daily traffic count")
    sales_psf: Optional[float] = Field(None, description="Average sales per SF")
    parking_ratio: Optional[float] = Field(None, description="Parking ratio (spaces per 1000 SF)")
    pad_sites: Optional[int] = Field(None, description="Number of pad sites")
    outparcels: Optional[int] = Field(None, description="Number of outparcels")
    grocery_anchored: Optional[bool] = Field(None, description="Whether center is grocery-anchored")
    nnn_vs_gross: Optional[str] = Field(None, description="Lease type (NNN, modified gross, gross)")
    below_market_leases: Optional[int] = Field(None, description="Number of below-market leases")
    year_built: Optional[int] = Field(None, description="Year built")
    year_renovated: Optional[int] = Field(None, description="Year renovated")


class RetailTenantExtraction(BaseModel):
    """Retail tenant details."""

    tenant_name: str = Field(..., description="Tenant name")
    tenant_category: Optional[str] = Field(None, description="Category (anchor, inline, pad site)")
    square_feet: Optional[int] = Field(None, description="Leased square footage")
    annual_rent: Optional[float] = Field(None, description="Annual rent in USD")
    rent_per_sf: Optional[float] = Field(None, description="Rent per SF")
    lease_expiration: Optional[str] = Field(None, description="Lease expiration date")
    renewal_options: Optional[str] = Field(None, description="Renewal option terms")
    percentage_rent: Optional[bool] = Field(None, description="Whether tenant pays percentage rent")
    sales_psf: Optional[float] = Field(None, description="Tenant sales per SF")
    co_tenancy_clause: Optional[bool] = Field(None, description="Whether tenant has co-tenancy clause")


class RetailExtraction(InvestorBriefExtraction):
    """Retail asset extraction schema extending base."""

    retail_details: Optional[RetailDetailsExtraction] = Field(
        None, description="Retail-specific property details"
    )
    retail_tenants: List[RetailTenantExtraction] = Field(
        default_factory=list, description="Retail tenant roll"
    )
