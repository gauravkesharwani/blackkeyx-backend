"""Pydantic schemas for the Investor Portal."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class GoogleAuthRequest(BaseModel):
    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class InvestorAuthResponse(BaseModel):
    success: bool
    access_token: str
    refresh_token: str
    investor_user_id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class InvestorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime
    plan: str = "free"
    deals_used: int = 0
    deals_limit: Optional[int] = 3  # None = unlimited (pro)


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: str
    status: str
    current_period_end: Optional[datetime]
    cancel_at_period_end: bool
    deals_used: int
    deals_limit: Optional[int]  # None = unlimited


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingPortalResponse(BaseModel):
    portal_url: str


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

class InvestorDealResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    original_filename: Optional[str]
    file_type: Optional[str]
    file_size_bytes: Optional[int]
    status: str
    processing_error: Optional[str]
    created_at: datetime
    updated_at: datetime


class InvestorDealListResponse(BaseModel):
    deals: List[InvestorDealResponse]
    total: int


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[uuid.UUID] = None


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    timestamp: str


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deal_id: uuid.UUID
    messages: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
