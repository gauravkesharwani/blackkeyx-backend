"""
Deal models - maps to DealMemo from frontend types/deal.ts

Renamed from Property to Deal to align with the new database schema.
The Property alias is kept for backward compatibility.
"""
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.asset_types.hotel import HotelDetails, HotelRoomMix
    from app.models.asset_types.industrial import IndustrialDetails, IndustrialTenant
    from app.models.asset_types.land import LandDetails
    from app.models.asset_types.mixed_use import MixedUseComponent, MixedUseDetails
    from app.models.asset_types.multifamily import MultifamilyDetails, MultifamilyUnitMix
    from app.models.asset_types.office import OfficeDetails, OfficeTenant
    from app.models.asset_types.retail import RetailDetails, RetailTenant
    from app.models.asset_types.self_storage import SelfStorageDetails, SelfStorageUnitMix
    from app.models.asset_types.student_housing import StudentHousingDetails
    from app.models.deal_structure import Reserve, SponsorFees, WaterfallStructure
    from app.models.embeddings import PropertyEmbedding
    from app.models.financial import AnnualProjection, Financing, InvestmentMetrics
    from app.models.market import MarketAnalysis
    from app.models.matching import DealMatch


class MajorTenant(Base, UUIDMixin, TimestampMixin):
    """
    Generic major tenant extracted from deal documents.

    Used as a fallback when asset-type-specific tenant tables are empty,
    particularly for mixed-use deals where the extraction captures tenant
    data generically rather than per-component.
    """

    __tablename__ = "major_tenants"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    annual_rent: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    lease_expiration: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tenant_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    deal: Mapped["Deal"] = relationship(back_populates="major_tenants")


class Deal(Base, UUIDMixin, TimestampMixin):
    """
    Deal memo / property listing.
    Maps to DealMemo from frontend.
    """

    __tablename__ = "deals"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investment terms
    minimum_investment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_return: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    risk_factors: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    ideal_investor_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structure: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timeline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Status: 'active' | 'closed' | 'paused'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Location
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Physical attributes (from former PropertyFeature)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Financial metrics
    purchase_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    replacement_cost_per_sf: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    discount_to_replacement_pct: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    total_equity_required: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_capitalization: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    # S3 document reference
    document_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    document_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Strategy and thesis
    value_add_strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Sponsor information
    sponsor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sponsor_track_record: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extraction metadata
    extraction_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    extraction_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # === COMMON RELATIONSHIPS ===

    matches: Mapped[List["DealMatch"]] = relationship(
        back_populates="matched_property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    investment_metrics: Mapped[Optional["InvestmentMetrics"]] = relationship(
        back_populates="property",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    financing: Mapped[Optional["Financing"]] = relationship(
        back_populates="property",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    annual_projections: Mapped[List["AnnualProjection"]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="AnnualProjection.year",
    )
    market_analysis: Mapped[Optional["MarketAnalysis"]] = relationship(
        back_populates="property",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Deal structure relationships
    sponsor_fees: Mapped[Optional["SponsorFees"]] = relationship(
        back_populates="deal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    waterfall_structure: Mapped[Optional["WaterfallStructure"]] = relationship(
        back_populates="deal",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reserves: Mapped[List["Reserve"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Generic major tenants (fallback for asset types without specific tenant tables)
    major_tenants: Mapped[List["MajorTenant"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Embeddings for semantic search
    embeddings: Mapped[List["PropertyEmbedding"]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    # === ASSET-TYPE SPECIFIC RELATIONSHIPS ===

    industrial_details: Mapped[Optional["IndustrialDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    industrial_tenants: Mapped[List["IndustrialTenant"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    multifamily_details: Mapped[Optional["MultifamilyDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    multifamily_unit_mix: Mapped[List["MultifamilyUnitMix"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    retail_details: Mapped[Optional["RetailDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    retail_tenants: Mapped[List["RetailTenant"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    office_details: Mapped[Optional["OfficeDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    office_tenants: Mapped[List["OfficeTenant"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    self_storage_details: Mapped[Optional["SelfStorageDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    self_storage_unit_mix: Mapped[List["SelfStorageUnitMix"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    student_housing_details: Mapped[Optional["StudentHousingDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    hotel_details: Mapped[Optional["HotelDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    hotel_room_mix: Mapped[List["HotelRoomMix"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )
    land_details: Mapped[Optional["LandDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    mixed_use_details: Mapped[Optional["MixedUseDetails"]] = relationship(
        back_populates="deal", uselist=False, cascade="all, delete-orphan", lazy="noload"
    )
    mixed_use_components: Mapped[List["MixedUseComponent"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", lazy="noload"
    )


# Backward compatibility alias
Property = Deal


class PropertyDocument(Base, UUIDMixin, TimestampMixin):
    """Uploaded document reference for a deal."""

    __tablename__ = "property_documents"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
    )

    # S3 storage info
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Extraction status
    extraction_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
