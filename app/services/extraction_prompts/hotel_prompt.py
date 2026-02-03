"""Hotel-specific extraction prompt supplement."""

HOTEL_SUPPLEMENT = """## Hotel-Specific Extraction

This is a HOTEL property. In addition to the common fields above, extract these hotel-specific details:

### Property Details
- Total room count
- Average room size (SF)
- ADR (average daily rate)
- RevPAR (revenue per available room)
- Occupancy rate percentage
- Franchise/brand name
- Franchise agreement expiration date
- Management company name
- Food & beverage revenue and as percentage of total revenue
- Meeting/event space (SF)
- Star rating (1-5)
- TripAdvisor score (if available)
- PIP (Property Improvement Plan) required (yes/no)
- PIP estimated cost
- GOPPAR (gross operating profit per available room)
- Competitive set penetration index

### Room Mix
For EACH room type, extract:
- Room type (Standard King, Double Queen, Suite, etc.)
- Number of rooms
- Average size (SF)
- Rack rate

Look for STR reports, competitive set analysis, P&L statements, PIP estimates, franchise documents, and management agreements in the document."""
