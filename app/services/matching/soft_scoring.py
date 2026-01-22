"""
Soft Scoring - Layer 2 of the matching engine.

Soft scoring assigns weighted points (0-100) based on how well
an investor's preferences align with a deal's characteristics.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.models.financial import InvestmentMetrics
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.property import Property

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of soft score components."""

    return_match: float = 0.0  # Max 25 points
    risk_match: float = 0.0  # Max 20 points
    geography_match: float = 0.0  # Max 15 points
    structure_match: float = 0.0  # Max 15 points
    hold_period_match: float = 0.0  # Max 10 points
    strategy_match: float = 0.0  # Max 10 points
    capacity_fit: float = 0.0  # Max 5 points


@dataclass
class SoftScoreResult:
    """Result of soft scoring evaluation."""

    score: float  # 0-100
    breakdown: ScoreBreakdown
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)


class SoftScorer:
    """
    Layer 2: Soft scoring for investor-deal matching.

    Scoring weights (total 100 points):
    - Return match: 25 points
    - Risk match: 20 points
    - Geography match: 15 points
    - Structure match: 15 points
    - Hold period match: 10 points
    - Strategy match: 10 points
    - Capacity fit: 5 points
    """

    # Scoring weights
    WEIGHTS = {
        "return_match": 25,
        "risk_match": 20,
        "geography_match": 15,
        "structure_match": 15,
        "hold_period_match": 10,
        "strategy_match": 10,
        "capacity_fit": 5,
    }

    def score(
        self,
        investor: InvestorProfile,
        property: Property,
        preferences: Optional[InvestorPreferences] = None,
        investment_metrics: Optional[InvestmentMetrics] = None,
    ) -> SoftScoreResult:
        """
        Calculate soft score for an investor-property pair.

        Args:
            investor: The investor profile
            property: The property/deal
            preferences: Optional detailed preferences
            investment_metrics: Optional deal investment metrics

        Returns:
            SoftScoreResult with total score, breakdown, and match details
        """
        breakdown = ScoreBreakdown()
        match_reasons = []
        concerns = []

        # Score each category
        breakdown.return_match = self._score_return_match(
            preferences, investment_metrics, match_reasons, concerns
        )

        breakdown.risk_match = self._score_risk_match(
            investor, property, preferences, match_reasons, concerns
        )

        breakdown.geography_match = self._score_geography_match(
            property, preferences, match_reasons, concerns
        )

        breakdown.structure_match = self._score_structure_match(
            property, preferences, match_reasons, concerns
        )

        breakdown.hold_period_match = self._score_hold_period_match(
            property, preferences, match_reasons, concerns
        )

        breakdown.strategy_match = self._score_strategy_match(
            property, preferences, match_reasons, concerns
        )

        breakdown.capacity_fit = self._score_capacity_fit(
            investor, property, match_reasons, concerns
        )

        # Calculate total score
        total_score = (
            breakdown.return_match
            + breakdown.risk_match
            + breakdown.geography_match
            + breakdown.structure_match
            + breakdown.hold_period_match
            + breakdown.strategy_match
            + breakdown.capacity_fit
        )

        logger.debug(
            f"Soft score for investor {investor.id} on property {property.id}: "
            f"{total_score:.1f}/100"
        )

        return SoftScoreResult(
            score=total_score,
            breakdown=breakdown,
            match_reasons=match_reasons,
            concerns=concerns,
        )

    def _score_return_match(
        self,
        preferences: Optional[InvestorPreferences],
        metrics: Optional[InvestmentMetrics],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score return expectations alignment (max 25 points)."""
        if not preferences or not metrics:
            return self.WEIGHTS["return_match"] * 0.5  # Neutral if no data

        # Compare target IRR ranges
        if preferences.target_irr_min and metrics.target_irr_min:
            deal_irr_mid = (
                (metrics.target_irr_min or 0) + (metrics.target_irr_max or 0)
            ) / 2 if metrics.target_irr_max else metrics.target_irr_min

            pref_irr_mid = (
                (preferences.target_irr_min or 0) + (preferences.target_irr_max or 0)
            ) / 2 if preferences.target_irr_max else preferences.target_irr_min

            # Calculate how close the IRR is to preference
            irr_diff = abs(deal_irr_mid - pref_irr_mid)

            if irr_diff <= 2:  # Within 2% of target
                match_reasons.append("Return target closely matches preferences")
                return self.WEIGHTS["return_match"]
            elif irr_diff <= 5:  # Within 5%
                match_reasons.append("Return target reasonably aligned")
                return self.WEIGHTS["return_match"] * 0.75
            elif irr_diff <= 10:
                concerns.append("Return target slightly misaligned with preferences")
                return self.WEIGHTS["return_match"] * 0.5
            else:
                concerns.append("Return target significantly different from preferences")
                return self.WEIGHTS["return_match"] * 0.25

        return self.WEIGHTS["return_match"] * 0.5

    def _score_risk_match(
        self,
        investor: InvestorProfile,
        property: Property,
        preferences: Optional[InvestorPreferences],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score risk tolerance alignment (max 20 points)."""
        # Use either preferences risk level or investor's basic risk tolerance
        risk_level = None
        if preferences and preferences.risk_tolerance_level:
            risk_level = preferences.risk_tolerance_level
        elif investor.risk_tolerance:
            risk_level = investor.risk_tolerance

        if not risk_level:
            return self.WEIGHTS["risk_match"] * 0.5

        # Map risk level to numeric value
        risk_map = {
            "conservative": 1,
            "moderate": 2,
            "aggressive": 3,
        }
        investor_risk = risk_map.get(risk_level.lower(), 2)

        # Estimate deal risk from risk factors count
        deal_risk = 2  # Default moderate
        if property.risk_factors:
            num_risks = len(property.risk_factors)
            if num_risks >= 5:
                deal_risk = 3  # High risk
            elif num_risks <= 2:
                deal_risk = 1  # Low risk

        risk_diff = abs(investor_risk - deal_risk)

        if risk_diff == 0:
            match_reasons.append("Risk profile aligns with deal")
            return self.WEIGHTS["risk_match"]
        elif risk_diff == 1:
            return self.WEIGHTS["risk_match"] * 0.7
        else:
            concerns.append("Risk profile mismatch")
            return self.WEIGHTS["risk_match"] * 0.3

    def _score_geography_match(
        self,
        property: Property,
        preferences: Optional[InvestorPreferences],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score geographic preference alignment (max 15 points)."""
        if not preferences or not preferences.preferred_markets:
            return self.WEIGHTS["geography_match"] * 0.5

        property_market = None
        if property.city:
            property_market = property.city.lower()
        elif property.state:
            property_market = property.state.lower()

        if not property_market:
            return self.WEIGHTS["geography_match"] * 0.5

        # Check if property is in preferred markets
        preferred_lower = [m.lower() for m in preferences.preferred_markets]
        if property_market in preferred_lower:
            match_reasons.append(f"Located in preferred market: {property.city}")
            return self.WEIGHTS["geography_match"]

        # Partial match for state-level preferences
        if property.state and property.state.lower() in preferred_lower:
            match_reasons.append(f"Located in preferred state: {property.state}")
            return self.WEIGHTS["geography_match"] * 0.8

        return self.WEIGHTS["geography_match"] * 0.3

    def _score_structure_match(
        self,
        property: Property,
        preferences: Optional[InvestorPreferences],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score deal structure preference alignment (max 15 points)."""
        if not preferences or not preferences.preferred_structures:
            return self.WEIGHTS["structure_match"] * 0.5

        if not property.structure:
            return self.WEIGHTS["structure_match"] * 0.5

        deal_structure = property.structure.lower()
        preferred_lower = [s.lower() for s in preferences.preferred_structures]

        if deal_structure in preferred_lower:
            match_reasons.append(f"Preferred structure: {property.structure}")
            return self.WEIGHTS["structure_match"]

        # Partial matches for related structures
        related_structures = {
            "lp/gp": ["limited partnership", "lp", "gp"],
            "llc": ["limited liability company"],
            "reit": ["real estate investment trust"],
            "jv": ["joint venture"],
        }

        for preferred in preferred_lower:
            if preferred in related_structures.get(deal_structure, []):
                return self.WEIGHTS["structure_match"] * 0.8

        return self.WEIGHTS["structure_match"] * 0.3

    def _score_hold_period_match(
        self,
        property: Property,
        preferences: Optional[InvestorPreferences],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score hold period preference alignment (max 10 points)."""
        if not preferences:
            return self.WEIGHTS["hold_period_match"] * 0.5

        if not preferences.hold_period_min and not preferences.hold_period_max:
            return self.WEIGHTS["hold_period_match"] * 0.5

        # Parse deal timeline (e.g., "5-7 years")
        deal_hold = self._parse_timeline(property.timeline)
        if not deal_hold:
            return self.WEIGHTS["hold_period_match"] * 0.5

        pref_min = preferences.hold_period_min or 0
        pref_max = preferences.hold_period_max or 99

        if pref_min <= deal_hold <= pref_max:
            match_reasons.append(f"Hold period ({deal_hold} years) within preference")
            return self.WEIGHTS["hold_period_match"]

        # Slight mismatch (within 2 years)
        if abs(deal_hold - pref_min) <= 2 or abs(deal_hold - pref_max) <= 2:
            return self.WEIGHTS["hold_period_match"] * 0.6

        concerns.append("Hold period outside preferred range")
        return self.WEIGHTS["hold_period_match"] * 0.2

    def _score_strategy_match(
        self,
        property: Property,
        preferences: Optional[InvestorPreferences],
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score investment strategy alignment (max 10 points)."""
        if not preferences or not preferences.investment_strategy:
            return self.WEIGHTS["strategy_match"] * 0.5

        # Infer deal strategy from value_add_strategy presence
        deal_strategy = "core"  # Default
        if hasattr(property, "value_add_strategy") and property.value_add_strategy:
            deal_strategy = "value_add"

        # Map investor preference to strategy
        pref_strategy = preferences.investment_strategy.lower()
        strategy_compatibility = {
            "core": ["core", "core_plus"],
            "core_plus": ["core", "core_plus", "value_add"],
            "value_add": ["value_add", "core_plus", "opportunistic"],
            "opportunistic": ["opportunistic", "value_add"],
        }

        compatible = strategy_compatibility.get(pref_strategy, [])
        if deal_strategy in compatible:
            match_reasons.append(f"Strategy aligned: {deal_strategy}")
            return self.WEIGHTS["strategy_match"]

        return self.WEIGHTS["strategy_match"] * 0.3

    def _score_capacity_fit(
        self,
        investor: InvestorProfile,
        property: Property,
        match_reasons: List[str],
        concerns: List[str],
    ) -> float:
        """Score capacity/allocation fit (max 5 points)."""
        if not property.minimum_investment or not investor.capital_available:
            return self.WEIGHTS["capacity_fit"] * 0.5

        min_invest = property.minimum_investment
        capacity = investor.capital_available

        # Check if investment is reasonable portion of capacity
        ratio = min_invest / capacity if capacity > 0 else 1

        if 0.05 <= ratio <= 0.25:  # 5-25% of capacity is ideal
            match_reasons.append("Investment size appropriate for capacity")
            return self.WEIGHTS["capacity_fit"]
        elif ratio < 0.05:  # Too small relative to capacity
            return self.WEIGHTS["capacity_fit"] * 0.8
        elif ratio <= 0.5:  # Up to half of capacity
            return self.WEIGHTS["capacity_fit"] * 0.6
        else:  # More than half of capacity
            concerns.append("Investment may exceed comfortable allocation")
            return self.WEIGHTS["capacity_fit"] * 0.3

    def _parse_timeline(self, timeline: Optional[str]) -> Optional[int]:
        """Parse timeline string to extract average years."""
        if not timeline:
            return None

        # Try to extract numbers from strings like "5-7 years", "5 years", etc.
        import re

        numbers = re.findall(r"\d+", timeline)
        if numbers:
            nums = [int(n) for n in numbers]
            return sum(nums) // len(nums)  # Average

        return None

    def to_dict(self, result: SoftScoreResult) -> Dict:
        """Convert SoftScoreResult to dictionary for storage."""
        return {
            "score": result.score,
            "breakdown": {
                "return_match": result.breakdown.return_match,
                "risk_match": result.breakdown.risk_match,
                "geography_match": result.breakdown.geography_match,
                "structure_match": result.breakdown.structure_match,
                "hold_period_match": result.breakdown.hold_period_match,
                "strategy_match": result.breakdown.strategy_match,
                "capacity_fit": result.breakdown.capacity_fit,
            },
            "match_reasons": result.match_reasons,
            "concerns": result.concerns,
        }
