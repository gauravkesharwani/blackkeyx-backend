"""
Embedding service for semantic search using OpenAI embeddings and pgvector.

This service handles:
- Generating embeddings from text using OpenAI text-embedding-3-small
- Chunking documents by section type
- Storing and retrieving embeddings from PostgreSQL with pgvector
- Similarity search for matching investors to deals
"""

import logging
import uuid
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.embeddings import InvestorEmbedding, PropertyEmbedding
from app.schemas.extraction import InvestorBriefExtraction

if TYPE_CHECKING:
    from app.models.investor import InvestorPreferences, InvestorProfile

logger = logging.getLogger(__name__)
settings = get_settings()

# Embedding model configuration
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

# Section types for property embeddings
PROPERTY_SECTION_TYPES = [
    "executive_summary",
    "investment_thesis",
    "value_add_strategy",
    "market_analysis",
    "risk_factors",
    "tenant_info",
    "financials",
    "property_overview",
    "investment_terms",
    "sponsor_profile",
    "deal_structure",
    "cash_flow_projection",
]

# Section types for investor embeddings
INVESTOR_SECTION_TYPES = [
    "investment_thesis",
    "investment_criteria",
    "return_profile",
    "specific_concerns",
    "call_insights",
    "full_profile",
]


class EmbeddingService:
    """Service for generating and managing vector embeddings."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        # Truncate very long texts (model has ~8k token limit)
        max_chars = 30000  # Approximate safe limit
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Truncated text to {max_chars} characters for embedding")

        try:
            response = await self.client.embeddings.create(
                input=text,
                model=EMBEDDING_MODEL,
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def extract_sections_from_extraction(
        self, extraction: InvestorBriefExtraction
    ) -> Dict[str, str]:
        """
        Extract text sections from an investor brief extraction for embedding.

        Args:
            extraction: Parsed investor brief data

        Returns:
            Dictionary mapping section type to text content
        """
        sections = {}

        # Executive summary
        if extraction.executive_summary:
            sections["executive_summary"] = extraction.executive_summary

        # Investment thesis
        if extraction.investment_thesis:
            sections["investment_thesis"] = extraction.investment_thesis

        # Value add strategy
        if extraction.value_add_strategy:
            sections["value_add_strategy"] = extraction.value_add_strategy

        # Market analysis (concatenate all market fields)
        if extraction.market_analysis:
            market = extraction.market_analysis
            market_parts = []
            if market.market_name:
                market_parts.append(f"Market: {market.market_name}")
            if market.submarket:
                market_parts.append(f"Submarket: {market.submarket}")
            if market.population_growth:
                market_parts.append(f"Population Growth: {market.population_growth}")
            if market.employment_drivers:
                market_parts.append(
                    f"Employment Drivers: {', '.join(market.employment_drivers)}"
                )
            if market.market_rent_growth:
                market_parts.append(f"Rent Growth: {market.market_rent_growth}")
            if market.comparable_sales:
                market_parts.append(f"Comparable Sales: {market.comparable_sales}")
            if market.market_vacancy_rate:
                market_parts.append(f"Vacancy Rate: {market.market_vacancy_rate}%")
            if market.new_construction_pct:
                market_parts.append(f"New Construction: {market.new_construction_pct}% of inventory")
            if market.absorption_rate:
                market_parts.append(f"Absorption Rate: {market.absorption_rate}")
            if market.landlord_pricing_power:
                market_parts.append(f"Landlord Pricing Power: {market.landlord_pricing_power}")
            if market_parts:
                sections["market_analysis"] = "\n".join(market_parts)

        # Risk factors
        if extraction.risk_factors:
            sections["risk_factors"] = "\n".join(extraction.risk_factors)

        # Tenant info (concatenate tenant details)
        if extraction.major_tenants:
            tenant_parts = []
            for tenant in extraction.major_tenants:
                parts = [f"Tenant: {tenant.tenant_name}"]
                if tenant.square_feet:
                    parts.append(f"SF: {tenant.square_feet:,}")
                if tenant.annual_rent:
                    parts.append(f"Rent: ${tenant.annual_rent:,.0f}")
                if tenant.lease_expiration:
                    parts.append(f"Expires: {tenant.lease_expiration}")
                if tenant.tenant_type:
                    parts.append(f"Type: {tenant.tenant_type}")
                tenant_parts.append(" | ".join(parts))
            if tenant_parts:
                sections["tenant_info"] = "\n".join(tenant_parts)

        # Financials (concatenate investment metrics and financing)
        financial_parts = []
        if extraction.investment_metrics:
            metrics = extraction.investment_metrics
            if metrics.target_irr_min or metrics.target_irr_max:
                irr_str = f"Target IRR: {metrics.target_irr_min or ''}-{metrics.target_irr_max or ''}%"
                financial_parts.append(irr_str)
            if metrics.target_equity_multiple:
                financial_parts.append(
                    f"Equity Multiple: {metrics.target_equity_multiple}x"
                )
            if metrics.cap_rate_going_in:
                financial_parts.append(
                    f"Going-in Cap Rate: {metrics.cap_rate_going_in}%"
                )
            if metrics.preferred_return:
                financial_parts.append(
                    f"Preferred Return: {metrics.preferred_return}%"
                )

            if metrics.cap_rate_exit:
                financial_parts.append(f"Exit Cap Rate: {metrics.cap_rate_exit}%")
            if metrics.target_cash_on_cash:
                financial_parts.append(f"Cash-on-Cash: {metrics.target_cash_on_cash}%")
            if metrics.return_from_cash_flow_pct:
                financial_parts.append(f"Return from Cash Flow: {metrics.return_from_cash_flow_pct}%")
            if metrics.return_from_sale_pct:
                financial_parts.append(f"Return from Sale: {metrics.return_from_sale_pct}%")
            if metrics.return_profile:
                financial_parts.append(f"Return Profile: {metrics.return_profile}")

        if extraction.financing:
            fin = extraction.financing
            if fin.loan_amount:
                financial_parts.append(f"Loan Amount: ${fin.loan_amount:,.0f}")
            if fin.ltv_ratio:
                financial_parts.append(f"LTV: {fin.ltv_ratio}%")
            if fin.interest_rate:
                financial_parts.append(f"Interest Rate: {fin.interest_rate}%")

        if financial_parts:
            sections["financials"] = "\n".join(financial_parts)

        # Property overview (location and physical details)
        if extraction.property_details:
            prop = extraction.property_details
            prop_parts = []
            if prop.address:
                prop_parts.append(f"Address: {prop.address}")
            if prop.city and prop.state:
                prop_parts.append(f"Location: {prop.city}, {prop.state}")
            if prop.total_square_feet:
                prop_parts.append(f"Square Feet: {prop.total_square_feet:,}")
            if prop.year_built:
                prop_parts.append(f"Year Built: {prop.year_built}")
            if prop.year_renovated:
                prop_parts.append(f"Year Renovated: {prop.year_renovated}")
            if prop.parking_spaces:
                prop_parts.append(f"Parking: {prop.parking_spaces} spaces")
            if prop_parts:
                sections["property_overview"] = "\n".join(prop_parts)

        # Investment terms
        terms_parts = []
        if extraction.deal_structure:
            terms_parts.append(f"Structure: {extraction.deal_structure}")
        if extraction.hold_period_years:
            terms_parts.append(f"Hold Period: {extraction.hold_period_years}")
        if extraction.minimum_investment:
            terms_parts.append(
                f"Minimum Investment: ${extraction.minimum_investment:,}"
            )
        if extraction.equity_required:
            terms_parts.append(f"Equity Required: ${extraction.equity_required:,.0f}")
        if extraction.ideal_investor_profile:
            terms_parts.append(f"Ideal Investor: {extraction.ideal_investor_profile}")
        if terms_parts:
            sections["investment_terms"] = "\n".join(terms_parts)

        # Sponsor profile (new)
        sponsor_parts = []
        if extraction.sponsor_name:
            sponsor_parts.append(f"Sponsor: {extraction.sponsor_name}")
        if extraction.sponsor_track_record:
            sponsor_parts.append(f"Track Record: {extraction.sponsor_track_record}")
        if sponsor_parts:
            sections["sponsor_profile"] = "\n".join(sponsor_parts)

        # Deal structure (new)
        structure_parts = []
        if extraction.waterfall_structure:
            ws = extraction.waterfall_structure
            if ws.preferred_return_pct:
                structure_parts.append(f"Preferred Return: {ws.preferred_return_pct}%")
            if ws.promote_tier_1_pct and ws.promote_tier_1_hurdle:
                structure_parts.append(f"Promote Tier 1: {ws.promote_tier_1_pct}% above {ws.promote_tier_1_hurdle}% IRR")
            if ws.promote_tier_2_pct and ws.promote_tier_2_hurdle:
                structure_parts.append(f"Promote Tier 2: {ws.promote_tier_2_pct}% above {ws.promote_tier_2_hurdle}% IRR")
            if ws.sponsor_coinvest_pct:
                structure_parts.append(f"Sponsor Co-invest: {ws.sponsor_coinvest_pct}%")
        if extraction.sponsor_fees:
            fees = extraction.sponsor_fees
            fee_items = []
            if fees.acquisition_fee_pct:
                fee_items.append(f"Acquisition: {fees.acquisition_fee_pct}%")
            if fees.asset_management_fee_pct:
                fee_items.append(f"Asset Mgmt: {fees.asset_management_fee_pct}%")
            if fees.disposition_fee_pct:
                fee_items.append(f"Disposition: {fees.disposition_fee_pct}%")
            if fee_items:
                structure_parts.append(f"Fees: {', '.join(fee_items)}")
        if structure_parts:
            sections["deal_structure"] = "\n".join(structure_parts)

        # Cash flow projection (new)
        if extraction.annual_projections:
            proj_parts = []
            for proj in extraction.annual_projections[:5]:  # First 5 years
                parts = [f"Year {proj.year}:"]
                if proj.noi:
                    parts.append(f"NOI ${proj.noi:,.0f}")
                if proj.cash_on_cash_return:
                    parts.append(f"CoC {proj.cash_on_cash_return}%")
                if proj.irr_through_year:
                    parts.append(f"IRR {proj.irr_through_year}%")
                proj_parts.append(" | ".join(parts))
            if proj_parts:
                sections["cash_flow_projection"] = "\n".join(proj_parts)

        return sections

    async def create_property_embeddings(
        self, property_id: uuid.UUID, extraction: InvestorBriefExtraction
    ) -> List[PropertyEmbedding]:
        """
        Generate and store embeddings for all sections of a property.

        Args:
            property_id: UUID of the property
            extraction: Parsed investor brief data

        Returns:
            List of created PropertyEmbedding objects
        """
        # Extract sections
        sections = self.extract_sections_from_extraction(extraction)

        if not sections:
            logger.warning(f"No text sections found for property {property_id}")
            return []

        # Delete existing embeddings for this property
        await self.session.execute(
            text(
                "DELETE FROM property_embeddings WHERE property_id = :property_id"
            ).bindparams(property_id=property_id)
        )

        # Create new embeddings
        embeddings = []
        for section_type, content in sections.items():
            try:
                embedding_vector = await self.generate_embedding(content)

                embedding = PropertyEmbedding(
                    id=uuid.uuid4(),
                    property_id=property_id,
                    section_type=section_type,
                    content=content,
                    embedding=embedding_vector,
                )
                self.session.add(embedding)
                embeddings.append(embedding)
                logger.debug(f"Created embedding for {section_type} on {property_id}")

            except Exception as e:
                logger.error(
                    f"Failed to create embedding for {section_type}: {e}"
                )
                continue

        await self.session.flush()
        logger.info(
            f"Created {len(embeddings)} embeddings for property {property_id}"
        )

        return embeddings

    async def create_investor_profile_embedding(
        self,
        investor_id: uuid.UUID,
        investor: "InvestorProfile",
        preferences: Optional["InvestorPreferences"] = None,
        call_summary: Optional[str] = None,
    ) -> List[InvestorEmbedding]:
        """
        Generate and store embeddings for an investor profile.

        Args:
            investor_id: UUID of the investor
            investor: Full InvestorProfile model
            preferences: Optional InvestorPreferences model
            call_summary: Optional call summary from extraction

        Returns:
            List of created InvestorEmbedding objects
        """
        # Delete existing embeddings for this investor
        await self.session.execute(
            text(
                "DELETE FROM investor_embeddings WHERE investor_id = :investor_id"
            ).bindparams(investor_id=investor_id)
        )

        embeddings = []
        sections = {}

        # 1. Investment thesis (narrative)
        if investor.investment_thesis:
            sections["investment_thesis"] = investor.investment_thesis

        # 2. Investment criteria (structured -> text)
        criteria_parts = []
        if preferences:
            if preferences.property_types:
                criteria_parts.append(f"Property types: {', '.join(preferences.property_types)}")
            if preferences.preferred_markets:
                criteria_parts.append(f"Preferred markets: {', '.join(preferences.preferred_markets)}")
            if preferences.excluded_markets:
                criteria_parts.append(f"Markets to avoid: {', '.join(preferences.excluded_markets)}")
            if preferences.investment_strategy:
                criteria_parts.append(f"Strategy: {preferences.investment_strategy}")
            if preferences.preferred_structures:
                criteria_parts.append(f"Structures: {', '.join(preferences.preferred_structures)}")
            if preferences.hold_period_min or preferences.hold_period_max:
                hold = f"{preferences.hold_period_min or '?'}-{preferences.hold_period_max or '?'} years"
                criteria_parts.append(f"Hold period: {hold}")
        elif investor.investment_preferences:
            criteria_parts.append(f"Property types: {', '.join(investor.investment_preferences)}")
        if criteria_parts:
            sections["investment_criteria"] = "\n".join(criteria_parts)

        # 3. Return profile (structured -> text)
        return_parts = []
        if preferences:
            if preferences.target_irr_min or preferences.target_irr_max:
                irr = f"{preferences.target_irr_min or '?'}-{preferences.target_irr_max or '?'}%"
                return_parts.append(f"Target IRR: {irr}")
            if preferences.risk_tolerance_level:
                return_parts.append(f"Risk tolerance: {preferences.risk_tolerance_level}")
        elif investor.risk_tolerance:
            return_parts.append(f"Risk tolerance: {investor.risk_tolerance}")
        if investor.capital_available:
            return_parts.append(f"Capital available: ${investor.capital_available:,}")
        if preferences and preferences.investment_experience:
            return_parts.append(f"Experience: {preferences.investment_experience}")
        if return_parts:
            sections["return_profile"] = "\n".join(return_parts)

        # 4. Specific concerns (narrative)
        if preferences and preferences.specific_concerns:
            sections["specific_concerns"] = preferences.specific_concerns

        # 5. Call insights (narrative)
        if call_summary:
            sections["call_insights"] = call_summary

        # 6. Full profile (composite)
        all_parts = [v for v in sections.values()]
        if all_parts:
            sections["full_profile"] = "\n\n".join(all_parts)

        # Generate embeddings for each section
        for section_type, content in sections.items():
            try:
                embedding_vector = await self.generate_embedding(content)

                embedding = InvestorEmbedding(
                    id=uuid.uuid4(),
                    investor_id=investor_id,
                    section_type=section_type,
                    content=content,
                    embedding=embedding_vector,
                )
                self.session.add(embedding)
                embeddings.append(embedding)

            except Exception as e:
                logger.error(
                    f"Failed to create investor embedding for {section_type}: {e}"
                )
                continue

        await self.session.flush()
        logger.info(
            f"Created {len(embeddings)} embeddings for investor {investor_id}"
        )

        return embeddings

    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        property_ids: Optional[List[uuid.UUID]] = None,
        section_types: Optional[List[str]] = None,
    ) -> List[Tuple[PropertyEmbedding, float]]:
        """
        Search for similar property embeddings using cosine distance.

        Args:
            query_embedding: Query vector to match against
            limit: Maximum number of results to return
            property_ids: Optional list of property IDs to filter by
            section_types: Optional list of section types to filter by

        Returns:
            List of (PropertyEmbedding, similarity_score) tuples
        """
        # Build the query using pgvector cosine distance operator
        # Cosine distance is 1 - cosine_similarity, so we order ascending
        query = f"""
            SELECT
                pe.*,
                1 - (pe.embedding <=> :query_embedding::vector) as similarity
            FROM property_embeddings pe
            WHERE 1=1
        """

        params = {"query_embedding": str(query_embedding)}

        if property_ids:
            placeholders = ", ".join(
                f":pid_{i}" for i in range(len(property_ids))
            )
            query += f" AND pe.property_id IN ({placeholders})"
            for i, pid in enumerate(property_ids):
                params[f"pid_{i}"] = str(pid)

        if section_types:
            placeholders = ", ".join(
                f":st_{i}" for i in range(len(section_types))
            )
            query += f" AND pe.section_type IN ({placeholders})"
            for i, st in enumerate(section_types):
                params[f"st_{i}"] = st

        query += " ORDER BY similarity DESC LIMIT :limit"
        params["limit"] = limit

        result = await self.session.execute(text(query), params)
        rows = result.fetchall()

        # Convert to PropertyEmbedding objects with similarity scores
        embeddings_with_scores = []
        for row in rows:
            # Reconstruct the PropertyEmbedding from the row
            embedding = PropertyEmbedding(
                id=row.id,
                property_id=row.property_id,
                section_type=row.section_type,
                content=row.content,
                embedding=row.embedding,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            embeddings_with_scores.append((embedding, row.similarity))

        return embeddings_with_scores

    async def find_similar_properties(
        self,
        investor_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Find properties most similar to an investor's profile.

        Args:
            investor_id: UUID of the investor
            limit: Maximum number of results to return

        Returns:
            List of (property_id, avg_similarity_score) tuples
        """
        # Get the investor's full_profile embedding
        result = await self.session.execute(
            select(InvestorEmbedding).where(
                InvestorEmbedding.investor_id == investor_id,
                InvestorEmbedding.section_type == "full_profile",
            )
        )
        investor_embedding = result.scalar_one_or_none()

        if not investor_embedding:
            logger.warning(f"No full_profile embedding found for investor {investor_id}")
            return []

        # Find similar property embeddings and aggregate by property
        query = """
            SELECT
                pe.property_id,
                AVG(1 - (pe.embedding <=> :query_embedding::vector)) as avg_similarity
            FROM property_embeddings pe
            GROUP BY pe.property_id
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """

        result = await self.session.execute(
            text(query),
            {
                "query_embedding": str(investor_embedding.embedding),
                "limit": limit,
            },
        )

        return [(row.property_id, float(row.avg_similarity)) for row in result.fetchall()]

    async def find_similar_investors(
        self,
        property_id: uuid.UUID,
        limit: int = 10,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Find investors most similar to a property's profile.

        Args:
            property_id: UUID of the property
            limit: Maximum number of results to return

        Returns:
            List of (investor_id, avg_similarity_score) tuples
        """
        # Get the property's embeddings (use executive_summary or investment_thesis)
        result = await self.session.execute(
            select(PropertyEmbedding).where(
                PropertyEmbedding.property_id == property_id,
                PropertyEmbedding.section_type.in_(
                    ["executive_summary", "investment_thesis", "investment_terms"]
                ),
            )
        )
        property_embeddings = result.scalars().all()

        if not property_embeddings:
            logger.warning(f"No embeddings found for property {property_id}")
            return []

        # Average the property embeddings
        avg_embedding = [0.0] * EMBEDDING_DIMENSIONS
        for pe in property_embeddings:
            for i, val in enumerate(pe.embedding):
                avg_embedding[i] += val / len(property_embeddings)

        # Find similar investor embeddings and aggregate by investor
        query = """
            SELECT
                ie.investor_id,
                AVG(1 - (ie.embedding <=> :query_embedding::vector)) as avg_similarity
            FROM investor_embeddings ie
            WHERE ie.section_type = 'full_profile'
            GROUP BY ie.investor_id
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """

        result = await self.session.execute(
            text(query),
            {
                "query_embedding": str(avg_embedding),
                "limit": limit,
            },
        )

        return [(row.investor_id, float(row.avg_similarity)) for row in result.fetchall()]

    async def search_properties_by_query(
        self,
        query: str,
        limit: int = 20,
        min_similarity: float = 0.3,
        status: Optional[str] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Search for properties using a natural language query.

        This method generates an embedding for the query text and finds
        properties with similar embeddings using cosine similarity.

        Args:
            query: Natural language search query (e.g., "multifamily in growing markets")
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            status: Optional filter by property status (active, closed, paused)

        Returns:
            List of (property_id, similarity_score) tuples sorted by similarity
        """
        # Generate embedding for the query
        try:
            query_embedding = await self.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return []

        # Build query to search properties by embedding similarity
        # Join with properties table to filter by status if provided
        query_sql = """
            SELECT
                pe.property_id,
                AVG(1 - (pe.embedding <=> :query_embedding::vector)) as avg_similarity
            FROM property_embeddings pe
        """

        if status:
            query_sql += """
                JOIN deals p ON pe.property_id = p.id
                WHERE p.status = :status
            """

        query_sql += """
            GROUP BY pe.property_id
            HAVING AVG(1 - (pe.embedding <=> :query_embedding::vector)) >= :min_similarity
            ORDER BY avg_similarity DESC
            LIMIT :limit
        """

        params = {
            "query_embedding": str(query_embedding),
            "limit": limit,
            "min_similarity": min_similarity,
        }
        if status:
            params["status"] = status

        result = await self.session.execute(text(query_sql), params)
        rows = result.fetchall()

        logger.info(f"Semantic search for '{query[:50]}...' found {len(rows)} results")

        return [(row.property_id, float(row.avg_similarity)) for row in rows]
