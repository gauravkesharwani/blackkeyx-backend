"""
Document extraction service.

Uses OpenAI structured outputs to extract deal data from PDFs.
"""

from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.property import DealMemoExtraction

settings = get_settings()

# Extraction prompt for OpenAI
EXTRACTION_PROMPT = """You are an expert at extracting structured data from real estate investment memorandums.

Extract the following information from the document:
1. Deal/Property Name
2. Deal Type (multifamily, industrial, office, retail, etc.)
3. Executive Summary
4. Investment Thesis
5. Minimum Investment Amount
6. Target Return (IRR or CoC)
7. Key Risk Factors (list)
8. Ideal Investor Profile
9. Deal Structure (LP/GP, REIT, etc.)
10. Investment Timeline/Hold Period

Be precise and extract actual values from the document. If a field is not found, use reasonable defaults based on the deal type.

Return confidence score (0-1) based on how much information was clearly extractable."""


class ExtractionService:
    """Service for extracting deal data from documents."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_from_text(
        self, document_text: str
    ) -> DealMemoExtraction:
        """
        Extract deal memo data from document text using OpenAI.

        Uses structured outputs for guaranteed JSON schema compliance.
        """
        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": document_text},
                ],
                response_format=DealMemoExtraction,
            )

            return completion.choices[0].message.parsed

        except Exception as e:
            # Return a default extraction on error
            return DealMemoExtraction(
                name="Untitled Deal",
                dealType="unknown",
                summary="Extraction failed. Please review manually.",
                thesis="",
                minimumInvestment=100000,
                targetReturn="TBD",
                riskFactors=["Extraction error - manual review needed"],
                idealInvestorProfile="Accredited investors",
                structure="LP/GP",
                timeline="5-7 years",
                confidence=0.0,
                rawText=document_text[:1000] if document_text else "",
            )

    async def extract_from_pdf(
        self, pdf_content: bytes
    ) -> DealMemoExtraction:
        """
        Extract deal memo data from PDF bytes.

        TODO: Implement PDF parsing with PyPDF2 or similar.
        """
        # Placeholder - would use pdf-parse or similar to extract text
        # Then call extract_from_text
        mock_text = "[PDF content would be extracted here]"
        return await self.extract_from_text(mock_text)


# Singleton instance
_extraction_service: Optional[ExtractionService] = None


def get_extraction_service() -> ExtractionService:
    """Get or create extraction service singleton."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
