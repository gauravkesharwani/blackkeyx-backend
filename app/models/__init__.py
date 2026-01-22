"""SQLAlchemy models for BlackKeyX."""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.consent import Consent, LeadNote, StageHistory
from app.models.embeddings import InvestorEmbedding, PropertyEmbedding
from app.models.financial import AnnualProjection, Financing, InvestmentMetrics, Tenant
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.market import MarketAnalysis
from app.models.matching import DealMatch
from app.models.property import Property, PropertyDocument, PropertyFeature
from app.models.voice import CallSession, CallTranscript

__all__ = [
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    # Investor
    "InvestorProfile",
    "InvestorPreferences",
    # Property
    "Property",
    "PropertyFeature",
    "PropertyDocument",
    # Financial
    "InvestmentMetrics",
    "Financing",
    "Tenant",
    "AnnualProjection",
    # Market
    "MarketAnalysis",
    # Embeddings
    "PropertyEmbedding",
    "InvestorEmbedding",
    # Consent
    "Consent",
    "LeadNote",
    "StageHistory",
    # Matching
    "DealMatch",
    # Voice
    "CallSession",
    "CallTranscript",
]
