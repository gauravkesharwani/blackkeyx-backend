"""Property service for deal management operations."""

import logging
import uuid
from typing import Optional, Sequence, Tuple

import boto3
from botocore.exceptions import ClientError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.repositories.property_repo import PropertyRepository
from app.models.property import Deal, Property
from app.schemas.extraction import InvestorBriefExtraction
from app.services.extraction_service import get_extraction_service
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)
settings = get_settings()


class PropertyService:
    """Service for property/deal operations."""

    ALLOWED_CONTENT_TYPES = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB

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
        self,
        status: Optional[str] = None,
        deal_type: Optional[str] = None,
        min_investment_max: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[Sequence[Property], int]:
        """List deals with optional filters and pagination."""
        return await self.property_repo.search_deals(
            status=status,
            deal_type=deal_type,
            min_investment_max=min_investment_max,
            search=search,
            skip=skip,
            limit=limit,
        )

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
        """Create a new deal with basic fields only (legacy method)."""
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
        try:
            return await self.property_repo.create(property_obj)
        except Exception as e:
            logger.error(f"Failed to save deal '{name}' to database: {e}", exc_info=True)
            raise

    async def create_deal_from_extraction(
        self,
        extraction: InvestorBriefExtraction,
        document_s3_key: Optional[str] = None,
        document_filename: Optional[str] = None,
        generate_embeddings: bool = True,
        deal_type: Optional[str] = None,
    ) -> Property:
        """
        Create a new deal with all related data from extraction.

        This method saves:
        - Property (main record)
        - InvestmentMetrics (if available)
        - Financing (if available)
        - Tenants (if available)
        - AnnualProjections (if available)
        - MarketAnalysis (if available)
        - PropertyDocument (if document info provided)
        - PropertyEmbeddings (if generate_embeddings=True)

        Args:
            extraction: The full extraction data from PDF
            document_s3_key: S3 key of the uploaded document
            document_filename: Original filename
            generate_embeddings: Whether to generate embeddings for semantic search

        Returns:
            Created Property with all related data
        """
        # Create property with all related data
        try:
            property_obj = await self.property_repo.create_with_extraction(
                extraction=extraction,
                document_s3_key=document_s3_key,
                document_filename=document_filename,
                deal_type=deal_type,
            )
        except Exception as e:
            logger.error(
                f"Failed to save deal '{extraction.deal_name}' with extraction data to database: {e}",
                exc_info=True,
            )
            raise

        # Generate embeddings for semantic search
        if generate_embeddings:
            try:
                embedding_service = EmbeddingService(self.session)
                await embedding_service.create_property_embeddings(
                    property_id=property_obj.id,
                    extraction=extraction,
                )
                logger.info(f"Generated embeddings for property {property_obj.id}")
            except Exception as e:
                # Log but don't fail the deal creation if embeddings fail
                logger.error(f"Failed to generate embeddings for property {property_obj.id}: {e}")

        return property_obj

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

    async def delete_deal(self, deal_id: uuid.UUID) -> bool:
        """
        Delete a deal by ID, including its S3 document.

        Returns True if deleted, False if not found.
        """
        # First, get the deal to retrieve the S3 key
        deal = await self.property_repo.get(deal_id)
        if not deal:
            return False

        s3_key = deal.document_s3_key

        # Delete from database (cascades to all related tables)
        deleted = await self.property_repo.delete(deal_id)

        # Delete document from S3 if it exists
        if deleted and s3_key:
            try:
                self.s3_client.delete_object(
                    Bucket=settings.aws_s3_bucket,
                    Key=s3_key,
                )
                logger.info(f"Deleted S3 document: {s3_key}")
            except ClientError as e:
                # Log but don't fail - the DB record is already deleted
                logger.warning(f"Failed to delete S3 document {s3_key}: {e}")

        return deleted

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

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for accessing an S3 object.

        Args:
            s3_key: The S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

    async def get_document_url(self, deal_id: uuid.UUID) -> Optional[str]:
        """
        Get a presigned URL for a deal's document.

        Args:
            deal_id: The deal/property UUID

        Returns:
            Presigned URL or None if no document exists
        """
        deal = await self.property_repo.get(deal_id)
        if not deal or not deal.document_s3_key:
            return None

        return self.generate_presigned_url(deal.document_s3_key)

    async def extract_document(self, upload_id: str, deal_type: str = "industrial") -> dict:
        """
        Extract deal data from document using AI.

        Downloads the PDF from S3 and uses OpenAI Responses API with base64-encoded
        data for reliable extraction without URL access issues.

        Args:
            upload_id: The upload ID returned from upload_document

        Returns:
            Dictionary with extracted deal data matching DealMemoExtraction schema

        Raises:
            ValueError: If no document found for upload_id
            ClientError: If S3 operations fail
        """
        # Find the uploaded file in S3
        s3_prefix = f"uploads/{upload_id}/"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=settings.aws_s3_bucket,
                Prefix=s3_prefix,
                MaxKeys=1,
            )
        except ClientError as e:
            logger.error(f"Failed to list S3 objects for upload {upload_id}: {e}")
            raise

        contents = response.get("Contents", [])
        if not contents:
            raise ValueError(f"No document found for upload_id: {upload_id}")

        s3_key = contents[0]["Key"]
        filename = s3_key.split("/")[-1]  # Extract filename from key
        logger.info(f"Found document at S3 key: {s3_key}")

        # Download the PDF content from S3
        try:
            s3_response = self.s3_client.get_object(
                Bucket=settings.aws_s3_bucket,
                Key=s3_key,
            )
            pdf_content = s3_response["Body"].read()
            logger.info(f"Downloaded {len(pdf_content)} bytes from S3")
        except ClientError as e:
            logger.error(f"Failed to download document from S3: {e}")
            raise

        # Extract data using the extraction service with base64-encoded PDF
        extraction_service = get_extraction_service()
        extraction = await extraction_service.extract_from_pdf_bytes(pdf_content, filename, deal_type=deal_type)

        # Convert to legacy DealMemoExtraction format for API response
        deal_memo = extraction_service.convert_to_deal_memo(extraction)

        return {
            "name": deal_memo.name,
            "deal_type": deal_memo.dealType,
            "summary": deal_memo.summary,
            "thesis": deal_memo.thesis,
            "minimum_investment": deal_memo.minimumInvestment,
            "target_return": deal_memo.targetReturn,
            "risk_factors": deal_memo.riskFactors,
            "ideal_investor_profile": deal_memo.idealInvestorProfile,
            "structure": deal_memo.structure,
            "timeline": deal_memo.timeline,
            "confidence": deal_memo.confidence,
            "raw_text": deal_memo.rawText,
        }

    async def extract_document_full(self, upload_id: str, deal_type: str = "industrial") -> InvestorBriefExtraction:
        """
        Extract FULL deal data from document using AI.

        Returns the complete InvestorBriefExtraction object with all data:
        - Investment metrics (IRR, cap rates, equity multiples)
        - Financing details (loan amount, LTV, interest rate)
        - Major tenants (rent roll data)
        - Annual projections (year-by-year financials)
        - Market analysis (market data, vacancy, rent growth)
        - Property details (address, square footage)
        - Sponsor information

        Args:
            upload_id: The upload ID returned from upload_document

        Returns:
            Full InvestorBriefExtraction object

        Raises:
            ValueError: If no document found for upload_id
            ClientError: If S3 operations fail
        """
        # Find the uploaded file in S3
        s3_prefix = f"uploads/{upload_id}/"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=settings.aws_s3_bucket,
                Prefix=s3_prefix,
                MaxKeys=1,
            )
        except ClientError as e:
            logger.error(f"Failed to list S3 objects for upload {upload_id}: {e}")
            raise

        contents = response.get("Contents", [])
        if not contents:
            raise ValueError(f"No document found for upload_id: {upload_id}")

        s3_key = contents[0]["Key"]
        filename = s3_key.split("/")[-1]
        logger.info(f"Found document at S3 key: {s3_key}")

        # Download the PDF content from S3
        try:
            s3_response = self.s3_client.get_object(
                Bucket=settings.aws_s3_bucket,
                Key=s3_key,
            )
            pdf_content = s3_response["Body"].read()
            logger.info(f"Downloaded {len(pdf_content)} bytes from S3")
        except ClientError as e:
            logger.error(f"Failed to download document from S3: {e}")
            raise

        # Extract data using the extraction service
        extraction_service = get_extraction_service()
        extraction = await extraction_service.extract_from_pdf_bytes(
            pdf_content, filename, deal_type=deal_type
        )

        logger.info(
            f"Full extraction complete for {filename}: "
            f"{extraction.deal_name} (confidence: {extraction.confidence_score})"
        )

        return extraction

    async def extract_and_create_deal(
        self, upload_id: str, deal_type: str = "industrial",
        generate_embeddings: bool = True,
    ) -> Property:
        """
        Extract deal data from document and create the deal with all related data.

        This is the recommended method for creating deals as it:
        1. Extracts all data from the PDF
        2. Creates the Property with all related tables populated
        3. Generates embeddings for semantic search

        Args:
            upload_id: The upload ID returned from upload_document
            generate_embeddings: Whether to generate embeddings (default True)

        Returns:
            Created Property with all related data

        Raises:
            ValueError: If no document found for upload_id
            ClientError: If S3 operations fail
        """
        # Find the uploaded file in S3
        s3_prefix = f"uploads/{upload_id}/"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=settings.aws_s3_bucket,
                Prefix=s3_prefix,
                MaxKeys=1,
            )
        except ClientError as e:
            logger.error(f"Failed to list S3 objects for upload {upload_id}: {e}")
            raise

        contents = response.get("Contents", [])
        if not contents:
            raise ValueError(f"No document found for upload_id: {upload_id}")

        s3_key = contents[0]["Key"]
        filename = s3_key.split("/")[-1]
        file_size = contents[0].get("Size", 0)
        logger.info(f"Found document at S3 key: {s3_key}")

        # Download the PDF content from S3
        try:
            s3_response = self.s3_client.get_object(
                Bucket=settings.aws_s3_bucket,
                Key=s3_key,
            )
            pdf_content = s3_response["Body"].read()
            content_type = s3_response.get("ContentType", "application/pdf")
            logger.info(f"Downloaded {len(pdf_content)} bytes from S3")
        except ClientError as e:
            logger.error(f"Failed to download document from S3: {e}")
            raise

        # Extract data using the extraction service
        extraction_service = get_extraction_service()
        extraction = await extraction_service.extract_from_pdf_bytes(pdf_content, filename, deal_type=deal_type)

        # Move document to permanent location
        permanent_s3_key = f"deals/{uuid.uuid4()}/{filename}"
        try:
            # Copy to permanent location
            self.s3_client.copy_object(
                Bucket=settings.aws_s3_bucket,
                CopySource={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
                Key=permanent_s3_key,
            )
            logger.info(f"Copied document to permanent location: {permanent_s3_key}")
        except ClientError as e:
            logger.warning(f"Failed to copy document to permanent location: {e}")
            permanent_s3_key = s3_key  # Fall back to original location

        # Create the deal with all related data
        property_obj = await self.create_deal_from_extraction(
            extraction=extraction,
            document_s3_key=permanent_s3_key,
            document_filename=filename,
            generate_embeddings=generate_embeddings,
            deal_type=deal_type,
        )

        logger.info(
            f"Created deal '{property_obj.name}' (ID: {property_obj.id}) "
            f"with all related data from extraction"
        )

        return property_obj

    async def semantic_search(
        self,
        query: str,
        limit: int = 20,
        min_similarity: float = 0.3,
        status: Optional[str] = None,
    ) -> list[tuple[Property, float]]:
        """
        Search for deals using natural language query and semantic similarity.

        This method uses OpenAI embeddings and pgvector to find deals
        that semantically match the query text.

        Args:
            query: Natural language search query
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            status: Optional status filter

        Returns:
            List of (Property, similarity_score) tuples
        """
        embedding_service = EmbeddingService(self.session)

        # Get property IDs with similarity scores
        property_scores = await embedding_service.search_properties_by_query(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            status=status,
        )

        if not property_scores:
            return []

        # Fetch full Property objects
        results = []
        for property_id, similarity in property_scores:
            property_obj = await self.property_repo.get(property_id)
            if property_obj:
                results.append((property_obj, similarity))

        return results
