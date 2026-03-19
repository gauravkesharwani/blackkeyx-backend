"""SQLAlchemy models for BlackKeyX."""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.consent import Consent, LeadNote, StageHistory
from app.models.deal_structure import Reserve, SponsorFees, WaterfallStructure
from app.models.embeddings import InvestorEmbedding, PropertyEmbedding
from app.models.financial import AnnualProjection, Financing, InvestmentMetrics
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.market import MarketAnalysis
from app.models.matching import DealMatch
from app.models.property import Deal, MajorTenant, Property, PropertyDocument
from app.models.voice import CallSession, CallTranscript
from app.models.investor_portal import (
    InvestorUser,
    InvestorSubscription,
    InvestorDeal,
    DealChunk,
    InvestorChatSession,
)

# Asset type models
from app.models.asset_types import (
    HotelDetails,
    HotelRoomMix,
    IndustrialDetails,
    IndustrialTenant,
    LandDetails,
    MixedUseComponent,
    MixedUseDetails,
    MultifamilyDetails,
    MultifamilyUnitMix,
    OfficeDetails,
    OfficeTenant,
    RetailDetails,
    RetailTenant,
    SelfStorageDetails,
    SelfStorageUnitMix,
    StudentHousingDetails,
)

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "InvestorProfile",
    "InvestorPreferences",
    "Deal",
    "MajorTenant",
    "Property",
    "PropertyDocument",
    "InvestmentMetrics",
    "Financing",
    "AnnualProjection",
    "MarketAnalysis",
    "SponsorFees",
    "WaterfallStructure",
    "Reserve",
    "PropertyEmbedding",
    "InvestorEmbedding",
    "Consent",
    "LeadNote",
    "StageHistory",
    "DealMatch",
    "CallSession",
    "CallTranscript",
    "InvestorUser",
    "InvestorSubscription",
    "InvestorDeal",
    "DealChunk",
    "InvestorChatSession",
    "IndustrialDetails",
    "IndustrialTenant",
    "MultifamilyDetails",
    "MultifamilyUnitMix",
    "RetailDetails",
    "RetailTenant",
    "OfficeDetails",
    "OfficeTenant",
    "SelfStorageDetails",
    "SelfStorageUnitMix",
    "StudentHousingDetails",
    "HotelDetails",
    "HotelRoomMix",
    "LandDetails",
    "MixedUseDetails",
    "MixedUseComponent",
]
