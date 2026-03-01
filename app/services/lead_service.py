"""Lead service for lead submission operations."""

import asyncio
import logging
import re
import uuid
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository
from app.models.consent import StageHistory
from app.models.investor import InvestorProfile
from app.services.embedding_service import EmbeddingService
from app.services.livekit_dispatcher import get_livekit_dispatcher
from app.services.matching_service import run_matching_background

logger = logging.getLogger(__name__)

# --- Qualification scoring (single source of truth) ---

CAPACITY_SCORES: dict[str, int] = {
    "$100K-$250K": 10,
    "$250K-$500K": 15,
    "$500K-$1M": 20,
    "$1M+": 25,
}

FIT_SCORES: dict[str, int] = {
    "high_priority": 25,
    "medium_priority": 15,
    "open_to_exploring": 10,
    "not_a_focus": 5,
}

PROCESS_SCORES: dict[str, int] = {
    "toe_in": 10,
    "meaningful_first": 20,
    "full_commitment": 25,
}

TIMING_SCORES: dict[str, int] = {
    "actively_deploying": 25,
    "possibly_evaluating": 15,
    "just_researching": 5,
}

_OTHER_DEFAULT_SCORE = 15


def _get_score(value: Optional[str], scores: dict[str, int]) -> int:
    if not value:
        return 0
    if value.startswith("other:"):
        return _OTHER_DEFAULT_SCORE
    return scores.get(value, _OTHER_DEFAULT_SCORE)


def calculate_qualification_score(qualification: dict) -> int:
    """Compute qualification score (0-100) from raw chatbot answers."""
    return (
        _get_score(qualification.get("capacity"), CAPACITY_SCORES)
        + _get_score(qualification.get("fit"), FIT_SCORES)
        + _get_score(qualification.get("process"), PROCESS_SCORES)
        + _get_score(qualification.get("timing"), TIMING_SCORES)
    )


def determine_qualification_bucket(score: int) -> str:
    """Determine bucket: active_intro (>=70), nurture (>=40), not_qualified (<40)."""
    if score >= 70:
        return "active_intro"
    if score >= 40:
        return "nurture"
    return "not_qualified"


async def _dispatch_call_background(
    investor_id,
    phone_number: str,
    investor_context: dict,
) -> None:
    """Background task to dispatch outbound call. Creates its own DB session."""
    try:
        from app.db.session import async_session_factory

        dispatcher = get_livekit_dispatcher()

        room_name = await dispatcher.dispatch_outbound_call(
            phone_number=phone_number,
            investor_context=investor_context,
        )

        async with async_session_factory() as session:
            call_repo = CallRepository(session)
            await call_repo.create_call(
                investor_id=investor_id,
                room_name=room_name,
                status="initiated",
            )

            investor = await session.get(InvestorProfile, investor_id)
            if investor:
                investor.stage = "call_dispatched"
                session.add(StageHistory(
                    investor_id=investor_id,
                    from_stage="new_lead",
                    to_stage="call_dispatched",
                    changed_by="system",
                    notes="Auto-dispatched outbound call after lead submission",
                ))

            await session.commit()

        logger.info(f"Outbound call dispatched for lead {investor_id} in room {room_name}")
    except Exception as e:
        logger.warning(f"Failed to dispatch outbound call for lead {investor_id}: {e}")


class LeadService:
    """Service for lead submission operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.investor_repo = InvestorRepository(session)
        self.call_repo = CallRepository(session)
        self.livekit = get_livekit_dispatcher()

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """
        Normalize phone number to E.164 format for LiveKit SIP.

        Examples:
            '(415) 555-1234' -> '+14155551234'
            '415-555-1234' -> '+14155551234'
            '+14155551234' -> '+14155551234'
        """
        if phone.startswith("+"):
            digits = "+" + re.sub(r"\D", "", phone[1:])
        else:
            digits = re.sub(r"\D", "", phone)

        if digits.startswith("+"):
            return digits
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if len(digits) > 10:
            return f"+{digits}"
        return f"+1{digits}"

    @staticmethod
    def parse_capital(capital_str: Optional[str]) -> Optional[int]:
        """Parse capital string like '$250K-$500K' to integer (midpoint)."""
        if not capital_str:
            return None
        if capital_str.startswith("other:"):
            return None

        capital_map = {
            "$100K-$250K": 175000,
            "$250K-$500K": 375000,
            "$500K-$1M": 750000,
            "$1M+": 1500000,
        }
        return capital_map.get(capital_str)

    async def submit_lead(
        self,
        phone: str,
        consent: bool,
        name: Optional[str] = None,
        timeline: Optional[str] = None,
        capital_available: Optional[str] = None,
        investment_preferences: Optional[list] = None,
        qualification: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[InvestorProfile, bool]:
        """
        Submit a new lead.

        Returns (investor, is_new) tuple.
        - is_new=True if new lead was created
        - is_new=False if existing lead was found
        """
        if not consent:
            raise ValueError("Consent is required for lead submission")

        normalized_phone = self.normalize_phone(phone)

        # Check for existing lead
        existing = await self.investor_repo.get_by_phone(normalized_phone)
        if existing:
            return existing, False

        # Parse capital
        capital_int = None
        if qualification:
            capital_int = self.parse_capital(qualification.get("capacity"))
        elif capital_available:
            capital_int = self.parse_capital(capital_available)

        # Create investor profile
        investor = InvestorProfile(
            id=uuid.uuid4(),
            phone=normalized_phone,
            name=name,
            timeline=timeline,
            capital_available=capital_int,
            investment_preferences=investment_preferences or [],
            stage="new_lead",
            source="web",
        )

        # Add qualification data if present — score computed server-side
        if qualification:
            investor.investor_type = qualification.get("investorType")
            investor.capacity = qualification.get("capacity")
            investor.fit = qualification.get("fit")
            investor.process = qualification.get("process")
            investor.timing = qualification.get("timing")

            score = calculate_qualification_score(qualification)
            bucket = determine_qualification_bucket(score)

            investor.qualification_score = score
            investor.qualification_bucket = bucket
            investor.lead_score = score

        # Save investor
        investor = await self.investor_repo.create(investor)

        # Store consent record
        await self.investor_repo.add_consent(
            investor_id=investor.id,
            consent_text="TCPA consent granted via web chatbot",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Record initial stage
        stage_change = StageHistory(
            investor_id=investor.id,
            from_stage=None,
            to_stage="new_lead",
            changed_by="system",
            notes="Lead submitted via chatbot",
        )
        self.session.add(stage_change)

        # Generate investor embeddings if investment data is available
        if (
            investor.investment_thesis
            or investor.investment_preferences
            or investor.risk_tolerance
        ):
            try:
                embedding_service = EmbeddingService(self.session)
                await embedding_service.create_investor_profile_embedding(
                    investor_id=investor.id,
                    investor=investor,
                    preferences=None,  # No preferences yet at lead submission
                )
                # Trigger matching in background after embeddings are created
                asyncio.create_task(run_matching_background(investor_id=investor.id))
            except Exception as e:
                logger.warning(f"Failed to create investor embeddings: {e}")
                # Don't fail the lead submission if embeddings fail

        # Auto-dispatch outbound call in background (don't block the API response)
        investor_context = {
            "investor_id": str(investor.id),
            "name": investor.name or "there",
            "capital_available": investor.capacity or investor.capital_available,
            "timeline": investor.timeline,
            "investment_preferences": investor.investment_preferences or [],
        }
        asyncio.create_task(
            _dispatch_call_background(
                investor_id=investor.id,
                phone_number=normalized_phone,
                investor_context=investor_context,
            )
        )

        return investor, True
