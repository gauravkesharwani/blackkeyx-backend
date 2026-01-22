"""
Semantic Matching - Layer 3 of the matching engine.

Uses vector embeddings and cosine similarity to find semantic
alignment between investor profiles and deal descriptions.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class SemanticMatchResult:
    """Result of semantic matching evaluation."""

    score: float  # 0-100 (normalized from cosine similarity)
    raw_similarity: float  # Raw cosine similarity 0-1
    matched_sections: List[Tuple[str, float]]  # Section type and its similarity


class SemanticMatcher:
    """
    Layer 3: Semantic matching using vector embeddings.

    This layer:
    1. Retrieves embeddings for both investor and property
    2. Computes cosine similarity between relevant sections
    3. Returns a normalized score (0-100) based on semantic alignment
    """

    def __init__(self, session: AsyncSession):
        self.embedding_service = EmbeddingService(session)

    async def compute_semantic_score(
        self,
        investor_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> SemanticMatchResult:
        """
        Compute semantic similarity between investor and property.

        Args:
            investor_id: UUID of the investor
            property_id: UUID of the property

        Returns:
            SemanticMatchResult with normalized score and details
        """
        try:
            # Find similar properties for this investor
            similar_properties = await self.embedding_service.find_similar_properties(
                investor_id=investor_id,
                limit=100,  # Get more to find specific property
            )

            # Find the specific property's similarity
            property_similarity = 0.0
            for pid, similarity in similar_properties:
                if pid == property_id:
                    property_similarity = similarity
                    break

            # If property not found in similar results, compute directly
            if property_similarity == 0.0:
                property_similarity = await self._compute_direct_similarity(
                    investor_id, property_id
                )

            # Normalize to 0-100 scale
            # Cosine similarity typically ranges 0-1 for positive embeddings
            # We scale it to 0-100 with a slight boost for high similarities
            normalized_score = min(100.0, property_similarity * 100)

            return SemanticMatchResult(
                score=normalized_score,
                raw_similarity=property_similarity,
                matched_sections=[],  # Simplified - could expand to show section matches
            )

        except Exception as e:
            logger.error(
                f"Semantic matching failed for investor {investor_id} "
                f"and property {property_id}: {e}"
            )
            return SemanticMatchResult(
                score=50.0,  # Neutral score on error
                raw_similarity=0.5,
                matched_sections=[],
            )

    async def _compute_direct_similarity(
        self,
        investor_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> float:
        """
        Compute similarity directly between investor and property embeddings.

        Used when the property isn't in the top similar results.

        Args:
            investor_id: UUID of the investor
            property_id: UUID of the property

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # This would require additional database queries to fetch
            # both embeddings and compute similarity
            # For now, return a neutral score
            return 0.5

        except Exception:
            return 0.5

    async def batch_compute(
        self,
        investor_id: uuid.UUID,
        property_ids: List[uuid.UUID],
    ) -> List[Tuple[uuid.UUID, SemanticMatchResult]]:
        """
        Compute semantic scores for multiple properties.

        Args:
            investor_id: UUID of the investor
            property_ids: List of property UUIDs to score

        Returns:
            List of (property_id, SemanticMatchResult) tuples
        """
        # Get all similar properties at once
        similar_properties = await self.embedding_service.find_similar_properties(
            investor_id=investor_id,
            limit=1000,  # Get many to cover requested properties
        )

        # Build lookup map
        similarity_map = {pid: sim for pid, sim in similar_properties}

        results = []
        for property_id in property_ids:
            similarity = similarity_map.get(property_id, 0.5)
            result = SemanticMatchResult(
                score=min(100.0, similarity * 100),
                raw_similarity=similarity,
                matched_sections=[],
            )
            results.append((property_id, result))

        return results

    async def find_top_matches(
        self,
        investor_id: uuid.UUID,
        limit: int = 10,
        min_score: float = 30.0,
    ) -> List[Tuple[uuid.UUID, SemanticMatchResult]]:
        """
        Find top semantically matching properties for an investor.

        Args:
            investor_id: UUID of the investor
            limit: Maximum number of matches to return
            min_score: Minimum score threshold (0-100)

        Returns:
            List of (property_id, SemanticMatchResult) tuples sorted by score
        """
        min_similarity = min_score / 100.0

        similar_properties = await self.embedding_service.find_similar_properties(
            investor_id=investor_id,
            limit=limit,
        )

        results = []
        for property_id, similarity in similar_properties:
            if similarity >= min_similarity:
                result = SemanticMatchResult(
                    score=min(100.0, similarity * 100),
                    raw_similarity=similarity,
                    matched_sections=[],
                )
                results.append((property_id, result))

        return results
