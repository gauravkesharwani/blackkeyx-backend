"""Office-specific extraction prompt supplement."""

OFFICE_SUPPLEMENT = """## Office-Specific Extraction

This is an OFFICE property. In addition to the common fields above, extract these office-specific details:

### Building Details
- Building class (A, B, or C)
- Number of floors
- Typical floor plate size (SF)
- Net rentable area (NRA)
- Total tenant count
- Weighted average lease term (WALT) in years
- Average rent per SF (NNN basis)
- Average rent per SF (Full Service Gross basis)
- Standard TI allowance per SF
- Parking ratio (spaces per 1,000 SF)
- Building amenities (lobby, fitness, conference, etc.)
- LEED certification level (if any)
- Energy Star score (if available)
- Largest tenant as percentage of NRA
- Near-term lease expirations (% expiring within 2 years)
- Sublease space (SF)

### Office Tenant Roll
For EACH tenant, extract:
- Tenant name
- Square footage
- Annual rent and rent per SF
- Lease start and expiration dates
- Renewal options
- TI allowance per SF
- Credit rating

Look for rent rolls, lease expiration schedules, stacking plans, and tenant improvement schedules in the document."""
