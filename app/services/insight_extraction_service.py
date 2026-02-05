"""Service for extracting investor insights from call transcripts.

Uses OpenAI Responses API with structured outputs to extract
investor profile and preferences data from call transcripts.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repositories.investor_repo import InvestorRepository
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.voice import CallSession
from app.schemas.transcript_extraction import TranscriptInsightExtraction
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
settings = get_settings()

EXTRACTION_PROMPT = """You are an expert at analyzing sales call transcripts for a commercial real estate investment platform called Black Key Exchange.

Your task is to extract structured investor profile information from a call transcript between an AI investment advisor (Sarah) and a potential investor.

The call is designed to qualify investors and understand their:
1. Preferred geographic markets (cities/regions they want to invest in)
2. Property types of interest (industrial, multifamily, office, retail, self-storage)
3. Investment strategy preference (core/stabilized, value-add, opportunistic)
4. Risk tolerance (conservative, moderate, aggressive)
5. Target hold period (short-term, 3-5 years, long-term)
6. Past CRE investment experience
7. Capital available for investment
8. Investment timeline
9. Target return expectations (specific IRR range, equity multiple, or return descriptors)
10. Deal structure preferences (LP, JV, co-GP, REIT, DST)
11. Markets or regions to avoid

EXTRACTION RULES:
- Only extract information that was explicitly stated or strongly implied by the investor
- Use null/empty for fields where information was not discussed
- For numeric fields (capital, hold periods), only extract if specific numbers were mentioned
- For arrays (markets, property_types), only include items actually discussed
- Be conservative - it's better to leave a field empty than to guess
- Map informal language to our defined categories:
  - "I'm new to this" -> investment_experience: "first_time"
  - "I've done a few deals" -> investment_experience: "some_experience"
  - "I'm pretty conservative" -> risk_tolerance: "conservative"
  - "I like value-add deals" -> investment_strategy: "value_add"
  - "I'm looking for mid-teens returns" -> target_irr_min: 13, target_irr_max: 17
  - "double digit returns" -> target_irr_min: 10, target_irr_max: null
  - "I want something safe, maybe 8-10%" -> target_irr_min: 8, target_irr_max: 10
  - "I prefer LP positions" -> preferred_structures: ["LP"]
  - "I like to co-invest with the sponsor" -> preferred_structures: ["co-GP", "JV"]

PROPERTY TYPES (use these exact values):
- industrial
- multifamily
- office
- retail
- self-storage
- mixed-use

INVESTMENT STRATEGIES (use these exact values):
- core (stabilized, low risk)
- core_plus (mostly stabilized with minor improvements)
- value_add (significant improvements needed)
- opportunistic (development, major repositioning)

CONFIDENCE SCORING:
- 0.9-1.0: Clear, complete information with explicit statements
- 0.7-0.8: Good information but some inference required
- 0.5-0.6: Partial information, significant gaps
- 0.3-0.4: Limited useful information extracted
- 0.0-0.2: Very little or no useful information

Return a structured JSON response with the extracted information."""


class InsightExtractionService:
    """Service for extracting and saving investor insights from transcripts."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.investor_repo = InvestorRepository(session)

    async def extract_insights(self, transcript: str) -> TranscriptInsightExtraction:
        """Extract structured insights from a call transcript using LLM."""
        try:
            response = await self.client.responses.parse(
                model="gpt-5.2",
                input=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": f"Call Transcript:\n\n{transcript}",
                            }
                        ],
                    },
                ],
                text_format=TranscriptInsightExtraction,
            )
            return response.output_parsed
        except Exception as e:
            logger.error(f"Failed to extract insights: {e}")
            raise

    async def save_insights(
        self,
        investor_id: uuid.UUID,
        extraction: TranscriptInsightExtraction,
        min_confidence: float = 0.5,
    ) -> bool:
        """Save extracted insights to investor profile and preferences.

        Args:
            investor_id: UUID of the investor to update
            extraction: Extracted insights from transcript
            min_confidence: Minimum confidence score to save (default 0.5)

        Returns:
            True if insights were saved, False if skipped due to low confidence
        """
        if extraction.confidence_score < min_confidence:
            logger.warning(
                f"Extraction confidence {extraction.confidence_score} below threshold "
                f"{min_confidence} for investor {investor_id}"
            )
            return False

        investor = await self.investor_repo.get(investor_id)
        if not investor:
            logger.error(f"Investor {investor_id} not found")
            return False

        # Update profile fields (only non-null extractions)
        profile = extraction.profile_updates

        if profile.name and not investor.name:
            investor.name = profile.name
        if profile.timeline:
            investor.timeline = profile.timeline
        if profile.capital_available and not investor.capital_available:
            investor.capital_available = profile.capital_available
        if profile.investment_preferences:
            # Merge with existing preferences
            existing = set(investor.investment_preferences or [])
            investor.investment_preferences = list(
                existing | set(profile.investment_preferences)
            )
        if profile.investment_thesis:
            investor.investment_thesis = profile.investment_thesis
        if profile.risk_tolerance:
            investor.risk_tolerance = profile.risk_tolerance

        # Update or create preferences
        await self._update_preferences(investor_id, extraction)

        await self.session.flush()

        # Regenerate investor embeddings with updated profile data
        try:
            # Load preferences for rich embedding
            prefs_result = await self.session.execute(
                select(InvestorPreferences).where(
                    InvestorPreferences.investor_id == investor_id
                )
            )
            prefs = prefs_result.scalar_one_or_none()

            embedding_service = EmbeddingService(self.session)
            await embedding_service.create_investor_profile_embedding(
                investor_id=investor_id,
                investor=investor,
                preferences=prefs,
                call_summary=extraction.call_summary,
            )
            logger.info(f"Regenerated embeddings for investor {investor_id}")
        except Exception as e:
            logger.warning(f"Failed to regenerate investor embeddings: {e}")
            # Don't fail the extraction if embeddings fail

        return True

    async def _update_preferences(
        self,
        investor_id: uuid.UUID,
        extraction: TranscriptInsightExtraction,
    ) -> None:
        """Update or create investor preferences record."""
        prefs = extraction.preferences_updates

        result = await self.session.execute(
            select(InvestorPreferences).where(
                InvestorPreferences.investor_id == investor_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Merge arrays with existing data
            if prefs.property_types:
                existing_types = set(existing.property_types or [])
                existing.property_types = list(
                    existing_types | set(prefs.property_types)
                )
            if prefs.preferred_markets:
                existing_markets = set(existing.preferred_markets or [])
                existing.preferred_markets = list(
                    existing_markets | set(prefs.preferred_markets)
                )
            if prefs.excluded_markets:
                existing_excluded = set(existing.excluded_markets or [])
                existing.excluded_markets = list(
                    existing_excluded | set(prefs.excluded_markets)
                )
            if prefs.preferred_structures:
                existing_structs = set(existing.preferred_structures or [])
                existing.preferred_structures = list(
                    existing_structs | set(prefs.preferred_structures)
                )

            # Update scalar fields if not already set
            if prefs.risk_tolerance_level and not existing.risk_tolerance_level:
                existing.risk_tolerance_level = prefs.risk_tolerance_level
            if prefs.investment_strategy and not existing.investment_strategy:
                existing.investment_strategy = prefs.investment_strategy
            if prefs.hold_period_min and not existing.hold_period_min:
                existing.hold_period_min = prefs.hold_period_min
            if prefs.hold_period_max and not existing.hold_period_max:
                existing.hold_period_max = prefs.hold_period_max
            if prefs.investment_experience and not existing.investment_experience:
                existing.investment_experience = prefs.investment_experience
            if prefs.target_irr_min and not existing.target_irr_min:
                existing.target_irr_min = prefs.target_irr_min
            if prefs.target_irr_max and not existing.target_irr_max:
                existing.target_irr_max = prefs.target_irr_max
            if prefs.specific_concerns:
                # Append to existing concerns
                if existing.specific_concerns:
                    existing.specific_concerns = (
                        f"{existing.specific_concerns}\n\n{prefs.specific_concerns}"
                    )
                else:
                    existing.specific_concerns = prefs.specific_concerns
        else:
            # Create new preferences record
            new_prefs = InvestorPreferences(
                id=uuid.uuid4(),
                investor_id=investor_id,
                property_types=prefs.property_types or [],
                preferred_markets=prefs.preferred_markets or [],
                excluded_markets=prefs.excluded_markets or [],
                risk_tolerance_level=prefs.risk_tolerance_level,
                investment_strategy=prefs.investment_strategy,
                hold_period_min=prefs.hold_period_min,
                hold_period_max=prefs.hold_period_max,
                investment_experience=prefs.investment_experience,
                specific_concerns=prefs.specific_concerns,
                preferred_structures=prefs.preferred_structures or [],
                target_irr_min=prefs.target_irr_min,
                target_irr_max=prefs.target_irr_max,
            )
            self.session.add(new_prefs)

    async def _update_call_extraction_status(
        self,
        call_session_id: uuid.UUID,
        status: str,
        confidence: Optional[float] = None,
        summary: Optional[str] = None,
    ) -> None:
        """Update extraction status on the call session."""
        values = {
            "extraction_status": status,
            "extracted_at": datetime.utcnow() if status in ("completed", "failed") else None,
        }
        if confidence is not None:
            values["extraction_confidence"] = confidence
        if summary is not None:
            values["extraction_summary"] = summary[:500]  # Truncate to fit

        await self.session.execute(
            update(CallSession)
            .where(CallSession.id == call_session_id)
            .values(**values)
        )

    async def extract_and_save(
        self,
        investor_id: uuid.UUID,
        call_session_id: uuid.UUID,
        transcript: str,
    ) -> Optional[TranscriptInsightExtraction]:
        """Complete extraction workflow: extract insights and save to database.

        Args:
            investor_id: UUID of the investor
            call_session_id: UUID of the call session (for logging)
            transcript: Full transcript text from the call

        Returns:
            TranscriptInsightExtraction if successful, None on failure
        """
        try:
            logger.info(f"Starting insight extraction for call {call_session_id}")

            # Mark extraction as pending
            await self._update_call_extraction_status(call_session_id, "pending")
            await self.session.commit()

            extraction = await self.extract_insights(transcript)

            logger.info(
                f"Extraction complete (confidence: {extraction.confidence_score}): "
                f"{extraction.call_summary[:100]}..."
            )

            saved = await self.save_insights(investor_id, extraction)

            if saved:
                # Update investor stage to insights_extracted
                await self.investor_repo.update_stage(
                    investor_id=investor_id,
                    new_stage="insights_extracted",
                    changed_by="system",
                    notes=f"Insights extracted from call. Confidence: {extraction.confidence_score:.2f}",
                )

            # Update call session with extraction results
            await self._update_call_extraction_status(
                call_session_id,
                status="completed",
                confidence=extraction.confidence_score,
                summary=extraction.call_summary,
            )

            await self.session.commit()
            logger.info(f"Insights saved for investor {investor_id}")

            return extraction

        except Exception as e:
            logger.error(f"Insight extraction failed for call {call_session_id}: {e}")
            # Mark extraction as failed
            try:
                await self._update_call_extraction_status(
                    call_session_id, "failed", summary=str(e)[:500]
                )
                await self.session.commit()
            except Exception:
                await self.session.rollback()
            return None


# Singleton instance
_insight_extraction_service: Optional[InsightExtractionService] = None


def get_insight_extraction_service(
    session: AsyncSession,
) -> InsightExtractionService:
    """Get InsightExtractionService instance for the given session."""
    return InsightExtractionService(session)
