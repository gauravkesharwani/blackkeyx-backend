"""
Investor Portal models.

Self-service investor accounts separate from the CRM InvestorProfile system.
Investors register via Google OAuth, upload deal documents, and chat with
an AI assistant about those documents using RAG.
"""

import uuid
from datetime import datetime
from typing import Any, List, Optional, TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class InvestorUser(Base, UUIDMixin, TimestampMixin):
    """
    Self-registered investor user for the portal.
    Authenticated via Google OAuth — no password stored.
    Entirely separate from InvestorProfile (CRM lead record).
    """

    __tablename__ = "investor_users"

    google_sub: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    deals: Mapped[List["InvestorDeal"]] = relationship(
        back_populates="investor_user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    subscription: Mapped[Optional["InvestorSubscription"]] = relationship(
        back_populates="investor_user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chat_sessions: Mapped[List["InvestorChatSession"]] = relationship(
        back_populates="investor_user",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class InvestorSubscription(Base, UUIDMixin, TimestampMixin):
    """
    Stripe subscription record for an InvestorUser.
    One-to-one with InvestorUser.
    Created with plan='free' on every new registration.
    """

    __tablename__ = "investor_subscriptions"

    investor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    plan: Mapped[str] = mapped_column(String(20), default="free", nullable=False)  # free | pro
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # active | past_due | canceled | trialing
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    investor_user: Mapped["InvestorUser"] = relationship(back_populates="subscription")


class InvestorDeal(Base, UUIDMixin, TimestampMixin):
    """
    A deal document uploaded by an InvestorUser.
    Strict data isolation: always scoped to investor_user_id.
    """

    __tablename__ = "investor_deals"

    investor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # S3 reference — key format: investor/{investor_user_id}/{uuid8}_{filename}
    s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # pdf | docx
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Pipeline status: pending | processing | ready | error
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    processing_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    investor_user: Mapped["InvestorUser"] = relationship(back_populates="deals")
    chunks: Mapped[List["DealChunk"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        lazy="noload",  # Never eager-load — can be hundreds of rows
    )
    chat_sessions: Mapped[List["InvestorChatSession"]] = relationship(
        back_populates="deal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DealChunk(Base, UUIDMixin):
    """
    A text chunk from an InvestorDeal document with its pgvector embedding.
    Write-once — never updated after creation.
    """

    __tablename__ = "deal_chunks"

    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    deal: Mapped["InvestorDeal"] = relationship(back_populates="chunks")


class InvestorChatSession(Base, UUIDMixin, TimestampMixin):
    """
    Chat session between an investor and the RAG chatbot for a specific deal.
    Messages stored as JSONB: [{role, content, timestamp}].
    """

    __tablename__ = "investor_chat_sessions"

    investor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    messages: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    investor_user: Mapped["InvestorUser"] = relationship(back_populates="chat_sessions")
    deal: Mapped["InvestorDeal"] = relationship(back_populates="chat_sessions")
