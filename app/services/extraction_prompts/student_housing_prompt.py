"""Student-housing-specific extraction prompt supplement."""

STUDENT_HOUSING_SUPPLEMENT = """## Student Housing-Specific Extraction

This is a STUDENT HOUSING property. In addition to the common fields above, extract these student-housing-specific details:

### Property Details
- Total beds
- Total units
- Average beds per unit
- Monthly rent per bed
- Monthly rent per unit
- Distance to campus (walking, driving, or transit time)
- Affiliated university name
- University enrollment count
- Pre-leasing percentage (for upcoming term)
- Pre-leasing velocity description
- Amenities list (study rooms, computer lab, pool, shuttle, etc.)
- Whether units are furnished (yes/no)
- Whether utilities are included (yes/no)
- Whether leases are individual/by-the-bed (yes/no)
- Description of on-campus housing competition

Look for pre-leasing reports, university enrollment data, competitive surveys, and bed/unit mix tables in the document."""
