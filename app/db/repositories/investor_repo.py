"""Investor repository with filtering and search capabilities."""

import uuid
from datetime import datetime
from typing import Dict, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.consent import Consent, LeadNote, StageHistory
from app.models.investor import InvestorProfile


class InvestorRepository(BaseRepository[InvestorProfile]):
    """Repository for investor/lead operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(InvestorProfile, session)

    async def get_with_relations(
        self, id: uuid.UUID
    ) -> Optional[InvestorProfile]:
        """Get investor with all related data (calls, matches, notes, stage_history)."""
        result = await self.session.execute(
            select(InvestorProfile)
            .options(
                selectinload(InvestorProfile.calls),
                selectinload(InvestorProfile.matches),
                selectinload(InvestorProfile.notes),
                selectinload(InvestorProfile.stage_history),
                selectinload(InvestorProfile.consents),
            )
            .where(InvestorProfile.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[InvestorProfile]:
        """Get investor by phone number."""
        result = await self.session.execute(
            select(InvestorProfile).where(InvestorProfile.phone == phone)
        )
        return result.scalar_one_or_none()

    async def get_by_stage(self, stage: str) -> Sequence[InvestorProfile]:
        """Get all investors in a specific pipeline stage."""
        result = await self.session.execute(
            select(InvestorProfile)
            .where(InvestorProfile.stage == stage)
            .order_by(InvestorProfile.lead_score.desc())
        )
        return result.scalars().all()

    async def get_stats_by_stage(self) -> Dict[str, int]:
        """Get count of investors per pipeline stage."""
        result = await self.session.execute(
            select(InvestorProfile.stage, func.count(InvestorProfile.id))
            .group_by(InvestorProfile.stage)
        )
        return dict(result.all())

    async def get_average_score(self) -> float:
        """Get average lead score."""
        result = await self.session.execute(
            select(func.avg(InvestorProfile.lead_score))
        )
        avg = result.scalar_one_or_none()
        return float(avg) if avg else 0.0

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
        """
        Search leads with filters, pagination, and sorting.
        Returns (leads, total_count).

        Matches frontend LeadFilters interface:
        - stage: PipelineStage filter
        - score_min/max: Lead score range
        - capital_min/max: Capital available range
        - date_from/to: Created date range
        - search: Phone number search
        - sort_by: created_at, lead_score, capital_available
        - sort_order: asc, desc
        """
        # Base query
        query = select(InvestorProfile)

        # Apply filters
        if stage:
            query = query.where(InvestorProfile.stage == stage)
        if score_min is not None:
            query = query.where(InvestorProfile.lead_score >= score_min)
        if score_max is not None:
            query = query.where(InvestorProfile.lead_score <= score_max)
        if capital_min is not None:
            query = query.where(InvestorProfile.capital_available >= capital_min)
        if capital_max is not None:
            query = query.where(InvestorProfile.capital_available <= capital_max)
        if date_from:
            query = query.where(InvestorProfile.created_at >= date_from)
        if date_to:
            query = query.where(InvestorProfile.created_at <= date_to)
        if search:
            query = query.where(InvestorProfile.phone.contains(search))

        # Count total before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Sorting
        sort_column_map = {
            "created_at": InvestorProfile.created_at,
            "lead_score": InvestorProfile.lead_score,
            "capital_available": InvestorProfile.capital_available,
        }
        sort_column = sort_column_map.get(sort_by, InvestorProfile.created_at)

        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Pagination
        query = query.offset(skip).limit(limit)

        # Execute
        result = await self.session.execute(query)
        leads = result.scalars().all()

        return leads, total

    async def update_stage(
        self,
        investor_id: uuid.UUID,
        new_stage: str,
        changed_by: str = "admin",
        notes: Optional[str] = None,
    ) -> Optional[InvestorProfile]:
        """
        Update investor stage and record history.
        Returns the updated investor or None if not found.
        """
        investor = await self.get(investor_id)
        if not investor:
            return None

        old_stage = investor.stage
        investor.stage = new_stage

        # Record stage change history
        stage_change = StageHistory(
            investor_id=investor_id,
            from_stage=old_stage,
            to_stage=new_stage,
            changed_by=changed_by,
            notes=notes,
        )
        self.session.add(stage_change)

        await self.session.flush()
        await self.session.refresh(investor)

        return investor

    async def add_note(
        self,
        investor_id: uuid.UUID,
        content: str,
        created_by: str = "admin",
    ) -> Optional[LeadNote]:
        """Add a note to an investor."""
        investor = await self.get(investor_id)
        if not investor:
            return None

        note = LeadNote(
            investor_id=investor_id,
            content=content,
            created_by=created_by,
        )
        self.session.add(note)
        await self.session.flush()
        await self.session.refresh(note)

        return note

    async def add_consent(
        self,
        investor_id: uuid.UUID,
        consent_text: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Consent:
        """Add a consent record for an investor."""
        consent = Consent(
            investor_id=investor_id,
            consent_text=consent_text,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(consent)
        await self.session.flush()
        await self.session.refresh(consent)

        return consent
