"""Retail-specific extraction prompt supplement."""

RETAIL_SUPPLEMENT = """## Retail-Specific Extraction

This is a RETAIL property. In addition to the common fields above, extract these retail-specific details:

### Center Details
- Gross leasable area (GLA)
- Anchor tenant percentage of GLA
- Number of inline tenants
- Average inline rent per SF
- CAM rate per SF
- Number of tenants paying percentage rent
- Daily traffic count (if available)
- Average sales per SF
- Parking ratio (spaces per 1,000 SF)
- Number of pad sites
- Number of outparcels
- Whether center is grocery-anchored (yes/no)
- Lease type (NNN, modified gross, gross)
- Number of below-market leases

### Retail Tenant Roll
For EACH tenant, extract:
- Tenant name
- Category (anchor, junior anchor, inline, pad site)
- Square footage
- Annual rent and rent per SF
- Lease expiration date
- Renewal options
- Whether tenant pays percentage rent
- Sales per SF (if available)
- Whether tenant has a co-tenancy clause

Look for tenant schedules, rent roll, sales reports, and lease expiration schedules in the document."""
