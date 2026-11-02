"""Tests for LLMResponseCache context key support (FR-A1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from vds_agent_core.llm.cache import LLMResponseCache


@pytest.fixture()
def cache(tmp_path: Path) -> LLMResponseCache:
    return LLMResponseCache(cache_root=tmp_path / "cache")


class TestCacheContextKey:
    """FR-A1: context dict differentiates cache keys."""

    def test_different_context_different_keys(self, cache: LLMResponseCache) -> None:
        """Same prompt + model with different context produces different cache keys."""
        prompt = "evaluate architecture"
        model = "gpt-4o"

        cache.set(prompt, model, "response-A", context={"fr_hash": "aaa"})
        cache.set(prompt, model, "response-B", context={"fr_hash": "bbb"})

        hit_a = cache.get(prompt, model, context={"fr_hash": "aaa"})
        hit_b = cache.get(prompt, model, context={"fr_hash": "bbb"})

        assert hit_a is not None
        assert hit_b is not None
        assert hit_a.response == "response-A"
        assert hit_b.response == "response-B"

    def test_same_context_cache_hit(self, cache: LLMResponseCache) -> None:
        """Same prompt + model + same context returns cached entry."""
        prompt = "evaluate endpoints"
        model = "gpt-4o"
        ctx = {"fr_hash": "deadbeef", "run_id": "r1"}

        cache.set(prompt, model, "cached-response", context=ctx)
        hit = cache.get(prompt, model, context=ctx)

        assert hit is not None
        assert hit.response == "cached-response"
        assert cache.stats.hits == 1

    def test_no_context_backward_compat(self, cache: LLMResponseCache) -> None:
        """Omitting context preserves existing behavior (no regression)."""
        prompt = "score this"
        model = "gpt-4o"

        cache.set(prompt, model, "old-response")
        hit = cache.get(prompt, model)

        assert hit is not None
        assert hit.response == "old-response"

        # With context=None explicitly should also work
        hit2 = cache.get(prompt, model, context=None)
        assert hit2 is not None
        assert hit2.response == "old-response"
