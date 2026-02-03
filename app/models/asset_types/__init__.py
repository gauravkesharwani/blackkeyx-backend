"""Asset-type specific models for different commercial property classes."""

from app.models.asset_types.hotel import HotelDetails, HotelRoomMix
from app.models.asset_types.industrial import IndustrialDetails, IndustrialTenant
from app.models.asset_types.land import LandDetails
from app.models.asset_types.mixed_use import MixedUseComponent, MixedUseDetails
from app.models.asset_types.multifamily import MultifamilyDetails, MultifamilyUnitMix
from app.models.asset_types.office import OfficeDetails, OfficeTenant
from app.models.asset_types.retail import RetailDetails, RetailTenant
from app.models.asset_types.self_storage import SelfStorageDetails, SelfStorageUnitMix
from app.models.asset_types.student_housing import StudentHousingDetails

__all__ = [
    # Industrial
    "IndustrialDetails",
    "IndustrialTenant",
    # Multifamily
    "MultifamilyDetails",
    "MultifamilyUnitMix",
    # Retail
    "RetailDetails",
    "RetailTenant",
    # Office
    "OfficeDetails",
    "OfficeTenant",
    # Self Storage
    "SelfStorageDetails",
    "SelfStorageUnitMix",
    # Student Housing
    "StudentHousingDetails",
    # Hotel
    "HotelDetails",
    "HotelRoomMix",
    # Land
    "LandDetails",
    # Mixed Use
    "MixedUseDetails",
    "MixedUseComponent",
]
