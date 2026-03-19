"""
Investor Portal Service.

Handles:
- Google OAuth login / registration
- Deal CRUD + S3 upload
- Background document processing (extract → chunk → embed)
- RAG chatbot (vector search → GPT-4o streaming)
- Stripe subscription management
"""

import asyncio
import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from fastapi import HTTPException, UploadFile
from openai import AsyncOpenAI
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import async_session_factory
from app.middleware.investor_auth import (
    GoogleTokenInfo,
    create_access_token,
    create_refresh_token,
    verify_google_id_token,
)
from app.models.investor_portal import (
    DealChunk,
    InvestorChatSession,
    InvestorDeal,
    InvestorSubscription,
    InvestorUser,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Allowed file types and max size (30 MB)
ALLOWED_TYPES = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 30 * 1024 * 1024  # 30 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_s3_key(investor_user_id: uuid.UUID, filename: str) -> str:
    """Build S3 key with enforced prefix. Strips directory components."""
    safe_name = Path(filename).name
    file_uuid = uuid.uuid4().hex[:8]
    return f"investor/{investor_user_id}/{file_uuid}_{safe_name}"


def _detect_file_type(content_type: str, filename: str) -> str:
    """Return 'pdf' or 'docx'. Raises HTTPException for unsupported types."""
    ext = Path(filename).suffix.lower()
    if ext == ".pdf" or content_type == "application/pdf":
        return "pdf"
    if ext == ".docx" or "wordprocessingml" in content_type:
        return "docx"
    raise HTTPException(
        status_code=415,
        detail="Unsupported file type. Only PDF and DOCX are allowed.",
    )


def _extract_text_sync(content: bytes, file_type: str) -> str:
    """Extract plain text from PDF or DOCX bytes (runs in thread pool)."""
    if file_type == "pdf":
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)
    elif file_type == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    raise ValueError(f"Unsupported file_type: {file_type}")


async def _extract_title_and_description(text_content: str, filename: str) -> tuple[str, str]:
    """
    Use GPT-4o-mini to extract a concise title and one-sentence description
    from the first ~1500 words of the document.
    Falls back to the filename (without extension) if extraction fails.
    """
    preview = " ".join(text_content.split()[:1500])
    fallback_title = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract deal metadata from real estate investment documents. "
                        "Return ONLY a JSON object with two fields: "
                        "'title' (short deal name, max 80 chars) and "
                        "'description' (one sentence summary, max 200 chars). "
                        "Example: {\"title\": \"Lakewood 240-Unit Multifamily\", "
                        "\"description\": \"Value-add multifamily acquisition in Lakewood, CO targeting 18% IRR over 5 years.\"}"
                    ),
                },
                {"role": "user", "content": f"Document excerpt:\n\n{preview}"},
            ],
            max_tokens=150,
            temperature=0,
            response_format={"type": "json_object"},
        )
        import json
        result = json.loads(response.choices[0].message.content or "{}")
        title = str(result.get("title", fallback_title)).strip()[:255] or fallback_title
        description = str(result.get("description", "")).strip()[:500]
        return title, description
    except Exception as e:
        logger.warning("Title extraction failed, using filename fallback: %s", e)
        return fallback_title, ""


def _chunk_text(text_content: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping word-count chunks.
    500 words ≈ 650 tokens — safe for text-embedding-3-small (8192 limit).
    """
    words = text_content.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 50:  # skip near-empty chunks
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Main Service
# ---------------------------------------------------------------------------

class InvestorPortalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._s3 = None

    @property
    def s3(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        return self._s3

    # -----------------------------------------------------------------------
    # Auth
    # -----------------------------------------------------------------------

    async def google_login(self, id_token: str) -> dict:
        """
        Verify Google ID token, upsert InvestorUser, create subscription if new,
        return access + refresh JWTs.
        """
        token_info: GoogleTokenInfo = verify_google_id_token(id_token)

        # Upsert investor user
        result = await self.session.execute(
            select(InvestorUser).where(InvestorUser.google_sub == token_info.sub)
        )
        investor = result.scalar_one_or_none()

        if investor is None:
            # New user — create investor + free subscription
            investor = InvestorUser(
                google_sub=token_info.sub,
                email=token_info.email,
                full_name=token_info.name,
                avatar_url=token_info.picture,
            )
            self.session.add(investor)
            await self.session.flush()

            subscription = InvestorSubscription(
                investor_user_id=investor.id,
                plan="free",
                status="active",
            )
            self.session.add(subscription)
            await self.session.flush()
        else:
            # Returning user — update profile info
            investor.full_name = token_info.name or investor.full_name
            investor.avatar_url = token_info.picture or investor.avatar_url
            await self.session.flush()

        access_token = create_access_token(investor.id, investor.email)
        refresh_token = create_refresh_token(investor.id, investor.email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "investor_user_id": str(investor.id),
            "email": investor.email,
            "full_name": investor.full_name,
            "avatar_url": investor.avatar_url,
        }

    async def get_investor(self, investor_user_id: uuid.UUID) -> InvestorUser:
        """Fetch investor by ID. Raises 404 if not found."""
        result = await self.session.execute(
            select(InvestorUser).where(InvestorUser.id == investor_user_id)
        )
        investor = result.scalar_one_or_none()
        if not investor:
            raise HTTPException(status_code=404, detail="Investor not found")
        return investor

    async def refresh_access_token(self, refresh_token_str: str) -> dict:
        """Issue a new access token from a valid refresh token."""
        from app.middleware.investor_auth import decode_token
        payload = decode_token(refresh_token_str)
        if payload.type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        investor_id = uuid.UUID(payload.sub)
        new_access = create_access_token(investor_id, payload.email)
        return {"access_token": new_access}

    # -----------------------------------------------------------------------
    # Subscription / Plan
    # -----------------------------------------------------------------------

    async def get_subscription(self, investor_user_id: uuid.UUID) -> InvestorSubscription:
        result = await self.session.execute(
            select(InvestorSubscription).where(
                InvestorSubscription.investor_user_id == investor_user_id
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return sub

    async def get_deal_count(self, investor_user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(InvestorDeal).where(
                InvestorDeal.investor_user_id == investor_user_id
            )
        )
        return result.scalar_one()

    async def check_upload_limit(self, investor_user_id: uuid.UUID) -> None:
        """Raise HTTP 402 if investor is on free plan and has hit the deal limit."""
        sub = await self.get_subscription(investor_user_id)
        if sub.plan == "free":
            count = await self.get_deal_count(investor_user_id)
            if count >= settings.free_plan_deal_limit:
                raise HTTPException(
                    status_code=402,
                    detail={
                        "code": "upload_limit_reached",
                        "message": f"Free plan allows {settings.free_plan_deal_limit} deals. Upgrade to Pro for unlimited.",
                        "upgrade_url": "/investor/billing",
                    },
                )

    async def create_stripe_checkout_session(self, investor_user_id: uuid.UUID) -> str:
        """Create a Stripe Checkout session and return the URL."""
        import stripe
        stripe.api_key = settings.stripe_secret_key

        sub = await self.get_subscription(investor_user_id)
        investor = await self.get_investor(investor_user_id)

        # Create Stripe customer if not exists
        if not sub.stripe_customer_id:
            customer = stripe.Customer.create(email=investor.email, name=investor.full_name)
            sub.stripe_customer_id = customer.id
            await self.session.flush()

        checkout = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": settings.stripe_pro_price_id, "quantity": 1}],
            success_url=f"{settings.cors_origins[0]}/investor/dashboard?upgraded=true",
            cancel_url=f"{settings.cors_origins[0]}/investor/billing",
        )
        return checkout.url

    async def create_billing_portal_session(self, investor_user_id: uuid.UUID) -> str:
        """Create a Stripe Customer Portal session and return the URL."""
        import stripe
        stripe.api_key = settings.stripe_secret_key

        sub = await self.get_subscription(investor_user_id)
        if not sub.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No Stripe customer found")

        portal = stripe.billing_portal.Session.create(
            customer=sub.stripe_customer_id,
            return_url=f"{settings.cors_origins[0]}/investor/billing",
        )
        return portal.url

    async def handle_stripe_webhook(self, payload: bytes, sig_header: str) -> None:
        """Process Stripe webhook events to keep subscription in sync."""
        import stripe
        stripe.api_key = settings.stripe_secret_key

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            stripe_customer_id = data.get("customer")
            stripe_subscription_id = data.get("subscription")
            await self._activate_pro(stripe_customer_id, stripe_subscription_id)

        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            await self._sync_subscription(data)

        elif event_type == "customer.subscription.deleted":
            await self._cancel_subscription(data.get("customer"))

        elif event_type == "invoice.payment_failed":
            await self._mark_past_due(data.get("customer"))

    async def _activate_pro(self, stripe_customer_id: str, stripe_subscription_id: str) -> None:
        result = await self.session.execute(
            select(InvestorSubscription).where(
                InvestorSubscription.stripe_customer_id == stripe_customer_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan = "pro"
            sub.stripe_subscription_id = stripe_subscription_id
            sub.status = "active"
            await self.session.flush()

    async def _sync_subscription(self, stripe_sub: dict) -> None:
        result = await self.session.execute(
            select(InvestorSubscription).where(
                InvestorSubscription.stripe_customer_id == stripe_sub.get("customer")
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = stripe_sub.get("status", sub.status)
            sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
            period_end = stripe_sub.get("current_period_end")
            if period_end:
                sub.current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)
            await self.session.flush()

    async def _cancel_subscription(self, stripe_customer_id: str) -> None:
        result = await self.session.execute(
            select(InvestorSubscription).where(
                InvestorSubscription.stripe_customer_id == stripe_customer_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.plan = "free"
            sub.status = "canceled"
            sub.stripe_subscription_id = None
            await self.session.flush()

    async def _mark_past_due(self, stripe_customer_id: str) -> None:
        result = await self.session.execute(
            select(InvestorSubscription).where(
                InvestorSubscription.stripe_customer_id == stripe_customer_id
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "past_due"
            await self.session.flush()

    # -----------------------------------------------------------------------
    # Deals
    # -----------------------------------------------------------------------

    async def list_deals(self, investor_user_id: uuid.UUID) -> List[InvestorDeal]:
        result = await self.session.execute(
            select(InvestorDeal)
            .where(InvestorDeal.investor_user_id == investor_user_id)
            .order_by(InvestorDeal.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_deal(self, deal_id: uuid.UUID, investor_user_id: uuid.UUID) -> InvestorDeal:
        """Fetch deal with ownership check."""
        result = await self.session.execute(
            select(InvestorDeal).where(
                InvestorDeal.id == deal_id,
                InvestorDeal.investor_user_id == investor_user_id,
            )
        )
        deal = result.scalar_one_or_none()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        return deal

    async def create_deal(
        self,
        investor_user_id: uuid.UUID,
        file: UploadFile,
        background_tasks,
    ) -> InvestorDeal:
        """
        Upload file to S3, auto-extract title & description via GPT,
        create deal record, and enqueue background processing.
        """
        await self.check_upload_limit(investor_user_id)

        # Validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum size is 30 MB.")

        file_type = _detect_file_type(file.content_type or "", file.filename or "")
        s3_key = _build_s3_key(investor_user_id, file.filename or "document")

        # Extract text preview for title/description (first page only, fast)
        loop = asyncio.get_running_loop()
        try:
            text_preview = await loop.run_in_executor(None, _extract_text_sync, content, file_type)
        except Exception:
            text_preview = ""

        # Auto-extract title and description using GPT-4o-mini
        title, description = await _extract_title_and_description(
            text_preview, file.filename or "document"
        )

        # Upload to S3
        self.s3.put_object(
            Bucket=settings.aws_s3_bucket,
            Key=s3_key,
            Body=content,
            ContentType=file.content_type or "application/octet-stream",
        )

        # Create deal record
        deal = InvestorDeal(
            investor_user_id=investor_user_id,
            title=title,
            description=description,
            s3_key=s3_key,
            original_filename=file.filename,
            file_type=file_type,
            file_size_bytes=len(content),
            status="pending",
        )
        self.session.add(deal)
        await self.session.commit()
        await self.session.refresh(deal)
        deal_id = deal.id

        # Enqueue background processing (new session — request session will close)
        background_tasks.add_task(process_deal_document, deal_id, content, file_type)

        return deal

    async def delete_deal(self, deal_id: uuid.UUID, investor_user_id: uuid.UUID) -> None:
        """Delete deal, its S3 file, and all chunks."""
        deal = await self.get_deal(deal_id, investor_user_id)

        # Delete from S3
        if deal.s3_key:
            try:
                self.s3.delete_object(Bucket=settings.aws_s3_bucket, Key=deal.s3_key)
            except Exception as e:
                logger.warning("Failed to delete S3 object %s: %s", deal.s3_key, e)

        await self.session.delete(deal)
        await self.session.flush()

    # -----------------------------------------------------------------------
    # Chat (RAG)
    # -----------------------------------------------------------------------

    async def get_or_create_chat_session(
        self,
        deal_id: uuid.UUID,
        investor_user_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
    ) -> InvestorChatSession:
        if session_id:
            result = await self.session.execute(
                select(InvestorChatSession).where(
                    InvestorChatSession.id == session_id,
                    InvestorChatSession.deal_id == deal_id,
                    InvestorChatSession.investor_user_id == investor_user_id,
                )
            )
            chat = result.scalar_one_or_none()
            if chat:
                return chat

        # Create new session
        chat = InvestorChatSession(
            investor_user_id=investor_user_id,
            deal_id=deal_id,
            messages=[],
        )
        self.session.add(chat)
        await self.session.flush()
        return chat

    async def get_chat_history(
        self, deal_id: uuid.UUID, investor_user_id: uuid.UUID
    ) -> Optional[InvestorChatSession]:
        """Get the most recent chat session for a deal."""
        result = await self.session.execute(
            select(InvestorChatSession)
            .where(
                InvestorChatSession.deal_id == deal_id,
                InvestorChatSession.investor_user_id == investor_user_id,
            )
            .order_by(InvestorChatSession.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def rag_chat_stream(
        self,
        deal_id: uuid.UUID,
        investor_user_id: uuid.UUID,
        question: str,
        session_id: Optional[uuid.UUID],
    ) -> AsyncGenerator[str, None]:
        """
        RAG chatbot — streams GPT-4o response as SSE tokens.
        Saves exchange to ChatSession after completion.
        """
        # Verify ownership and readiness
        deal = await self.get_deal(deal_id, investor_user_id)
        if deal.status != "ready":
            raise HTTPException(
                status_code=400,
                detail=f"Deal is not ready for chat (status: {deal.status})",
            )

        # Get or create chat session
        chat_session = await self.get_or_create_chat_session(
            deal_id, investor_user_id, session_id
        )

        client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Embed the question
        q_emb_response = await client.embeddings.create(
            input=question,
            model="text-embedding-3-small",
        )
        q_embedding = q_emb_response.data[0].embedding
        q_embedding_str = "[" + ",".join(str(x) for x in q_embedding) + "]"

        # Vector similarity search scoped to this deal
        rows = await self.session.execute(
            text("""
                SELECT chunk_text,
                       1 - (embedding <=> CAST(:q_emb AS vector)) AS similarity
                FROM deal_chunks
                WHERE deal_id = :deal_id
                ORDER BY similarity DESC
                LIMIT 8
            """),
            {"q_emb": q_embedding_str, "deal_id": str(deal_id)},
        )
        context_chunks = [row.chunk_text for row in rows.fetchall()]

        if not context_chunks:
            yield "data: I couldn't find relevant information in this document.\n\n"
            yield "data: [DONE]\n\n"
            return

        context = "\n\n---\n\n".join(context_chunks)

        system_prompt = (
            "You are an expert investment analyst helping an investor understand a deal document. "
            "Answer questions based ONLY on the provided document context below. "
            "Be precise, professional, and cite specific numbers or facts from the document. "
            "If the context doesn't contain enough information to answer, say so clearly."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document context:\n{context}\n\nQuestion: {question}"},
        ]

        # Include recent chat history for context (last 6 messages)
        if chat_session.messages:
            history = chat_session.messages[-6:]
            messages = (
                [messages[0]]
                + [{"role": m["role"], "content": m["content"]} for m in history]
                + [messages[1]]
            )

        # Stream GPT-4o response
        full_response = ""
        stream = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
            max_tokens=1024,
            temperature=0.2,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_response += delta
                yield f"data: {delta}\n\n"

        yield "data: [DONE]\n\n"

        # Persist messages to chat session
        now = datetime.now(timezone.utc).isoformat()
        chat_session.messages = list(chat_session.messages) + [
            {"role": "user", "content": question, "timestamp": now},
            {"role": "assistant", "content": full_response, "timestamp": now},
        ]
        await self.session.flush()


# ---------------------------------------------------------------------------
# Background Task — Document Processing
# ---------------------------------------------------------------------------

async def process_deal_document(
    deal_id: uuid.UUID,
    content: bytes,
    file_type: str,
) -> None:
    """
    Background task: extract text → chunk → embed → store.
    Opens its own DB session (request session is closed by this point).
    """
    async with async_session_factory() as session:
        try:
            # Mark as processing
            deal = await session.get(InvestorDeal, deal_id)
            if not deal:
                logger.error("Deal %s not found for processing", deal_id)
                return

            deal.status = "processing"
            await session.flush()

            # Extract text in thread pool (blocking I/O)
            loop = asyncio.get_running_loop()
            text_content = await loop.run_in_executor(
                None, _extract_text_sync, content, file_type
            )

            if not text_content.strip():
                deal.status = "error"
                deal.processing_error = "Could not extract text from document"
                await session.commit()
                return

            # Chunk the text
            chunks = _chunk_text(text_content)
            if not chunks:
                deal.status = "error"
                deal.processing_error = "Document appears to be empty"
                await session.commit()
                return

            # Embed chunks in batches of 20
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            BATCH_SIZE = 20

            for batch_start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[batch_start: batch_start + BATCH_SIZE]
                response = await client.embeddings.create(
                    input=batch,
                    model="text-embedding-3-small",
                )
                for i, emb_data in enumerate(response.data):
                    chunk_obj = DealChunk(
                        deal_id=deal_id,
                        chunk_index=batch_start + i,
                        chunk_text=batch[i],
                        token_count=len(batch[i].split()),
                        embedding=emb_data.embedding,
                    )
                    session.add(chunk_obj)

            deal.status = "ready"
            await session.commit()
            logger.info("Deal %s processed successfully (%d chunks)", deal_id, len(chunks))

        except Exception as e:
            logger.exception("Error processing deal %s: %s", deal_id, e)
            try:
                async with async_session_factory() as err_session:
                    deal = await err_session.get(InvestorDeal, deal_id)
                    if deal:
                        deal.status = "error"
                        deal.processing_error = str(e)[:500]
                        await err_session.commit()
            except Exception:
                logger.exception("Failed to update deal error status for %s", deal_id)
