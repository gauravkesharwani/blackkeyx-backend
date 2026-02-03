"""
Asset-type-specific extraction prompts.

Each asset type has a supplemental prompt that extends the base prompt
with asset-specific extraction instructions.
"""

from app.services.extraction_prompts.base_prompt import BASE_EXTRACTION_PROMPT
from app.services.extraction_prompts.hotel_prompt import HOTEL_SUPPLEMENT
from app.services.extraction_prompts.industrial_prompt import INDUSTRIAL_SUPPLEMENT
from app.services.extraction_prompts.land_prompt import LAND_SUPPLEMENT
from app.services.extraction_prompts.mixed_use_prompt import MIXED_USE_SUPPLEMENT
from app.services.extraction_prompts.multifamily_prompt import MULTIFAMILY_SUPPLEMENT
from app.services.extraction_prompts.office_prompt import OFFICE_SUPPLEMENT
from app.services.extraction_prompts.retail_prompt import RETAIL_SUPPLEMENT
from app.services.extraction_prompts.self_storage_prompt import SELF_STORAGE_SUPPLEMENT
from app.services.extraction_prompts.student_housing_prompt import STUDENT_HOUSING_SUPPLEMENT

_SUPPLEMENT_MAP: dict[str, str] = {
    "industrial": INDUSTRIAL_SUPPLEMENT,
    "multifamily": MULTIFAMILY_SUPPLEMENT,
    "retail": RETAIL_SUPPLEMENT,
    "office": OFFICE_SUPPLEMENT,
    "self-storage": SELF_STORAGE_SUPPLEMENT,
    "student-housing": STUDENT_HOUSING_SUPPLEMENT,
    "hotel": HOTEL_SUPPLEMENT,
    "land": LAND_SUPPLEMENT,
    "mixed-use": MIXED_USE_SUPPLEMENT,
}


def get_extraction_prompt(deal_type: str) -> str:
    """Return the full extraction prompt for a given deal type.

    Combines the base prompt with the asset-type-specific supplement.
    Falls back to just the base prompt for unknown types.
    """
    supplement = _SUPPLEMENT_MAP.get(deal_type, "")
    if supplement:
        return f"{BASE_EXTRACTION_PROMPT}\n\n{supplement}"
    return BASE_EXTRACTION_PROMPT
