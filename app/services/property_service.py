"""Property service for deal management operations."""

import logging
import uuid
from typing import Optional, Sequence, Tuple

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repositories.property_repo import PropertyRepository
from app.models.property import Property

logger = logging.getLogger(__name__)
settings = get_settings()


class PropertyService:
    """Service for property/deal operations."""

    ALLOWED_CONTENT_TYPES = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, session: AsyncSession):
        self.session = session
        self.property_repo = PropertyRepository(session)
        self._s3_client = None

    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
        return self._s3_client

    async def list_deals(
        self, status: Optional[str] = None
    ) -> Tuple[Sequence[Property], int]:
        """List deals with optional status filter."""
        if status:
            deals = await self.property_repo.get_by_status(status)
            return deals, len(deals)
        return await self.property_repo.get_active_deals()

    async def get_deal(self, deal_id: uuid.UUID) -> Optional[Property]:
        """Get deal by ID."""
        return await self.property_repo.get(deal_id)

    async def create_deal(
        self,
        name: str,
        deal_type: Optional[str] = None,
        summary: Optional[str] = None,
        thesis: Optional[str] = None,
        minimum_investment: Optional[int] = None,
        target_return: Optional[str] = None,
        risk_factors: Optional[list] = None,
        ideal_investor_profile: Optional[str] = None,
        structure: Optional[str] = None,
        timeline: Optional[str] = None,
    ) -> Property:
        """Create a new deal."""
        property_obj = Property(
            id=uuid.uuid4(),
            name=name,
            deal_type=deal_type,
            summary=summary,
            thesis=thesis,
            minimum_investment=minimum_investment,
            target_return=target_return,
            risk_factors=risk_factors or [],
            ideal_investor_profile=ideal_investor_profile,
            structure=structure,
            timeline=timeline,
            status="active",
        )
        return await self.property_repo.create(property_obj)

    async def update_deal(
        self,
        deal_id: uuid.UUID,
        name: Optional[str] = None,
        deal_type: Optional[str] = None,
        summary: Optional[str] = None,
        thesis: Optional[str] = None,
        minimum_investment: Optional[int] = None,
        target_return: Optional[str] = None,
        risk_factors: Optional[list] = None,
        ideal_investor_profile: Optional[str] = None,
        structure: Optional[str] = None,
        timeline: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[Property]:
        """Update an existing deal."""
        deal = await self.property_repo.get(deal_id)
        if not deal:
            return None

        # Update fields if provided
        if name is not None:
            deal.name = name
        if deal_type is not None:
            deal.deal_type = deal_type
        if summary is not None:
            deal.summary = summary
        if thesis is not None:
            deal.thesis = thesis
        if minimum_investment is not None:
            deal.minimum_investment = minimum_investment
        if target_return is not None:
            deal.target_return = target_return
        if risk_factors is not None:
            deal.risk_factors = risk_factors
        if ideal_investor_profile is not None:
            deal.ideal_investor_profile = ideal_investor_profile
        if structure is not None:
            deal.structure = structure
        if timeline is not None:
            deal.timeline = timeline
        if status is not None:
            deal.status = status

        return await self.property_repo.update(deal)

    def validate_file(self, content_type: str, size: int) -> Optional[str]:
        """Validate file type and size. Returns error message or None."""
        if content_type not in self.ALLOWED_CONTENT_TYPES:
            return "Invalid file type. Allowed: PDF, DOCX"
        if size > self.MAX_FILE_SIZE:
            return f"File too large. Max size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
        return None

    async def upload_document(
        self, filename: str, content: bytes, content_type: str
    ) -> str:
        """Upload document to S3. Returns upload_id."""
        upload_id = str(uuid.uuid4())
        s3_key = f"uploads/{upload_id}/{filename}"

        try:
            self.s3_client.put_object(
                Bucket=settings.aws_s3_bucket,
                Key=s3_key,
                Body=content,
                ContentType=content_type,
            )
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

        return upload_id

    async def extract_document(self, upload_id: str) -> dict:
        """
        Extract deal data from document using AI.

        TODO: Implement actual PDF parsing and OpenAI extraction.
        Currently returns mock data.
        """
        return {
            "name": "Sample Deal",
            "deal_type": "multifamily",
            "summary": "This is a sample deal extracted from the document.",
            "thesis": "Strong fundamentals with value-add opportunity.",
            "minimum_investment": 100000,
            "target_return": "15-18% IRR",
            "risk_factors": ["Market risk", "Interest rate risk", "Occupancy risk"],
            "ideal_investor_profile": "Accredited investors seeking stable cash flow",
            "structure": "LP/GP",
            "timeline": "5-7 years",
            "confidence": 0.85,
            "raw_text": "[Document text would be extracted here]",
        }
