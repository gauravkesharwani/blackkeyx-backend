"""Tests for semantic matching logic (Layer 3)."""

import math

import numpy as np
import pytest

from app.services.matching.semantic_match import (
    SECTION_WEIGHTS,
    SemanticMatchResult,
    _cosine_similarity,
)


class TestCosineimilarity:
    """Test the cosine similarity function."""

    def test_identical_vectors(self):
        vec = [1.0, 2.0, 3.0]
        sim = _cosine_similarity(vec, vec)
        assert math.isclose(sim, 1.0, rel_tol=1e-5)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        sim = _cosine_similarity(a, b)
        assert math.isclose(sim, 0.0, abs_tol=1e-5)

    def test_opposite_vectors(self):
        a = [1.0, 2.0, 3.0]
        b = [-1.0, -2.0, -3.0]
        sim = _cosine_similarity(a, b)
        assert math.isclose(sim, -1.0, rel_tol=1e-5)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_both_zero_vectors(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_high_dimensional_vectors(self):
        """Test with OpenAI embedding-sized vectors (1536 dimensions)."""
        rng = np.random.default_rng(42)
        a = rng.random(1536).tolist()
        b = rng.random(1536).tolist()
        sim = _cosine_similarity(a, b)
        # Random high-dimensional vectors should have similarity near 0.5
        assert 0.0 < sim < 1.0

    def test_similar_vectors_high_similarity(self):
        """Slightly perturbed vector should have high similarity."""
        rng = np.random.default_rng(42)
        a = rng.random(100).tolist()
        # Add small noise
        noise = (rng.random(100) * 0.01).tolist()
        b = [x + n for x, n in zip(a, noise)]
        sim = _cosine_similarity(a, b)
        assert sim > 0.99


class TestSectionWeights:
    """Test that section weight configuration is valid."""

    def test_weights_sum_to_one(self):
        total = sum(SECTION_WEIGHTS.values())
        assert math.isclose(total, 1.0, rel_tol=1e-5)

    def test_all_weights_positive(self):
        for pair, weight in SECTION_WEIGHTS.items():
            assert weight > 0, f"Weight for {pair} should be positive"

    def test_expected_section_pairs_present(self):
        expected_investor_sections = {
            "investment_thesis",
            "investment_criteria",
            "return_profile",
            "specific_concerns",
            "call_insights",
            "full_profile",
        }
        actual_investor_sections = {k[0] for k in SECTION_WEIGHTS.keys()}
        assert expected_investor_sections == actual_investor_sections

    def test_financials_has_high_weight(self):
        """Return profile -> financials should be heavily weighted."""
        weight = SECTION_WEIGHTS.get(("return_profile", "financials"), 0)
        assert weight >= 0.15, "Financial matching should have significant weight"


class TestSemanticMatchResult:
    """Test the SemanticMatchResult dataclass."""

    def test_default_matched_sections(self):
        result = SemanticMatchResult(score=75.0, raw_similarity=0.75)
        assert result.matched_sections == []

    def test_score_bounds(self):
        result = SemanticMatchResult(
            score=85.5,
            raw_similarity=0.855,
            matched_sections=[("thesis->thesis", 0.9)],
        )
        assert 0 <= result.score <= 100
        assert 0 <= result.raw_similarity <= 1
