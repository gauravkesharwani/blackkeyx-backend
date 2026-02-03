"""Self-storage-specific extraction prompt supplement."""

SELF_STORAGE_SUPPLEMENT = """## Self-Storage-Specific Extraction

This is a SELF-STORAGE property. In addition to the common fields above, extract these self-storage-specific details:

### Facility Details
- Total units
- Net rentable square footage
- Climate-controlled percentage and unit count
- Drive-up unit count
- Average rent per SF
- Economic occupancy percentage
- Physical occupancy percentage
- Management platform/software (e.g., SiteLink, StorEDGE)
- RV/boat parking availability (yes/no)
- Average length of stay (months)
- Street rate growth percentage
- ECRI (existing customer rate increase) potential percentage

### Unit Mix
For EACH unit size category, extract:
- Unit size (e.g., 5x5, 10x10, 10x15, 10x20, 10x30)
- Number of units
- Monthly rate per unit
- Occupancy percentage for this size
- Whether climate-controlled

Look for unit mix tables, rate comparison sheets, occupancy reports, and revenue management data in the document."""
