"""Tests for vds_agent_core.llm.cache."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from vds_agent_core.llm.cache import (
    AnalysisCache,
    CacheEntry,
    CacheStats,
    LLMResponseCache,
    _default_cache_root,
)

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# _default_cache_root
# ---------------------------------------------------------------------------


def test_default_cache_root_uses_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VDS_CACHE_ROOT", str(tmp_path / "custom"))
    assert _default_cache_root() == tmp_path / "custom" / "llm"


def test_default_cache_root_falls_back_to_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDS_CACHE_ROOT", raising=False)
    result = _default_cache_root()
    assert result == Path.home() / ".vds" / "cache" / "llm"


# ---------------------------------------------------------------------------
# LLMResponseCache — instantiation
# ---------------------------------------------------------------------------


def test_cache_init_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Default init creates cache_dir from _default_cache_root."""
    monkeypatch.setenv("VDS_CACHE_ROOT", str(tmp_path))
    cache = LLMResponseCache()
    assert cache.cache_dir == tmp_path / "llm"
    assert cache.cache_dir.is_dir()


def test_cache_init_custom_root(tmp_path: Path) -> None:
    """Custom cache_root is used directly."""
    custom = tmp_path / "my-cache"
    cache = LLMResponseCache(cache_root=custom)
    assert cache.cache_dir == custom
    assert custom.is_dir()


def test_cache_init_string_root(tmp_path: Path) -> None:
    """String cache_root is converted to Path."""
    cache = LLMResponseCache(cache_root=str(tmp_path / "str-cache"))
    assert isinstance(cache.cache_dir, Path)
    assert cache.cache_dir.is_dir()


# ---------------------------------------------------------------------------
# get / set round-trip
# ---------------------------------------------------------------------------


def test_get_set_roundtrip(tmp_path: Path) -> None:
    cache = LLMResponseCache(cache_root=tmp_path / "cache")
    cache.set("hello world", "gpt-4", "response text", input_tokens=10, output_tokens=20)

    entry = cache.get("hello world", "gpt-4")
    assert entry is not None
    assert entry.response == "response text"
    assert entry.model == "gpt-4"
    assert entry.input_tokens == 10
    assert entry.output_tokens == 20


def test_get_miss_returns_none(tmp_path: Path) -> None:
    cache = LLMResponseCache(cache_root=tmp_path / "cache")
    assert cache.get("nonexistent", "gpt-4") is None


def test_get_from_disk_after_memory_clear(tmp_path: Path) -> None:
    """Disk cache is read when memory cache is empty."""
    cache = LLMResponseCache(cache_root=tmp_path / "cache")
    cache.set("prompt", "model-x", "disk-response")

    # Clear memory cache only, disk remains
    cache._memory_cache.clear()

    entry = cache.get("prompt", "model-x")
    assert entry is not None
    assert entry.response == "disk-response"


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------


def test_expired_entry_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = LLMResponseCache(cache_root=tmp_path / "cache", default_ttl=1)
    cache.set("prompt", "model", "resp")

    # Capture real time, then fast-forward past TTL
    future = time.time() + 10
    monkeypatch.setattr(time, "time", lambda: future)
    assert cache.get("prompt", "model") is None


# ---------------------------------------------------------------------------
# Metrics callback
# ---------------------------------------------------------------------------


def test_metrics_callback_called_on_hit(tmp_path: Path) -> None:
    callback = MagicMock()
    cache = LLMResponseCache(cache_root=tmp_path / "cache", metrics_callback=callback)
    cache.set("p", "m", "r")
    cache.get("p", "m")

    callback.assert_called_once_with("llm")


def test_no_metrics_callback_no_error(tmp_path: Path) -> None:
    """No callback set — hits still work without error."""
    cache = LLMResponseCache(cache_root=tmp_path / "cache")
    cache.set("p", "m", "r")
    entry = cache.get("p", "m")
    assert entry is not None


def test_metrics_callback_called_on_disk_hit(tmp_path: Path) -> None:
    callback = MagicMock()
    cache = LLMResponseCache(cache_root=tmp_path / "cache", metrics_callback=callback)
    cache.set("p", "m", "r")
    cache._memory_cache.clear()  # Force disk read
    cache.get("p", "m")

    callback.assert_called_once_with("llm")


# ---------------------------------------------------------------------------
# CacheStats tracking
# ---------------------------------------------------------------------------


def test_stats_tracking(tmp_path: Path) -> None:
    cache = LLMResponseCache(cache_root=tmp_path / "cache")

    # Miss
    cache.get("miss", "m")
    assert cache.stats.misses == 1
    assert cache.stats.hits == 0

    # Set + hit
    cache.set("hit", "m", "r", input_tokens=100, output_tokens=50)
    cache.get("hit", "m")
    assert cache.stats.hits == 1
    assert cache.stats.saved_tokens == 150

    stats = cache.get_stats()
    assert stats.hit_rate == 0.5
    assert stats.saved_cost > 0


def test_stats_empty_hit_rate() -> None:
    stats = CacheStats()
    assert stats.hit_rate == 0.0


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_removes_all(tmp_path: Path) -> None:
    cache = LLMResponseCache(cache_root=tmp_path / "cache")
    cache.set("a", "m", "r1")
    cache.set("b", "m", "r2")

    count = cache.clear()
    assert count == 2
    assert cache.get("a", "m") is None
    assert cache.get("b", "m") is None
    assert cache.stats.hits == 0


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------


def test_cache_entry_is_expired() -> None:
    entry = CacheEntry(
        key="k",
        response="r",
        model="m",
        created_at=time.time() - 100,
        ttl_seconds=10,
    )
    assert entry.is_expired is True


def test_cache_entry_not_expired() -> None:
    entry = CacheEntry(
        key="k",
        response="r",
        model="m",
        created_at=time.time(),
        ttl_seconds=3600,
    )
    assert entry.is_expired is False


# ---------------------------------------------------------------------------
# AnalysisCache
# ---------------------------------------------------------------------------


def test_analysis_cache_roundtrip(tmp_path: Path) -> None:
    ac = AnalysisCache(cache_dir=tmp_path / "analysis")
    ctx = {"check": "CL-001"}
    ac.set("content", ctx, {"score": 0.9})

    result = ac.get("content", ctx)
    assert result == {"score": 0.9}


def test_analysis_cache_miss(tmp_path: Path) -> None:
    ac = AnalysisCache(cache_dir=tmp_path / "analysis")
    assert ac.get("nope", {}) is None


def test_analysis_cache_stats(tmp_path: Path) -> None:
    ac = AnalysisCache(cache_dir=tmp_path / "analysis")
    ac.set("c", {}, {"v": 1})
    ac.get("c", {})
    s = ac.stats()
    assert s["hits"] == 1


def test_analysis_cache_clear(tmp_path: Path) -> None:
    ac = AnalysisCache(cache_dir=tmp_path / "analysis")
    ac.set("c", {}, {"v": 1})
    ac.clear()
    assert ac.get("c", {}) is None
