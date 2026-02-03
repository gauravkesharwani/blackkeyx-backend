"""Multifamily-specific extraction prompt supplement."""

MULTIFAMILY_SUPPLEMENT = """## Multifamily-Specific Extraction

This is a MULTIFAMILY property. In addition to the common fields above, extract these multifamily-specific details:

### Property Details
- Total unit count
- Average unit size (SF)
- Average rent per unit and per SF
- In-place occupancy percentage
- Market rent per unit (for loss-to-lease calculation)
- Loss-to-lease percentage
- Amenities list (pool, gym, clubhouse, etc.)
- Washer/dryer configuration (in-unit, hookups, shared laundry)
- Property vintage/class
- Recent renovations description
- Renovation premium (rent increase for renovated units)
- Current concessions
- Annual turnover rate percentage
- Operating expense ratio

### Unit Mix
For EACH unit type, extract:
- Unit type (Studio, 1BR/1BA, 2BR/2BA, 3BR/2BA, etc.)
- Number of units
- Average square footage
- Current rent
- Market rent

Look for unit mix tables, rent comparables, and operating pro forma sections in the document."""
