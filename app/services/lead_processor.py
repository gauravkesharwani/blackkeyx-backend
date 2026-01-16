"""
Lead processing service.

Handles the full lead submission flow:
1. Create investor profile
2. Store TCPA consent
3. Record initial stage
4. (Future) Dispatch voice call via LiveKit
"""

import uuid
from typing import Optional

from app.db.repositories.investor_repo import InvestorRepository
from app.models.consent import Consent, StageHistory
from app.models.investor import InvestorProfile
from app.schemas.lead import LeadSubmissionRequest


def parse_capital_to_int(capital_str: Optional[str]) -> Optional[int]:
    """
    Parse capital string to integer value.

    Maps frontend capacity options to midpoint values:
    - '$100K-$250K' -> 175000
    - '$250K-$500K' -> 375000
    - '$500K-$1M' -> 750000
    - '$1M+' -> 1500000
    """
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


class LeadProcessor:
    """Service for processing incoming leads."""

    def __init__(self, investor_repo: InvestorRepository):
        self.investor_repo = investor_repo

    async def process_lead(
        self,
        lead_data: LeadSubmissionRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> InvestorProfile:
        """
        Process a new lead submission.

        Steps:
        1. Check for existing lead by phone
        2. Create investor profile
        3. Store TCPA consent
        4. Record initial stage change

        Returns:
            InvestorProfile: The created or existing investor
        """
        # Check for existing lead
        existing = await self.investor_repo.get_by_phone(lead_data.phoneNumber)
        if existing:
            return existing

        # Parse capital
        capital_available = None
        if lead_data.qualification:
            capital_available = parse_capital_to_int(lead_data.qualification.capacity)
        elif lead_data.capitalAvailable:
            capital_available = parse_capital_to_int(lead_data.capitalAvailable)

        # Create investor profile
        investor = InvestorProfile(
            id=uuid.uuid4(),
            phone=lead_data.phoneNumber,
            timeline=lead_data.investmentTimeline,
            capital_available=capital_available,
            investment_preferences=lead_data.investmentPreferences or [],
            stage="new_lead",
            source="web",
        )

        # Add qualification data
        if lead_data.qualification:
            q = lead_data.qualification
            investor.investor_type = q.investorType
            investor.capacity = q.capacity
            investor.fit = q.fit
            investor.process = q.process
            investor.timing = q.timing
            investor.qualification_bucket = q.bucket
            investor.qualification_score = q.score
            investor.lead_score = q.score

        # Save investor
        investor = await self.investor_repo.create(investor)

        # Store consent
        await self.investor_repo.add_consent(
            investor_id=investor.id,
            consent_text="TCPA consent granted via web chatbot",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return investor

    async def dispatch_call(self, investor_id: uuid.UUID) -> Optional[str]:
        """
        Dispatch a voice call to the investor via LiveKit.

        TODO: Implement LiveKit integration in Phase 2.

        Returns:
            Optional[str]: Room name if call dispatched, None otherwise
        """
        # Placeholder for LiveKit integration
        # Will be implemented in Phase 2
        return None
