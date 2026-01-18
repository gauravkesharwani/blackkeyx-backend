"""FastAPI dependency injection for repositories and services."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.investor_repo import InvestorRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.session import get_db
from app.services.admin_service import AdminService
from app.services.lead_service import LeadService
from app.services.property_service import PropertyService
from app.services.voice_service import VoiceService


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


async def get_voice_service(
    session: AsyncSession = Depends(get_db),
) -> VoiceService:
    """Get VoiceService instance."""
    return VoiceService(session)


async def get_admin_service(
    session: AsyncSession = Depends(get_db),
) -> AdminService:
    """Get AdminService instance."""
    return AdminService(session)


async def get_lead_service(
    session: AsyncSession = Depends(get_db),
) -> LeadService:
    """Get LeadService instance."""
    return LeadService(session)


async def get_property_service(
    session: AsyncSession = Depends(get_db),
) -> PropertyService:
    """Get PropertyService instance."""
    return PropertyService(session)
