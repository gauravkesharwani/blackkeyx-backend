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

Look for component-by-component P&L breakdowns, shared cost allocations, parking revenue analyses, and cross-component synergy discussions in the document.

### Major Tenants / Rent Roll
IMPORTANT: Extract ALL individual tenants from the commercial rent roll, retail tenant list, or any tenant schedule in the document. For each tenant extract:
- Tenant name
- Square footage leased
- Annual rent (base rent)
- Lease expiration date
- Tenant type (national, regional, local)

### Pro-Forma / Financial Projections
If the document contains a pro-forma operating statement, extract the financial data as annual projections:
- Use "Current Pro Forma" as Year 1 and "Stabilized Pro Forma" as Year 2 if those are the available scenarios
- Extract gross revenue (Effective Gross Income), operating expenses, and NOI for each scenario
- For offering memorandums (OMs), sponsor fees and waterfall structures are typically not included — use null for those fields if not found"""
