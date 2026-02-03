"""Land-specific extraction prompt supplement."""

LAND_SUPPLEMENT = """## Land-Specific Extraction

This is a LAND deal. In addition to the common fields above, extract these land-specific details:

### Parcel Details
- Total acreage
- Current zoning designation
- Whether the land is entitled (yes/no)
- Entitlement status description
- Approved density (units per acre or FAR)
- Approved use description
- Topography description (flat, sloped, etc.)
- Available utilities (water, sewer, electric, gas, fiber)
- Environmental assessment status (Phase I/II results)
- Flood zone designation (Zone X, AE, etc.)
- Expected development timeline
- Comparable land sales data
- Impact fees (total estimated)
- Infrastructure costs (roads, utilities, etc.)
- Absorption projection for planned development

Look for zoning maps, entitlement documents, environmental reports, site plans, development pro formas, and comparable land sales in the document."""
