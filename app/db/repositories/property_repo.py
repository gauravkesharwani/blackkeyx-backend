"""Property/Deal repository."""

import uuid
from typing import Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.property import Property, PropertyFeature


class PropertyRepository(BaseRepository[Property]):
    """Repository for property/deal operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Property, session)

    async def get_with_features(self, id: uuid.UUID) -> Optional[Property]:
        """Get property with features loaded."""
        result = await self.session.execute(
            select(Property)
            .options(selectinload(Property.features))
            .where(Property.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> Sequence[Property]:
        """Get all properties with a specific status."""
        result = await self.session.execute(
            select(Property)
            .where(Property.status == status)
            .order_by(Property.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_deals(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[Sequence[Property], int]:
        """Get all active deals with total count."""
        # Count total active
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Property)
            .where(Property.status == "active")
        )
        total = count_result.scalar_one()

        # Get deals
        result = await self.session.execute(
            select(Property)
            .where(Property.status == "active")
            .order_by(Property.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        deals = result.scalars().all()

        return deals, total

    async def search_deals(
        self,
        status: Optional[str] = None,
        deal_type: Optional[str] = None,
        min_investment_max: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[Sequence[Property], int]:
        """
        Search deals with filters.
        Returns (deals, total_count).
        """
        query = select(Property)

        if status:
            query = query.where(Property.status == status)
        if deal_type:
            query = query.where(Property.deal_type == deal_type)
        if min_investment_max is not None:
            query = query.where(Property.minimum_investment <= min_investment_max)
        if search:
            query = query.where(
                Property.name.ilike(f"%{search}%")
                | Property.summary.ilike(f"%{search}%")
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Order and paginate
        query = query.order_by(Property.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        deals = result.scalars().all()

        return deals, total

    async def create_with_features(
        self,
        property_data: dict,
        features_data: Optional[dict] = None,
    ) -> Property:
        """Create a property with optional features."""
        property_obj = Property(**property_data)
        self.session.add(property_obj)
        await self.session.flush()

        if features_data:
            features = PropertyFeature(
                property_id=property_obj.id,
                **features_data,
            )
            self.session.add(features)
            await self.session.flush()

        await self.session.refresh(property_obj)
        return property_obj

    async def update_status(
        self, id: uuid.UUID, status: str
    ) -> Optional[Property]:
        """Update property status."""
        property_obj = await self.get(id)
        if not property_obj:
            return None

        property_obj.status = status
        await self.session.flush()
        await self.session.refresh(property_obj)

        return property_obj
