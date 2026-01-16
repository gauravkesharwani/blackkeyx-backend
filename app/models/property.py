"""
Property models - maps to DealMemo from frontend types/deal.ts

Frontend type:
interface DealMemo {
  id: string
  name: string
  dealType: string
  summary: string
  thesis: string
  minimumInvestment: number
  targetReturn: string
  riskFactors: string[]
  idealInvestorProfile: string
  structure: string
  timeline: string
  status: 'active' | 'closed' | 'paused'
  createdAt: string
  updatedAt: string
}
"""
import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.matching import DealMatch


class Property(Base, UUIDMixin, TimestampMixin):
    """
    Deal memo / property listing.
    Maps to DealMemo from frontend.
    """

    __tablename__ = "properties"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Investment terms
    minimum_investment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_return: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_factors: Mapped[List[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    ideal_investor_profile: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structure: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timeline: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status: 'active' | 'closed' | 'paused'
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    # Location (optional, for extended use)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Additional financial metrics
    purchase_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    square_feet: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_equity_required: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # S3 document reference
    document_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    document_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    features: Mapped[Optional["PropertyFeature"]] = relationship(
        back_populates="property",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    matches: Mapped[List["DealMatch"]] = relationship(
        back_populates="matched_property",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PropertyFeature(Base, UUIDMixin, TimestampMixin):
    """
    Flexible JSONB-based features for multi-asset class support.
    Stores asset-specific attributes without schema migrations.
    """

    __tablename__ = "property_features"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Asset type determines which schema to validate against
    # e.g., 'industrial', 'multifamily', 'office', 'retail'
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # All features stored as JSONB (asset-specific)
    # Example for industrial: {"clear_height_min": 32, "loading_docks": 24}
    # Example for multifamily: {"unit_count": 250, "amenities": ["pool", "gym"]}
    features: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Common fields (applicable to most asset types)
    year_built: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    year_renovated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="features")


class PropertyDocument(Base, UUIDMixin, TimestampMixin):
    """
    Uploaded document reference for a property.
    """

    __tablename__ = "property_documents"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
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
