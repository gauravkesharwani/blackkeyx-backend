"""Mixed-use-specific extraction prompt supplement."""

MIXED_USE_SUPPLEMENT = """## Mixed-Use-Specific Extraction

This is a MIXED-USE property. In addition to the common fields above, extract these mixed-use-specific details:

### Property Details
- Component types (list of: retail, office, residential, hotel, etc.)
- Retail percentage of total area
- Office percentage of total area
- Residential percentage of total area
- Parking structure type (surface, garage, underground)
- Shared amenities list
- Whether property has a master lease (yes/no)
- Ground floor use type
- Description of synergies between components

### Component Breakdown
For EACH component, extract:
- Component type (retail, office, residential, etc.)
- Square footage
- NOI (net operating income)
- Occupancy percentage

Look for component-by-component P&L breakdowns, shared cost allocations, parking revenue analyses, and cross-component synergy discussions in the document."""
