"""
Embedding models for semantic search using pgvector.

These models store vector embeddings for:
- PropertyEmbedding: Document sections from investor briefs
- InvestorEmbedding: Investor profile and preferences text
"""
import uuid
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile
    from app.models.property import Property


class PropertyEmbedding(Base, UUIDMixin, TimestampMixin):
    """
    Vector embeddings for property/deal document sections.
    One-to-many relationship with Property (multiple sections per property).

    Section types:
    - executive_summary
    - investment_thesis
    - value_add_strategy
    - market_analysis
    - risk_factors
    - tenant_info
    - financials
    - property_overview
    - investment_terms
    """

    __tablename__ = "property_embeddings"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Section identification
    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Original text content (for reference)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)

    # Relationship
    property: Mapped["Property"] = relationship(back_populates="embeddings")


class InvestorEmbedding(Base, UUIDMixin, TimestampMixin):
    """
    Vector embeddings for investor profile text.
    One-to-many relationship with InvestorProfile (multiple sections per investor).

    Section types:
    - investment_thesis
    - investment_preferences
    - risk_profile
    - full_profile (concatenated)
    """

    __tablename__ = "investor_embeddings"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Section identification
    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Original text content (for reference)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Vector embedding (1536 dimensions for text-embedding-3-small)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)

    # Relationship
    investor: Mapped["InvestorProfile"] = relationship(back_populates="embeddings")
