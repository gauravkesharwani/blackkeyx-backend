"""
Hard Filters - Layer 1 of the matching engine.

Hard filters are pass/fail checks that determine if an investor
should even be considered for a deal. If any hard filter fails,
the investor is excluded from the match.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.property import Property

logger = logging.getLogger(__name__)


@dataclass
class HardFilterResult:
    """Result of hard filter evaluation."""

    passed: bool
    failed_filters: List[str]
    details: dict


class HardFilters:
    """
    Layer 1: Hard filters for investor-deal matching.

    These are non-negotiable pass/fail criteria:
    1. Investment capacity vs minimum investment
    2. Property type in preferences
    3. Market exclusion list
    4. Deal status (must be active)
    """

    def evaluate(
        self,
        investor: InvestorProfile,
        property: Property,
        preferences: Optional[InvestorPreferences] = None,
    ) -> HardFilterResult:
        """
        Evaluate all hard filters for an investor-property pair.

        Args:
            investor: The investor profile
            property: The property/deal
            preferences: Optional detailed preferences

        Returns:
            HardFilterResult with pass/fail status and details
        """
        failed_filters = []
        details = {}

        # Filter 1: Deal must be active
        if property.status != "active":
            failed_filters.append("deal_inactive")
            details["deal_status"] = property.status

        # Filter 2: Investment capacity check
        if property.minimum_investment and investor.capital_available:
            if investor.capital_available < property.minimum_investment:
                failed_filters.append("insufficient_capital")
                details["required"] = property.minimum_investment
                details["available"] = investor.capital_available

        # Filter 3: Property type preference (if preferences exist)
        if preferences and preferences.property_types:
            if property.deal_type and property.deal_type.lower() not in [
                pt.lower() for pt in preferences.property_types
            ]:
                failed_filters.append("property_type_mismatch")
                details["deal_type"] = property.deal_type
                details["preferred_types"] = preferences.property_types

        # Filter 4: Market exclusion check
        if preferences and preferences.excluded_markets:
            property_market = self._get_property_market(property)
            if property_market:
                excluded_lower = [m.lower() for m in preferences.excluded_markets]
                if property_market.lower() in excluded_lower:
                    failed_filters.append("excluded_market")
                    details["property_market"] = property_market
                    details["excluded_markets"] = preferences.excluded_markets

        passed = len(failed_filters) == 0

        if not passed:
            logger.debug(
                f"Hard filter failed for investor {investor.id} "
                f"on property {property.id}: {failed_filters}"
            )

        return HardFilterResult(
            passed=passed,
            failed_filters=failed_filters,
            details=details,
        )

    def _get_property_market(self, property: Property) -> Optional[str]:
        """Extract market name from property (city or market_analysis)."""
        if property.city:
            return property.city

        # Try market_analysis if available
        if hasattr(property, "market_analysis") and property.market_analysis:
            if property.market_analysis.market_name:
                return property.market_analysis.market_name

        return None

    def batch_evaluate(
        self,
        investor: InvestorProfile,
        properties: List[Property],
        preferences: Optional[InvestorPreferences] = None,
    ) -> List[tuple]:
        """
        Evaluate hard filters for an investor against multiple properties.

        Args:
            investor: The investor profile
            properties: List of properties to evaluate
            preferences: Optional detailed preferences

        Returns:
            List of (property, HardFilterResult) tuples that passed
        """
        results = []
        for prop in properties:
            result = self.evaluate(investor, prop, preferences)
            if result.passed:
                results.append((prop, result))

        logger.info(
            f"Hard filters: {len(results)}/{len(properties)} properties "
            f"passed for investor {investor.id}"
        )
        return results
