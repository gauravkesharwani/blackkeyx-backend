"""
Asset-type-specific extraction schemas.

Each asset type extends the base InvestorBriefExtraction with
asset-specific detail and tenant/unit-mix fields.
"""

from typing import Type

from app.schemas.extraction import InvestorBriefExtraction

from app.schemas.extraction_templates.hotel import HotelExtraction
from app.schemas.extraction_templates.industrial import IndustrialExtraction
from app.schemas.extraction_templates.land import LandExtraction
from app.schemas.extraction_templates.mixed_use import MixedUseExtraction
from app.schemas.extraction_templates.multifamily import MultifamilyExtraction
from app.schemas.extraction_templates.office import OfficeExtraction
from app.schemas.extraction_templates.retail import RetailExtraction
from app.schemas.extraction_templates.self_storage import SelfStorageExtraction
from app.schemas.extraction_templates.student_housing import StudentHousingExtraction

_SCHEMA_MAP: dict[str, Type[InvestorBriefExtraction]] = {
    "industrial": IndustrialExtraction,
    "multifamily": MultifamilyExtraction,
    "retail": RetailExtraction,
    "office": OfficeExtraction,
    "self-storage": SelfStorageExtraction,
    "student-housing": StudentHousingExtraction,
    "hotel": HotelExtraction,
    "land": LandExtraction,
    "mixed-use": MixedUseExtraction,
}


def get_extraction_schema(deal_type: str) -> Type[InvestorBriefExtraction]:
    """Return the extraction schema class for a given deal type.

    Falls back to the base InvestorBriefExtraction for unknown types.
    """
    return _SCHEMA_MAP.get(deal_type, InvestorBriefExtraction)


__all__ = [
    "get_extraction_schema",
    "IndustrialExtraction",
    "MultifamilyExtraction",
    "RetailExtraction",
    "OfficeExtraction",
    "SelfStorageExtraction",
    "StudentHousingExtraction",
    "HotelExtraction",
    "LandExtraction",
    "MixedUseExtraction",
]
