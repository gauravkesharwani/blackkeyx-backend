"""Embedding models for semantic search using pgvector."""
import uuid
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.investor import InvestorProfile
    from app.models.property import Deal


class PropertyEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embeddings for deal document sections. 1:N with Deal."""

    __tablename__ = "property_embeddings"

    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)

    property: Mapped["Deal"] = relationship(back_populates="embeddings")


class InvestorEmbedding(Base, UUIDMixin, TimestampMixin):
    """Vector embeddings for investor profile text. 1:N with InvestorProfile."""

    __tablename__ = "investor_embeddings"

    investor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)

    investor: Mapped["InvestorProfile"] = relationship(back_populates="embeddings")
