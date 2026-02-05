"""
Semantic Matching - Layer 3 of the matching engine.

Uses vector embeddings and cosine similarity to find semantic
alignment between investor profiles and deal descriptions.
Implements weighted section-to-section matching for precise scoring.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.embeddings import InvestorEmbedding, PropertyEmbedding
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Weighted section pairs: (investor_section, property_section) -> weight
# Weights sum to 1.0
SECTION_WEIGHTS: Dict[Tuple[str, str], float] = {
    ("investment_thesis", "investment_thesis"): 0.20,
    ("investment_thesis", "executive_summary"): 0.10,
    ("investment_criteria", "investment_terms"): 0.15,
    ("investment_criteria", "property_overview"): 0.05,
    ("return_profile", "financials"): 0.20,
    ("return_profile", "cash_flow_projection"): 0.05,
    ("specific_concerns", "risk_factors"): 0.10,
    ("call_insights", "executive_summary"): 0.05,
    ("full_profile", "deal_structure"): 0.05,
    ("full_profile", "sponsor_profile"): 0.05,
}


@dataclass
class SemanticMatchResult:
    """Result of semantic matching evaluation."""

    score: float  # 0-100 (normalized from cosine similarity)
    raw_similarity: float  # Raw cosine similarity 0-1
    matched_sections: List[Tuple[str, float]] = field(default_factory=list)


def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    dot = np.dot(a_arr, b_arr)
    norm_a = np.linalg.norm(a_arr)
    norm_b = np.linalg.norm(b_arr)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


class SemanticMatcher:
    """
    Layer 3: Semantic matching using vector embeddings.

    This layer:
    1. Retrieves embeddings for both investor and property
    2. Computes weighted cosine similarity between relevant section pairs
    3. Returns a normalized score (0-100) based on semantic alignment
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.embedding_service = EmbeddingService(session)

    async def _load_embeddings_by_section(
        self,
        table: str,
        id_column: str,
        entity_id: uuid.UUID,
    ) -> Dict[str, list]:
        """Load all embeddings for an entity, keyed by section_type."""
        if table == "investor_embeddings":
            result = await self.session.execute(
                select(InvestorEmbedding).where(
                    InvestorEmbedding.investor_id == entity_id
                )
            )
        else:
            result = await self.session.execute(
                select(PropertyEmbedding).where(
                    PropertyEmbedding.property_id == entity_id
                )
            )
        embeddings = result.scalars().all()
        return {e.section_type: e.embedding for e in embeddings}

    async def compute_semantic_score(
        self,
        investor_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> SemanticMatchResult:
        """
        Compute semantic similarity between investor and property
        using weighted section-to-section comparisons.

        Args:
            investor_id: UUID of the investor
            property_id: UUID of the property

        Returns:
            SemanticMatchResult with normalized score and details
        """
        try:
            # Load all embeddings for both entities
            investor_embeddings = await self._load_embeddings_by_section(
                "investor_embeddings", "investor_id", investor_id
            )
            property_embeddings = await self._load_embeddings_by_section(
                "property_embeddings", "property_id", property_id
            )

            if not investor_embeddings or not property_embeddings:
                # Fallback: use the old full_profile approach
                return await self._fallback_similarity(investor_id, property_id)

            weighted_sum = 0.0
            total_weight = 0.0
            matched_sections = []

            for (inv_section, prop_section), weight in SECTION_WEIGHTS.items():
                inv_emb = investor_embeddings.get(inv_section)
                prop_emb = property_embeddings.get(prop_section)

                if inv_emb is not None and prop_emb is not None:
                    sim = _cosine_similarity(inv_emb, prop_emb)
                    weighted_sum += sim * weight
                    total_weight += weight
                    matched_sections.append(
                        (f"{inv_section}->{prop_section}", sim)
                    )

            if total_weight > 0:
                # Re-normalize weights to account for missing sections
                raw_similarity = weighted_sum / total_weight
            else:
                # No section pairs matched at all — fall back
                return await self._fallback_similarity(investor_id, property_id)

            normalized_score = min(100.0, raw_similarity * 100)

            return SemanticMatchResult(
                score=normalized_score,
                raw_similarity=raw_similarity,
                matched_sections=matched_sections,
            )

        except Exception as e:
            logger.error(
                f"Semantic matching failed for investor {investor_id} "
                f"and property {property_id}: {e}"
            )
            return SemanticMatchResult(
                score=50.0,
                raw_similarity=0.5,
                matched_sections=[],
            )

    async def _fallback_similarity(
        self,
        investor_id: uuid.UUID,
        property_id: uuid.UUID,
    ) -> SemanticMatchResult:
        """
        Fallback: compute similarity using full_profile vs all property sections averaged.
        Used when specific section pairs are not available.
        """
        try:
            result = await self.session.execute(
                select(InvestorEmbedding).where(
                    InvestorEmbedding.investor_id == investor_id,
                    InvestorEmbedding.section_type == "full_profile",
                )
            )
            investor_emb = result.scalar_one_or_none()

            if not investor_emb:
                return SemanticMatchResult(score=50.0, raw_similarity=0.5, matched_sections=[])

            prop_result = await self.session.execute(
                select(PropertyEmbedding).where(
                    PropertyEmbedding.property_id == property_id
                )
            )
            property_embs = prop_result.scalars().all()

            if not property_embs:
                return SemanticMatchResult(score=50.0, raw_similarity=0.5, matched_sections=[])

            similarities = []
            for pe in property_embs:
                sim = _cosine_similarity(investor_emb.embedding, pe.embedding)
                similarities.append(sim)

            avg_sim = sum(similarities) / len(similarities)

            return SemanticMatchResult(
                score=min(100.0, avg_sim * 100),
                raw_similarity=avg_sim,
                matched_sections=[("full_profile->avg_all", avg_sim)],
            )

        except Exception:
            return SemanticMatchResult(score=50.0, raw_similarity=0.5, matched_sections=[])

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
        # Load investor embeddings once
        investor_embeddings = await self._load_embeddings_by_section(
            "investor_embeddings", "investor_id", investor_id
        )

        results = []
        for property_id in property_ids:
            if not investor_embeddings:
                results.append((
                    property_id,
                    SemanticMatchResult(score=50.0, raw_similarity=0.5, matched_sections=[]),
                ))
                continue

            property_embeddings = await self._load_embeddings_by_section(
                "property_embeddings", "property_id", property_id
            )

            if not property_embeddings:
                results.append((
                    property_id,
                    SemanticMatchResult(score=50.0, raw_similarity=0.5, matched_sections=[]),
                ))
                continue

            weighted_sum = 0.0
            total_weight = 0.0
            matched_sections = []

            for (inv_section, prop_section), weight in SECTION_WEIGHTS.items():
                inv_emb = investor_embeddings.get(inv_section)
                prop_emb = property_embeddings.get(prop_section)

                if inv_emb is not None and prop_emb is not None:
                    sim = _cosine_similarity(inv_emb, prop_emb)
                    weighted_sum += sim * weight
                    total_weight += weight
                    matched_sections.append(
                        (f"{inv_section}->{prop_section}", sim)
                    )

            if total_weight > 0:
                raw_similarity = weighted_sum / total_weight
            else:
                raw_similarity = 0.5

            results.append((
                property_id,
                SemanticMatchResult(
                    score=min(100.0, raw_similarity * 100),
                    raw_similarity=raw_similarity,
                    matched_sections=matched_sections,
                ),
            ))

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
        # Get all property IDs that have embeddings
        result = await self.session.execute(
            text("SELECT DISTINCT property_id FROM property_embeddings")
        )
        all_property_ids = [row[0] for row in result.fetchall()]

        if not all_property_ids:
            return []

        # Compute scores for all
        all_results = await self.batch_compute(investor_id, all_property_ids)

        # Filter by min_score and sort
        filtered = [
            (pid, res) for pid, res in all_results if res.score >= min_score
        ]
        filtered.sort(key=lambda x: x[1].score, reverse=True)

        return filtered[:limit]
