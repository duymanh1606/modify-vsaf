"""Tests for vds_agent_core.llm.cache.EmbeddingCache (Phase 225 W1 surface).

Covers `EmbeddingCache` and its helper `_default_embedding_cache_root` plus
`_EmbeddingCacheEntry.is_expired`. Disk-cache hit/expired/write-failure
branches are exercised explicitly.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from vds_agent_core.llm.cache import (
    EmbeddingCache,
    _default_embedding_cache_root,
    _EmbeddingCacheEntry,
)

if TYPE_CHECKING:
    import pytest

# ---------------------------------------------------------------------------
# _default_embedding_cache_root — env-var branch + default branch
# ---------------------------------------------------------------------------


def test_default_embedding_cache_root_uses_env_when_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VDS_CACHE_ROOT", str(tmp_path))
    root = _default_embedding_cache_root()
    assert root == tmp_path / "embedding"


def test_default_embedding_cache_root_falls_back_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("VDS_CACHE_ROOT", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = _default_embedding_cache_root()
    assert root == tmp_path / ".vds" / "cache" / "embedding"


# ---------------------------------------------------------------------------
# _EmbeddingCacheEntry.is_expired
# ---------------------------------------------------------------------------


def test_embedding_cache_entry_is_expired_true() -> None:
    entry = _EmbeddingCacheEntry(
        key="k",
        vector=[0.0],
        model="m",
        provider="p",
        base_url="http://x",
        created_at=time.time() - 1000,
        ttl_seconds=10,
    )
    assert entry.is_expired is True


def test_embedding_cache_entry_is_expired_false() -> None:
    entry = _EmbeddingCacheEntry(
        key="k",
        vector=[0.0],
        model="m",
        provider="p",
        base_url="http://x",
        created_at=time.time(),
        ttl_seconds=10000,
    )
    assert entry.is_expired is False


# ---------------------------------------------------------------------------
# EmbeddingCache — constructor variants
# ---------------------------------------------------------------------------


def test_embedding_cache_default_root_constructor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No cache_root kwarg -> uses _default_embedding_cache_root()."""
    monkeypatch.setenv("VDS_CACHE_ROOT", str(tmp_path))
    cache = EmbeddingCache()
    assert cache.cache_dir == tmp_path / "embedding"
    assert cache.cache_dir.exists()


def test_embedding_cache_explicit_root(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path / "custom")
    assert cache.cache_dir == tmp_path / "custom"
    assert cache.cache_dir.exists()


def test_embedding_cache_explicit_root_str(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=str(tmp_path / "custom-str"))
    assert cache.cache_dir == tmp_path / "custom-str"


# ---------------------------------------------------------------------------
# EmbeddingCache — get/set memory paths + miss
# ---------------------------------------------------------------------------


def test_embedding_cache_set_and_get_memory_hit(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path)
    cache.set("hello", "bge-m3", [0.1, 0.2], provider="ollama", base_url="http://x")
    out = cache.get("hello", "bge-m3", provider="ollama", base_url="http://x")
    assert out == [0.1, 0.2]
    assert cache.stats.hits == 1
    assert cache.stats.size == 1


def test_embedding_cache_get_miss_increments_stats(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path)
    out = cache.get("absent", "bge-m3", provider="ollama", base_url="http://x")
    assert out is None
    assert cache.stats.misses == 1
    assert cache.stats.hits == 0


def test_embedding_cache_keys_differ_across_provider(tmp_path: Path) -> None:
    """Same text/model/url but different provider -> different keys (no collision)."""
    cache = EmbeddingCache(cache_root=tmp_path)
    k1 = cache._compute_key("t", "m", provider="ollama", base_url="http://x")
    k2 = cache._compute_key("t", "m", provider="openai", base_url="http://x")
    assert k1 != k2


def test_embedding_cache_keys_differ_across_base_url(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path)
    k1 = cache._compute_key("t", "m", provider="p", base_url="http://a")
    k2 = cache._compute_key("t", "m", provider="p", base_url="http://b")
    assert k1 != k2


# ---------------------------------------------------------------------------
# EmbeddingCache — disk hit branch (memory empty, disk has fresh entry)
# ---------------------------------------------------------------------------


def test_embedding_cache_get_disk_hit_repopulates_memory(tmp_path: Path) -> None:
    cache_a = EmbeddingCache(cache_root=tmp_path, default_ttl=10000)
    cache_a.set("disk-text", "m", [1.0, 2.0], provider="p", base_url="http://x")
    # New cache instance => empty memory; must hit disk.
    cache_b = EmbeddingCache(cache_root=tmp_path, default_ttl=10000)
    out = cache_b.get("disk-text", "m", provider="p", base_url="http://x")
    assert out == [1.0, 2.0]
    assert cache_b.stats.hits == 1
    # Memory cache is now populated.
    out2 = cache_b.get("disk-text", "m", provider="p", base_url="http://x")
    assert out2 == [1.0, 2.0]
    assert cache_b.stats.hits == 2


# ---------------------------------------------------------------------------
# EmbeddingCache — expired memory entry branch
# ---------------------------------------------------------------------------


def test_embedding_cache_expired_memory_entry_falls_through(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path, default_ttl=10000)
    cache.set("t", "m", [9.0], provider="p", base_url="http://x")
    # Mutate the memory entry's created_at to past so is_expired -> True.
    key = cache._compute_key("t", "m", provider="p", base_url="http://x")
    cache._memory_cache[key].created_at = time.time() - 100000
    cache._memory_cache[key].ttl_seconds = 10
    # Disk file is also stale because it was written with the same created_at.
    # However the disk file was written with the original created_at so
    # may still be fresh; remove it explicitly so we hit the proper miss path.
    (tmp_path / f"{key}.json").unlink()
    out = cache.get("t", "m", provider="p", base_url="http://x")
    assert out is None
    # Expired memory entry should have been deleted.
    assert key not in cache._memory_cache


# ---------------------------------------------------------------------------
# EmbeddingCache — expired disk entry branch
# ---------------------------------------------------------------------------


def test_embedding_cache_expired_disk_entry_unlinked(tmp_path: Path) -> None:
    """Expired disk entry triggers unlink + miss."""
    cache = EmbeddingCache(cache_root=tmp_path)
    key = cache._compute_key("t", "m", provider="p", base_url="http://x")
    expired_entry = _EmbeddingCacheEntry(
        key=key,
        vector=[1.0],
        model="m",
        provider="p",
        base_url="http://x",
        created_at=time.time() - 100000,
        ttl_seconds=10,
    )
    (tmp_path / f"{key}.json").write_text(expired_entry.model_dump_json())
    out = cache.get("t", "m", provider="p", base_url="http://x")
    assert out is None
    assert not (tmp_path / f"{key}.json").exists()
    assert cache.stats.misses == 1


# ---------------------------------------------------------------------------
# EmbeddingCache — corrupt disk entry branch (read failure)
# ---------------------------------------------------------------------------


def test_embedding_cache_corrupt_disk_entry_returns_none(tmp_path: Path) -> None:
    """Corrupt JSON on disk triggers warning + miss (no crash)."""
    cache = EmbeddingCache(cache_root=tmp_path)
    key = cache._compute_key("t", "m", provider="p", base_url="http://x")
    (tmp_path / f"{key}.json").write_text("{ not valid json")
    out = cache.get("t", "m", provider="p", base_url="http://x")
    assert out is None
    assert cache.stats.misses == 1


# ---------------------------------------------------------------------------
# EmbeddingCache.set — disk-write-failure branch
# ---------------------------------------------------------------------------


def test_embedding_cache_set_disk_write_failure_logged(tmp_path: Path) -> None:
    """If disk write fails, set() logs warning but does not raise."""
    cache = EmbeddingCache(cache_root=tmp_path)
    with patch.object(Path, "write_text", side_effect=OSError("disk full")):
        # Must not raise; memory cache still populated.
        cache.set("x", "m", [0.0], provider="p", base_url="http://x")
    key = cache._compute_key("x", "m", provider="p", base_url="http://x")
    assert key in cache._memory_cache
    # stats.size NOT incremented because disk write failed.
    assert cache.stats.size == 0


def test_embedding_cache_set_custom_ttl(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path, default_ttl=86400)
    cache.set(
        "ttl-test", "m", [0.5], provider="p", base_url="http://x", ttl_seconds=42
    )
    key = cache._compute_key("ttl-test", "m", provider="p", base_url="http://x")
    entry = cache._memory_cache[key]
    assert entry.ttl_seconds == 42


# ---------------------------------------------------------------------------
# EmbeddingCache.clear
# ---------------------------------------------------------------------------


def test_embedding_cache_clear_removes_memory_and_disk(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path)
    cache.set("a", "m", [0.0], provider="p", base_url="http://x")
    cache.set("b", "m", [0.1], provider="p", base_url="http://x")
    count = cache.clear()
    assert count == 2
    assert cache._memory_cache == {}
    assert list(tmp_path.glob("*.json")) == []


def test_embedding_cache_clear_handles_unlink_errors(tmp_path: Path) -> None:
    """Files that can't be unlinked are silently skipped (no crash)."""
    cache = EmbeddingCache(cache_root=tmp_path)
    cache.set("a", "m", [0.0], provider="p", base_url="http://x")
    # Patch Path.unlink to fail — clear() must still complete.
    with patch.object(Path, "unlink", side_effect=OSError("locked")):
        count = cache.clear()
    # Files weren't actually unlinked, but clear() returned 0 without raising.
    assert count == 0


# ---------------------------------------------------------------------------
# EmbeddingCache.get_stats
# ---------------------------------------------------------------------------


def test_embedding_cache_get_stats_returns_stats_object(tmp_path: Path) -> None:
    cache = EmbeddingCache(cache_root=tmp_path)
    cache.set("a", "m", [0.0], provider="p", base_url="http://x")
    cache.get("a", "m", provider="p", base_url="http://x")  # hit
    cache.get("absent", "m", provider="p", base_url="http://x")  # miss
    stats = cache.get_stats()
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.size == 1


# ---------------------------------------------------------------------------
# EmbeddingCache — TTL enforcement (live)
# ---------------------------------------------------------------------------


def test_embedding_cache_ttl_zero_is_immediate_expiry(tmp_path: Path) -> None:
    """TTL=0 + tiny sleep produces an expired entry on second get()."""
    cache = EmbeddingCache(cache_root=tmp_path, default_ttl=0)
    cache.set("a", "m", [0.5], provider="p", base_url="http://x", ttl_seconds=0)
    # Sleep a hair so the expiry strictly trips (time.time() > created_at + 0).
    time.sleep(0.01)
    out = cache.get("a", "m", provider="p", base_url="http://x")
    assert out is None
