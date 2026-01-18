"""Admin service for dashboard operations."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Sequence, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.call_repo import CallRepository
from app.db.repositories.investor_repo import InvestorRepository
from app.db.repositories.property_repo import PropertyRepository
from app.models.consent import LeadNote
from app.models.investor import InvestorProfile
from app.services.livekit_dispatcher import get_livekit_dispatcher

logger = logging.getLogger(__name__)


class AdminService:
    """Service for admin dashboard operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.investor_repo = InvestorRepository(session)
        self.property_repo = PropertyRepository(session)
        self.call_repo = CallRepository(session)
        self.livekit = get_livekit_dispatcher()

    async def get_dashboard_stats(self) -> dict:
        """Get dashboard statistics."""
        total_leads = await self.investor_repo.count()
        by_stage = await self.investor_repo.get_stats_by_stage()
        average_score = await self.investor_repo.get_average_score()
        total_deals = await self.property_repo.count()
        return {
            "total_leads": total_leads,
            "by_stage": by_stage,
            "average_score": average_score,
            "total_deals": total_deals,
        }

    async def get_recent_leads(self, limit: int = 5) -> Sequence[InvestorProfile]:
        """Get recent leads for activity feed."""
        leads, _ = await self.investor_repo.search_leads(limit=limit)
        return leads

    async def search_leads(
        self,
        stage: Optional[str] = None,
        score_min: Optional[int] = None,
        score_max: Optional[int] = None,
        capital_min: Optional[int] = None,
        capital_max: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[Sequence[InvestorProfile], int]:
        """Search leads with filters."""
        return await self.investor_repo.search_leads(
            stage=stage,
            score_min=score_min,
            score_max=score_max,
            capital_min=capital_min,
            capital_max=capital_max,
            date_from=date_from,
            date_to=date_to,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

    async def get_lead(self, lead_id: uuid.UUID) -> Optional[InvestorProfile]:
        """Get lead with all relations."""
        return await self.investor_repo.get_with_relations(lead_id)

    async def update_lead_stage(
        self,
        lead_id: uuid.UUID,
        new_stage: str,
        notes: Optional[str] = None,
    ) -> Optional[InvestorProfile]:
        """Update lead stage and dispatch call if needed."""
        lead = await self.investor_repo.get_with_relations(lead_id)
        if not lead:
            return None

        # Update stage
        await self.investor_repo.update_stage(
            investor_id=lead_id,
            new_stage=new_stage,
            changed_by="admin",
            notes=notes,
        )

        # Auto-dispatch call when stage changes to call_dispatched
        if new_stage == "call_dispatched":
            investor_context = {
                "investor_id": str(lead_id),
                "name": lead.name or "there",
                "capital_available": lead.capacity or lead.capital_available,
                "timeline": lead.timeline,
                "investment_preferences": lead.investment_preferences or [],
            }

            room_name = await self.livekit.dispatch_outbound_call(
                phone_number=lead.phone,
                investor_context=investor_context,
            )

            await self.call_repo.create_call(
                investor_id=lead_id,
                room_name=room_name,
                status="initiated",
            )

        await self.session.commit()
        return await self.investor_repo.get_with_relations(lead_id)

    async def add_lead_note(
        self,
        lead_id: uuid.UUID,
        content: str,
    ) -> Optional[LeadNote]:
        """Add a note to a lead."""
        return await self.investor_repo.add_note(
            investor_id=lead_id,
            content=content,
            created_by="admin",
        )
