"""SQLAlchemy models for BlackKeyX."""

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.consent import Consent, LeadNote, StageHistory
from app.models.investor import InvestorProfile
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
    # Property
    "Property",
    "PropertyFeature",
    "PropertyDocument",
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
