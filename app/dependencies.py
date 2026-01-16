"""FastAPI dependency injection for repositories and services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.investor_repo import InvestorRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.session import get_db


async def get_investor_repo(
    session: AsyncSession = Depends(get_db),
) -> InvestorRepository:
    """Get InvestorRepository instance."""
    return InvestorRepository(session)


async def get_property_repo(
    session: AsyncSession = Depends(get_db),
) -> PropertyRepository:
    """Get PropertyRepository instance."""
    return PropertyRepository(session)
