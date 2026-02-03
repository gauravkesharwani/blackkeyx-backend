"""Industrial-specific extraction prompt supplement."""

INDUSTRIAL_SUPPLEMENT = """## Industrial-Specific Extraction

This is an INDUSTRIAL property. In addition to the common fields above, extract these industrial-specific details:

### Building Specifications
- Clear height (minimum and maximum, in feet)
- Loading docks (count)
- Drive-in doors (count)
- Dock height (feet)
- Truck court depth (feet)
- Column spacing (e.g., "50x50", "60x60")
- Rail access (yes/no)
- Power: amperage and voltage
- Crane capacity (tons)
- Sprinkler system type (ESFR, wet, dry)
- Office percentage of total building area
- Trailer parking spaces
- Cross-dock capability (yes/no)
- Freezer/cooler square footage

### Industrial Tenant Roll
For EACH tenant, extract:
- Tenant name
- Square footage occupied
- Annual rent and rent per SF
- Lease start and expiration dates
- Renewal options and terms
- Credit rating (S&P, Moody's, or D&B)
- Years at this location
- Whether the facility is mission-critical to the tenant's operations
- Distance from tenant's headquarters
- Tenant type (national, regional, local, e-commerce, manufacturing, logistics)

Look for rent roll tables, tenant schedules, and lease abstracts in the document."""
