"""
Repository for embedding database operations.

Provides data access layer for PropertyEmbedding and InvestorEmbedding models,
including pgvector similarity search operations.
"""

import uuid
from typing import List, Optional, Tuple

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embeddings import InvestorEmbedding, PropertyEmbedding


class EmbeddingRepository:
    """Repository for embedding CRUD and search operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== Property Embeddings ====================

    async def create_property_embedding(
        self, embedding: PropertyEmbedding
    ) -> PropertyEmbedding:
        """Create a new property embedding."""
        self.session.add(embedding)
        await self.session.flush()
        return embedding

    async def get_property_embeddings(
        self, property_id: uuid.UUID
    ) -> List[PropertyEmbedding]:
        """Get all embeddings for a property."""
        result = await self.session.execute(
            select(PropertyEmbedding).where(
                PropertyEmbedding.property_id == property_id
            )
        )
        return list(result.scalars().all())

    async def get_property_embedding_by_section(
        self, property_id: uuid.UUID, section_type: str
    ) -> Optional[PropertyEmbedding]:
        """Get a specific section embedding for a property."""
        result = await self.session.execute(
            select(PropertyEmbedding).where(
                PropertyEmbedding.property_id == property_id,
                PropertyEmbedding.section_type == section_type,
            )
        )
        return result.scalar_one_or_none()

    async def delete_property_embeddings(self, property_id: uuid.UUID) -> int:
        """Delete all embeddings for a property. Returns count deleted."""
        result = await self.session.execute(
            delete(PropertyEmbedding).where(
                PropertyEmbedding.property_id == property_id
            )
        )
        return result.rowcount

    async def search_similar_properties(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        exclude_property_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Search for properties with similar embeddings.

        Args:
            query_embedding: Query vector
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0-1)
            exclude_property_ids: Property IDs to exclude from results

        Returns:
            List of (property_id, similarity_score) tuples
        """
        # Build query with cosine similarity
        query = """
            SELECT
                pe.property_id,
                AVG(1 - (pe.embedding <=> :query_embedding::vector)) as similarity
            FROM property_embeddings pe
            WHERE 1=1
        """
        params = {"query_embedding": str(query_embedding)}

        if exclude_property_ids:
            placeholders = ", ".join(
                f":excl_{i}" for i in range(len(exclude_property_ids))
            )
            query += f" AND pe.property_id NOT IN ({placeholders})"
            for i, pid in enumerate(exclude_property_ids):
                params[f"excl_{i}"] = str(pid)

        query += """
            GROUP BY pe.property_id
            HAVING AVG(1 - (pe.embedding <=> :query_embedding::vector)) >= :min_sim
            ORDER BY similarity DESC
            LIMIT :limit
        """
        params["min_sim"] = min_similarity
        params["limit"] = limit

        result = await self.session.execute(text(query), params)
        return [(row.property_id, float(row.similarity)) for row in result.fetchall()]

    # ==================== Investor Embeddings ====================

    async def create_investor_embedding(
        self, embedding: InvestorEmbedding
    ) -> InvestorEmbedding:
        """Create a new investor embedding."""
        self.session.add(embedding)
        await self.session.flush()
        return embedding

    async def get_investor_embeddings(
        self, investor_id: uuid.UUID
    ) -> List[InvestorEmbedding]:
        """Get all embeddings for an investor."""
        result = await self.session.execute(
            select(InvestorEmbedding).where(
                InvestorEmbedding.investor_id == investor_id
            )
        )
        return list(result.scalars().all())

    async def get_investor_embedding_by_section(
        self, investor_id: uuid.UUID, section_type: str
    ) -> Optional[InvestorEmbedding]:
        """Get a specific section embedding for an investor."""
        result = await self.session.execute(
            select(InvestorEmbedding).where(
                InvestorEmbedding.investor_id == investor_id,
                InvestorEmbedding.section_type == section_type,
            )
        )
        return result.scalar_one_or_none()

    async def delete_investor_embeddings(self, investor_id: uuid.UUID) -> int:
        """Delete all embeddings for an investor. Returns count deleted."""
        result = await self.session.execute(
            delete(InvestorEmbedding).where(
                InvestorEmbedding.investor_id == investor_id
            )
        )
        return result.rowcount

    async def search_similar_investors(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.0,
        exclude_investor_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Search for investors with similar embeddings.

        Args:
            query_embedding: Query vector
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0-1)
            exclude_investor_ids: Investor IDs to exclude from results

        Returns:
            List of (investor_id, similarity_score) tuples
        """
        query = """
            SELECT
                ie.investor_id,
                AVG(1 - (ie.embedding <=> :query_embedding::vector)) as similarity
            FROM investor_embeddings ie
            WHERE ie.section_type = 'full_profile'
        """
        params = {"query_embedding": str(query_embedding)}

        if exclude_investor_ids:
            placeholders = ", ".join(
                f":excl_{i}" for i in range(len(exclude_investor_ids))
            )
            query += f" AND ie.investor_id NOT IN ({placeholders})"
            for i, iid in enumerate(exclude_investor_ids):
                params[f"excl_{i}"] = str(iid)

        query += """
            GROUP BY ie.investor_id
            HAVING AVG(1 - (ie.embedding <=> :query_embedding::vector)) >= :min_sim
            ORDER BY similarity DESC
            LIMIT :limit
        """
        params["min_sim"] = min_similarity
        params["limit"] = limit

        result = await self.session.execute(text(query), params)
        return [(row.investor_id, float(row.similarity)) for row in result.fetchall()]

    # ==================== Cross-search Operations ====================

    async def find_properties_for_investor(
        self,
        investor_id: uuid.UUID,
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Find properties most similar to an investor's profile.

        Uses the investor's full_profile embedding to search against
        all property embeddings.

        Args:
            investor_id: Investor UUID
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (property_id, avg_similarity) tuples
        """
        # Get investor's full_profile embedding
        investor_emb = await self.get_investor_embedding_by_section(
            investor_id, "full_profile"
        )
        if not investor_emb:
            return []

        return await self.search_similar_properties(
            query_embedding=investor_emb.embedding,
            limit=limit,
            min_similarity=min_similarity,
        )

    async def find_investors_for_property(
        self,
        property_id: uuid.UUID,
        limit: int = 10,
        min_similarity: float = 0.3,
    ) -> List[Tuple[uuid.UUID, float]]:
        """
        Find investors most similar to a property's profile.

        Uses the property's key embeddings (executive_summary, investment_thesis)
        to search against investor embeddings.

        Args:
            property_id: Property UUID
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (investor_id, avg_similarity) tuples
        """
        # Get property's key embeddings
        embeddings = await self.get_property_embeddings(property_id)
        key_embeddings = [
            e for e in embeddings
            if e.section_type in ("executive_summary", "investment_thesis", "investment_terms")
        ]

        if not key_embeddings:
            return []

        # Average the embeddings
        embedding_dim = len(key_embeddings[0].embedding)
        avg_embedding = [0.0] * embedding_dim
        for emb in key_embeddings:
            for i, val in enumerate(emb.embedding):
                avg_embedding[i] += val / len(key_embeddings)

        return await self.search_similar_investors(
            query_embedding=avg_embedding,
            limit=limit,
            min_similarity=min_similarity,
        )

    async def get_embedding_stats(self) -> dict:
        """Get statistics about stored embeddings."""
        property_count = await self.session.execute(
            text("SELECT COUNT(*) FROM property_embeddings")
        )
        investor_count = await self.session.execute(
            text("SELECT COUNT(*) FROM investor_embeddings")
        )
        property_sections = await self.session.execute(
            text(
                "SELECT section_type, COUNT(*) as cnt "
                "FROM property_embeddings GROUP BY section_type"
            )
        )
        investor_sections = await self.session.execute(
            text(
                "SELECT section_type, COUNT(*) as cnt "
                "FROM investor_embeddings GROUP BY section_type"
            )
        )

        return {
            "total_property_embeddings": property_count.scalar(),
            "total_investor_embeddings": investor_count.scalar(),
            "property_sections": {
                row.section_type: row.cnt for row in property_sections.fetchall()
            },
            "investor_sections": {
                row.section_type: row.cnt for row in investor_sections.fetchall()
            },
        }
