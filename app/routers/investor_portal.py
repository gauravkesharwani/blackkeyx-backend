"""
Investor Portal router.

Endpoints:
  POST   /api/v1/investor/auth/google       - Google OAuth login
  POST   /api/v1/investor/auth/refresh      - Refresh access token
  POST   /api/v1/investor/auth/logout       - Logout (clear cookies signal)
  GET    /api/v1/investor/me                - Get current investor profile
  GET    /api/v1/investor/subscription      - Get subscription + usage
  POST   /api/v1/investor/billing/checkout  - Stripe Checkout session
  POST   /api/v1/investor/billing/portal    - Stripe Customer Portal
  POST   /api/v1/investor/billing/webhook   - Stripe webhook (public)
  POST   /api/v1/investor/deals             - Upload deal document
  GET    /api/v1/investor/deals             - List own deals
  GET    /api/v1/investor/deals/{id}        - Get deal detail
  DELETE /api/v1/investor/deals/{id}        - Delete deal
  POST   /api/v1/investor/deals/{id}/chat   - RAG chat (SSE stream)
  GET    /api/v1/investor/deals/{id}/chat/history - Chat history
"""

import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Header,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.middleware.investor_auth import decode_token, require_investor
from app.middleware.rate_limit import limiter
from app.schemas.investor_portal import (
    BillingPortalResponse,
    ChatSessionResponse,
    CheckoutSessionResponse,
    GoogleAuthRequest,
    InvestorAuthResponse,
    InvestorDealListResponse,
    InvestorDealResponse,
    InvestorProfileResponse,
    SubscriptionResponse,
)
from app.services.investor_portal_service import InvestorPortalService

router = APIRouter()
settings = get_settings()


def get_service(session: AsyncSession = Depends(get_db)) -> InvestorPortalService:
    return InvestorPortalService(session)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.post("/auth/google", response_model=InvestorAuthResponse)
@limiter.limit("10/minute")
async def google_login(
    request: Request,
    body: GoogleAuthRequest,
    service: InvestorPortalService = Depends(get_service),
):
    """Verify Google ID token, register/login investor, return JWTs."""
    result = await service.google_login(body.id_token)
    return InvestorAuthResponse(success=True, **result)


@router.post("/auth/refresh")
async def refresh_token(
    investor_refresh_token: Optional[str] = Header(None, alias="X-Refresh-Token"),
    service: InvestorPortalService = Depends(get_service),
):
    """Issue new access token using refresh token."""
    if not investor_refresh_token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Refresh token required")
    result = await service.refresh_access_token(investor_refresh_token)
    return result


@router.post("/auth/logout")
async def logout():
    """Signal logout — Next.js BFF clears the cookies."""
    return {"success": True}


@router.get("/me", response_model=InvestorProfileResponse)
async def get_me(
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Get current investor profile with plan info."""
    investor = await service.get_investor(investor_user_id)
    sub = await service.get_subscription(investor_user_id)
    deals_used = await service.get_deal_count(investor_user_id)
    deals_limit = settings.free_plan_deal_limit if sub.plan == "free" else None

    return InvestorProfileResponse(
        id=investor.id,
        email=investor.email,
        full_name=investor.full_name,
        avatar_url=investor.avatar_url,
        is_active=investor.is_active,
        created_at=investor.created_at,
        plan=sub.plan,
        deals_used=deals_used,
        deals_limit=deals_limit,
    )


# ---------------------------------------------------------------------------
# Subscription & Billing
# ---------------------------------------------------------------------------

@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    sub = await service.get_subscription(investor_user_id)
    deals_used = await service.get_deal_count(investor_user_id)
    deals_limit = settings.free_plan_deal_limit if sub.plan == "free" else None

    return SubscriptionResponse(
        plan=sub.plan,
        status=sub.status,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
        deals_used=deals_used,
        deals_limit=deals_limit,
    )


@router.post("/billing/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Create Stripe Checkout session for Pro plan upgrade."""
    url = await service.create_stripe_checkout_session(investor_user_id)
    return CheckoutSessionResponse(checkout_url=url)


@router.post("/billing/portal", response_model=BillingPortalResponse)
async def create_billing_portal(
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Create Stripe Customer Portal session for managing billing."""
    url = await service.create_billing_portal_session(investor_user_id)
    return BillingPortalResponse(portal_url=url)


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    service: InvestorPortalService = Depends(get_service),
):
    """Stripe webhook endpoint — public, verified by Stripe signature."""
    payload = await request.body()
    if not stripe_signature:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    await service.handle_stripe_webhook(payload, stripe_signature)
    return {"received": True}


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

@router.post("/deals", response_model=InvestorDealResponse, status_code=201)
async def upload_deal(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """
    Upload a deal document (PDF or DOCX).
    Title and description are auto-extracted from the document content.
    """
    deal = await service.create_deal(
        investor_user_id=investor_user_id,
        file=file,
        background_tasks=background_tasks,
    )
    return InvestorDealResponse.model_validate(deal)


@router.get("/deals", response_model=InvestorDealListResponse)
async def list_deals(
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """List all deals uploaded by the current investor."""
    deals = await service.list_deals(investor_user_id)
    return InvestorDealListResponse(
        deals=[InvestorDealResponse.model_validate(d) for d in deals],
        total=len(deals),
    )


@router.get("/deals/{deal_id}", response_model=InvestorDealResponse)
async def get_deal(
    deal_id: uuid.UUID,
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Get a specific deal (ownership enforced)."""
    deal = await service.get_deal(deal_id, investor_user_id)
    return InvestorDealResponse.model_validate(deal)


@router.delete("/deals/{deal_id}", status_code=204)
async def delete_deal(
    deal_id: uuid.UUID,
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Delete a deal and all associated data."""
    await service.delete_deal(deal_id, investor_user_id)


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/deals/{deal_id}/chat")
async def chat_with_deal(
    deal_id: uuid.UUID,
    request: Request,
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """RAG chat — streams response as Server-Sent Events."""
    body = await request.json()
    question = body.get("question", "")
    session_id_raw = body.get("session_id")
    session_id = uuid.UUID(session_id_raw) if session_id_raw else None

    async def event_stream():
        try:
            async for token in service.rag_chat_stream(
                deal_id=deal_id,
                investor_user_id=investor_user_id,
                question=question,
                session_id=session_id,
            ):
                yield token
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/deals/{deal_id}/chat/history", response_model=Optional[ChatSessionResponse])
async def get_chat_history(
    deal_id: uuid.UUID,
    investor_user_id: uuid.UUID = Depends(require_investor),
    service: InvestorPortalService = Depends(get_service),
):
    """Get the most recent chat session for a deal."""
    session = await service.get_chat_history(deal_id, investor_user_id)
    if not session:
        return None
    return ChatSessionResponse.model_validate(session)
