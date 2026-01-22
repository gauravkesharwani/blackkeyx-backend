"""
Document extraction service using OpenAI Responses API.

Uses OpenAI Responses API with native PDF support for extracting
structured investment data from investor brief documents.
"""

import base64
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.schemas.extraction import InvestorBriefExtraction
from app.schemas.property import DealMemoExtraction

logger = logging.getLogger(__name__)
settings = get_settings()

# Enhanced extraction prompt for investor briefs
EXTRACTION_PROMPT = """You are an expert at extracting structured data from real estate investment memorandums and investor briefs.

Your task is to extract ALL available information from the document into a structured format. Be thorough and precise.

## Extraction Guidelines

1. **Deal Information**: Extract the deal name, property type, structure, and hold period.

2. **Narratives**: Extract the executive summary, investment thesis, and value-add strategy verbatim or as close to the original as possible.

3. **Financial Details**:
   - Total capitalization and equity required
   - Minimum investment amount
   - Target returns (IRR, equity multiple, cash-on-cash, preferred return)
   - Cap rates (going-in and exit)

4. **Financing**: Extract loan amount, LTV, interest rate, term, amortization, lender name, and loan type.

5. **Property Details**: Address, city, state, zip, square footage, year built, year renovated, parking.

6. **Tenants**: For each major tenant, extract name, square feet, annual rent, lease expiration, and tenant type.

7. **Market Analysis**: Market name, submarket, population growth, employment drivers, vacancy rate, rent growth, and comparable sales.

8. **Sponsor Information**: Sponsor name and track record.

9. **Risk Factors**: List ALL identified risk factors mentioned in the document. Look for sections labeled "Risks", "Risk Factors", "Investment Risks", or similar. Include market risks, operational risks, financial risks, tenant risks, etc.

10. **Ideal Investor Profile**: Extract the description of ideal/target investors. Look for sections about "Investor Profile", "Target Investors", "Suitable Investors", or descriptions of who the investment is designed for (e.g., accredited investors, institutional investors, high-net-worth individuals seeking cash flow, etc.).

11. **Annual Projections**: If available, extract year-by-year financial projections.

## Important Notes

- Use null for fields that are not found in the document
- For percentages, extract as decimal values (e.g., 15% → 15.0)
- For currency amounts, extract as raw numbers without formatting
- Provide a confidence score (0-1) based on extraction quality
- Add extraction_notes for any uncertainties or issues encountered
- IMPORTANT: Always populate risk_factors list - most investor briefs contain risk disclosures
- IMPORTANT: Always look for and extract ideal_investor_profile - this describes the target investor audience

Be precise and extract actual values from the document. Do not fabricate or estimate data."""

# Simple extraction prompt for backward compatibility
SIMPLE_EXTRACTION_PROMPT = """You are an expert at extracting structured data from real estate investment memorandums.

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
    """Service for extracting deal data from documents using OpenAI Responses API."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def extract_from_pdf_url(
        self, pdf_url: str
    ) -> InvestorBriefExtraction:
        """
        Extract investor brief data from a PDF via presigned URL.

        Uses OpenAI Responses API with native PDF support for direct
        document processing without manual text extraction.

        Args:
            pdf_url: Presigned S3 URL to the PDF document

        Returns:
            InvestorBriefExtraction with all extracted data
        """
        try:
            logger.info(f"Extracting from PDF URL: {pdf_url[:50]}...")

            response = await self.client.responses.parse(
                model="gpt-4o",
                input=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Extract all investment data from this investor brief PDF.",
                            },
                            {"type": "input_file", "file_url": pdf_url},
                        ],
                    },
                ],
                text_format=InvestorBriefExtraction,
            )

            result = response.output_parsed
            logger.info(
                f"Extraction complete: {result.deal_name} "
                f"(confidence: {result.confidence_score})"
            )
            return result

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            # Return a minimal extraction on error
            return InvestorBriefExtraction(
                deal_name="Untitled Deal",
                property_type="unknown",
                executive_summary="Extraction failed. Please review manually.",
                investment_thesis=None,
                value_add_strategy=None,
                total_capitalization=None,
                equity_required=None,
                minimum_investment=None,
                hold_period_years=None,
                risk_factors=["Extraction error - manual review needed"],
                ideal_investor_profile=None,
                sponsor_name=None,
                sponsor_track_record=None,
                property_details=None,
                investment_metrics=None,
                financing=None,
                major_tenants=[],
                market_analysis=None,
                annual_projections=[],
                confidence_score=0.0,
                extraction_notes=f"Extraction failed: {str(e)}",
            )

    async def extract_from_text(
        self, document_text: str
    ) -> DealMemoExtraction:
        """
        Extract deal memo data from document text using OpenAI.

        Uses structured outputs for guaranteed JSON schema compliance.
        This is the legacy method for backward compatibility.

        Args:
            document_text: Plain text content of the document

        Returns:
            DealMemoExtraction with basic extracted fields
        """
        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SIMPLE_EXTRACTION_PROMPT},
                    {"role": "user", "content": document_text},
                ],
                response_format=DealMemoExtraction,
            )

            return completion.choices[0].message.parsed

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
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

    async def extract_from_pdf_bytes(
        self, pdf_content: bytes, filename: str = "document.pdf"
    ) -> InvestorBriefExtraction:
        """
        Extract investor brief data from PDF bytes using base64 encoding.

        Uses OpenAI Responses API with base64-encoded PDF data for direct
        document processing without requiring external URL access.

        Args:
            pdf_content: Raw PDF bytes
            filename: Original filename for context

        Returns:
            InvestorBriefExtraction with all extracted data
        """
        try:
            # Encode PDF as base64 with data URL prefix
            base64_string = base64.b64encode(pdf_content).decode("utf-8")
            file_data = f"data:application/pdf;base64,{base64_string}"

            logger.info(f"Extracting from PDF bytes: {filename} ({len(pdf_content)} bytes)")

            response = await self.client.responses.parse(
                model="gpt-5.2",
                input=[
                    {"role": "system", "content": EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": "Extract all investment data from this investor brief PDF.",
                            },
                            {
                                "type": "input_file",
                                "filename": filename,
                                "file_data": file_data,
                            },
                        ],
                    },
                ],
                text_format=InvestorBriefExtraction,
            )

            result = response.output_parsed
            logger.info(
                f"Extraction complete: {result.deal_name} "
                f"(confidence: {result.confidence_score})"
            )
            return result

        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            # Return a minimal extraction on error
            return InvestorBriefExtraction(
                deal_name="Untitled Deal",
                property_type="unknown",
                executive_summary=f"Extraction failed: {str(e)}",
                investment_thesis=None,
                value_add_strategy=None,
                total_capitalization=None,
                equity_required=None,
                minimum_investment=None,
                hold_period_years=None,
                risk_factors=["Extraction error - manual review needed"],
                ideal_investor_profile=None,
                sponsor_name=None,
                sponsor_track_record=None,
                property_details=None,
                investment_metrics=None,
                financing=None,
                major_tenants=[],
                market_analysis=None,
                annual_projections=[],
                confidence_score=0.0,
                extraction_notes=f"Extraction failed: {str(e)}",
            )

    def convert_to_deal_memo(
        self, extraction: InvestorBriefExtraction
    ) -> DealMemoExtraction:
        """
        Convert enhanced extraction to legacy DealMemoExtraction format.

        Args:
            extraction: Full investor brief extraction

        Returns:
            DealMemoExtraction for backward compatibility
        """
        # Build target return string from available metrics
        target_return_parts = []
        if extraction.investment_metrics:
            metrics = extraction.investment_metrics
            # IRR
            if metrics.target_irr_min and metrics.target_irr_max:
                target_return_parts.append(f"{metrics.target_irr_min}-{metrics.target_irr_max}% IRR")
            elif metrics.target_irr_min:
                target_return_parts.append(f"{metrics.target_irr_min}% IRR")
            elif metrics.target_irr_max:
                target_return_parts.append(f"{metrics.target_irr_max}% IRR")
            # Equity Multiple
            if metrics.target_equity_multiple:
                target_return_parts.append(f"{metrics.target_equity_multiple}x Equity Multiple")
            # Cash-on-Cash
            if metrics.target_cash_on_cash:
                target_return_parts.append(f"{metrics.target_cash_on_cash}% CoC")
            # Preferred Return
            if metrics.preferred_return:
                target_return_parts.append(f"{metrics.preferred_return}% Pref")

        target_return = ", ".join(target_return_parts) if target_return_parts else "TBD"

        return DealMemoExtraction(
            name=extraction.deal_name,
            dealType=extraction.property_type,
            summary=extraction.executive_summary or "",
            thesis=extraction.investment_thesis or "",
            minimumInvestment=extraction.minimum_investment or 0,
            targetReturn=target_return,
            riskFactors=extraction.risk_factors,
            idealInvestorProfile=extraction.ideal_investor_profile or "",
            structure=extraction.deal_structure or "LP/GP",
            timeline=extraction.hold_period_years or "5-7 years",
            confidence=extraction.confidence_score,
            rawText=f"[Extracted from PDF - Confidence: {extraction.confidence_score}]",
        )


# Singleton instance
_extraction_service: Optional[ExtractionService] = None


def get_extraction_service() -> ExtractionService:
    """Get or create extraction service singleton."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
