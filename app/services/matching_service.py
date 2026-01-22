"""
Matching Service - Combines all three matching layers.

This service orchestrates the full matching pipeline:
1. Hard Filters (pass/fail)
2. Soft Scoring (0-100 weighted)
3. Semantic Matching (0-100 via embeddings)

Final Score = soft_score * 0.7 + semantic_score * 0.3
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial import InvestmentMetrics
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.matching import DealMatch
from app.models.property import Property
from app.services.matching.hard_filters import HardFilterResult, HardFilters
from app.services.matching.semantic_match import SemanticMatcher, SemanticMatchResult
from app.services.matching.soft_scoring import SoftScorer, SoftScoreResult

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Complete match result for an investor-property pair."""

    investor_id: uuid.UUID
    property_id: uuid.UUID
    hard_filter_passed: bool
    hard_filter_details: Dict = field(default_factory=dict)
    soft_score: float = 0.0
    soft_score_breakdown: Dict = field(default_factory=dict)
    semantic_score: float = 0.0
    final_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)


class MatchingService:
    """
    Main matching service that orchestrates all matching layers.

    Final score formula: soft_score * 0.7 + semantic_score * 0.3
    """

    SOFT_WEIGHT = 0.7
    SEMANTIC_WEIGHT = 0.3

    def __init__(self, session: AsyncSession):
        self.session = session
        self.hard_filters = HardFilters()
        self.soft_scorer = SoftScorer()
        self.semantic_matcher = SemanticMatcher(session)

    async def match_investor_to_properties(
        self,
        investor_id: uuid.UUID,
        property_ids: Optional[List[uuid.UUID]] = None,
        min_score: float = 0.0,
        limit: int = 50,
        save_matches: bool = True,
    ) -> List[MatchResult]:
        """
        Match an investor against properties.

        Args:
            investor_id: UUID of the investor
            property_ids: Optional list of specific properties to match
            min_score: Minimum final score threshold
            limit: Maximum number of matches to return
            save_matches: Whether to save matches to database

        Returns:
            List of MatchResult objects sorted by final_score descending
        """
        # Load investor with preferences
        investor = await self._load_investor(investor_id)
        if not investor:
            logger.error(f"Investor {investor_id} not found")
            return []

        # Load properties
        if property_ids:
            properties = await self._load_properties(property_ids)
        else:
            properties = await self._load_active_properties(limit=limit * 2)

        if not properties:
            logger.warning("No properties found for matching")
            return []

        # Run matching pipeline
        results = []
        for prop in properties:
            result = await self._match_single(investor, prop)
            if result.hard_filter_passed and result.final_score >= min_score:
                results.append(result)

        # Sort by final score descending
        results.sort(key=lambda r: r.final_score, reverse=True)
        results = results[:limit]

        # Save matches if requested
        if save_matches and results:
            await self._save_matches(results)

        logger.info(
            f"Matching complete for investor {investor_id}: "
            f"{len(results)} matches found"
        )

        return results

    async def match_property_to_investors(
        self,
        property_id: uuid.UUID,
        investor_ids: Optional[List[uuid.UUID]] = None,
        min_score: float = 0.0,
        limit: int = 50,
        save_matches: bool = True,
    ) -> List[MatchResult]:
        """
        Match a property against investors.

        Args:
            property_id: UUID of the property
            investor_ids: Optional list of specific investors to match
            min_score: Minimum final score threshold
            limit: Maximum number of matches to return
            save_matches: Whether to save matches to database

        Returns:
            List of MatchResult objects sorted by final_score descending
        """
        # Load property with metrics
        prop = await self._load_property(property_id)
        if not prop:
            logger.error(f"Property {property_id} not found")
            return []

        # Load investors
        if investor_ids:
            investors = await self._load_investors(investor_ids)
        else:
            investors = await self._load_qualified_investors(limit=limit * 2)

        if not investors:
            logger.warning("No investors found for matching")
            return []

        # Run matching pipeline
        results = []
        for investor in investors:
            result = await self._match_single(investor, prop)
            if result.hard_filter_passed and result.final_score >= min_score:
                results.append(result)

        # Sort by final score descending
        results.sort(key=lambda r: r.final_score, reverse=True)
        results = results[:limit]

        # Save matches if requested
        if save_matches and results:
            await self._save_matches(results)

        logger.info(
            f"Matching complete for property {property_id}: "
            f"{len(results)} investor matches found"
        )

        return results

    async def run_full_matching(
        self,
        min_score: float = 30.0,
        save_matches: bool = True,
    ) -> Dict:
        """
        Run matching for all active deals against all qualified investors.

        Args:
            min_score: Minimum final score threshold
            save_matches: Whether to save matches to database

        Returns:
            Summary statistics of matching run
        """
        # Load all active properties
        properties = await self._load_active_properties(limit=1000)

        # Load all qualified investors
        investors = await self._load_qualified_investors(limit=1000)

        logger.info(
            f"Running full matching: {len(properties)} properties x "
            f"{len(investors)} investors"
        )

        total_matches = 0
        all_results = []

        for prop in properties:
            for investor in investors:
                result = await self._match_single(investor, prop)
                if result.hard_filter_passed and result.final_score >= min_score:
                    all_results.append(result)
                    total_matches += 1

        # Save matches
        if save_matches and all_results:
            await self._save_matches(all_results)

        stats = {
            "properties_evaluated": len(properties),
            "investors_evaluated": len(investors),
            "total_pairs_evaluated": len(properties) * len(investors),
            "matches_found": total_matches,
            "min_score_threshold": min_score,
        }

        logger.info(f"Full matching complete: {stats}")
        return stats

    async def _match_single(
        self,
        investor: InvestorProfile,
        prop: Property,
    ) -> MatchResult:
        """
        Run full matching pipeline for a single investor-property pair.
        """
        result = MatchResult(
            investor_id=investor.id,
            property_id=prop.id,
            hard_filter_passed=False,
        )

        # Get preferences and metrics
        preferences = await self._get_investor_preferences(investor.id)
        metrics = await self._get_investment_metrics(prop.id)

        # Layer 1: Hard Filters
        hard_result = self.hard_filters.evaluate(investor, prop, preferences)
        result.hard_filter_passed = hard_result.passed
        result.hard_filter_details = hard_result.details

        if not hard_result.passed:
            return result

        # Layer 2: Soft Scoring
        soft_result = self.soft_scorer.score(
            investor, prop, preferences, metrics
        )
        result.soft_score = soft_result.score
        result.soft_score_breakdown = self.soft_scorer.to_dict(soft_result)
        result.match_reasons.extend(soft_result.match_reasons)
        result.concerns.extend(soft_result.concerns)

        # Layer 3: Semantic Matching
        semantic_result = await self.semantic_matcher.compute_semantic_score(
            investor.id, prop.id
        )
        result.semantic_score = semantic_result.score

        # Calculate final score
        result.final_score = (
            result.soft_score * self.SOFT_WEIGHT
            + result.semantic_score * self.SEMANTIC_WEIGHT
        )

        return result

    async def _save_matches(self, results: List[MatchResult]) -> None:
        """Save match results to database."""
        for result in results:
            # Check for existing match
            existing = await self.session.execute(
                select(DealMatch).where(
                    DealMatch.investor_id == result.investor_id,
                    DealMatch.property_id == result.property_id,
                )
            )
            match = existing.scalar_one_or_none()

            if match:
                # Update existing match
                match.hard_filter_passed = result.hard_filter_passed
                match.soft_score = result.soft_score
                match.semantic_score = result.semantic_score
                match.final_score = result.final_score
                match.similarity_score = result.final_score / 100.0
                match.match_reasons = result.match_reasons
                match.concerns = result.concerns
                match.score_breakdown = result.soft_score_breakdown
            else:
                # Create new match
                match = DealMatch(
                    id=uuid.uuid4(),
                    investor_id=result.investor_id,
                    property_id=result.property_id,
                    hard_filter_passed=result.hard_filter_passed,
                    soft_score=result.soft_score,
                    semantic_score=result.semantic_score,
                    final_score=result.final_score,
                    similarity_score=result.final_score / 100.0,
                    match_reasons=result.match_reasons,
                    concerns=result.concerns,
                    score_breakdown=result.soft_score_breakdown,
                    status="pending",
                )
                self.session.add(match)

        await self.session.flush()

    # ==================== Data Loading Helpers ====================

    async def _load_investor(
        self, investor_id: uuid.UUID
    ) -> Optional[InvestorProfile]:
        """Load an investor by ID."""
        result = await self.session.execute(
            select(InvestorProfile).where(InvestorProfile.id == investor_id)
        )
        return result.scalar_one_or_none()

    async def _load_investors(
        self, investor_ids: List[uuid.UUID]
    ) -> List[InvestorProfile]:
        """Load investors by IDs."""
        result = await self.session.execute(
            select(InvestorProfile).where(InvestorProfile.id.in_(investor_ids))
        )
        return list(result.scalars().all())

    async def _load_qualified_investors(
        self, limit: int = 100
    ) -> List[InvestorProfile]:
        """Load qualified investors for matching."""
        result = await self.session.execute(
            select(InvestorProfile)
            .where(
                InvestorProfile.qualification_bucket.in_(
                    ["active_intro", "nurture"]
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _load_property(self, property_id: uuid.UUID) -> Optional[Property]:
        """Load a property by ID."""
        result = await self.session.execute(
            select(Property).where(Property.id == property_id)
        )
        return result.scalar_one_or_none()

    async def _load_properties(
        self, property_ids: List[uuid.UUID]
    ) -> List[Property]:
        """Load properties by IDs."""
        result = await self.session.execute(
            select(Property).where(Property.id.in_(property_ids))
        )
        return list(result.scalars().all())

    async def _load_active_properties(self, limit: int = 100) -> List[Property]:
        """Load active properties for matching."""
        result = await self.session.execute(
            select(Property).where(Property.status == "active").limit(limit)
        )
        return list(result.scalars().all())

    async def _get_investor_preferences(
        self, investor_id: uuid.UUID
    ) -> Optional[InvestorPreferences]:
        """Get investor preferences if they exist."""
        result = await self.session.execute(
            select(InvestorPreferences).where(
                InvestorPreferences.investor_id == investor_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_investment_metrics(
        self, property_id: uuid.UUID
    ) -> Optional[InvestmentMetrics]:
        """Get investment metrics if they exist."""
        result = await self.session.execute(
            select(InvestmentMetrics).where(
                InvestmentMetrics.property_id == property_id
            )
        )
        return result.scalar_one_or_none()
