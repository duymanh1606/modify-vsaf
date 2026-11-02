"""LLM response caching with content hashing."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


def _default_cache_root() -> Path:
    """Resolve default cache root: VDS_CACHE_ROOT env var, then ~/.vds/cache/llm."""
    env = os.environ.get("VDS_CACHE_ROOT")
    if env:
        return Path(env) / "llm"
    return Path.home() / ".vds" / "cache" / "llm"


class CacheEntry(BaseModel):
    """Cached LLM response entry."""

    key: str
    response: str
    model: str
    created_at: float
    ttl_seconds: int
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > (self.created_at + self.ttl_seconds)


class CacheStats(BaseModel):
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    size: int = 0
    saved_tokens: int = 0
    saved_cost: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class LLMResponseCache:
    """Cache for LLM responses with content-based hashing."""

    # Cost per 1M tokens (approximate)
    COST_PER_1M_TOKENS = 3.00

    def __init__(
        self,
        cache_root: Path | str | None = None,
        metrics_callback: Callable[[str], Any] | None = None,
        default_ttl: int = 86400,  # 24 hours
        max_size: int = 1000,
    ):
        if cache_root is not None:
            self.cache_dir = Path(cache_root)
        else:
            self.cache_dir = _default_cache_root()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._metrics_callback = metrics_callback
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.stats = CacheStats()
        self._memory_cache: dict[str, CacheEntry] = {}

    def _compute_key(self, prompt: str, model: str, context: dict[str, Any] | None = None) -> str:
        """Compute cache key from prompt, model, and optional context."""
        if context is not None:
            content = f"{model}:{prompt}:{json.dumps(context, sort_keys=True, default=str)}"
        else:
            content = f"{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{key}.json"

    def _record_hit(self) -> None:
        """Invoke metrics callback on cache hit."""
        if self._metrics_callback:
            self._metrics_callback("llm")

    def get(self, prompt: str, model: str, *, context: dict[str, Any] | None = None) -> CacheEntry | None:
        """Get cached response if available and not expired."""
        key = self._compute_key(prompt, model, context)

        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired:
                self.stats.hits += 1
                self.stats.saved_tokens += entry.input_tokens + entry.output_tokens
                self._record_hit()
                logger.debug("Cache hit (memory)", key=key[:8])
                return entry
            else:
                del self._memory_cache[key]

        # Check disk cache
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                entry = CacheEntry.model_validate(data)
                if not entry.is_expired:
                    self._memory_cache[key] = entry
                    self.stats.hits += 1
                    self.stats.saved_tokens += entry.input_tokens + entry.output_tokens
                    self._record_hit()
                    logger.debug("Cache hit (disk)", key=key[:8])
                    return entry
                else:
                    cache_path.unlink()  # Remove expired
            except Exception as e:
                logger.warning("Failed to read cache", key=key[:8], error=str(e))

        self.stats.misses += 1
        return None

    def set(
        self,
        prompt: str,
        model: str,
        response: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        ttl: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Cache a response."""
        key = self._compute_key(prompt, model, context)

        entry = CacheEntry(
            key=key,
            response=response,
            model=model,
            created_at=time.time(),
            ttl_seconds=ttl or self.default_ttl,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Store in memory
        self._memory_cache[key] = entry

        # Store on disk
        cache_path = self._get_cache_path(key)
        try:
            cache_path.write_text(entry.model_dump_json())
            self.stats.size += 1
            logger.debug("Cached response", key=key[:8], tokens=input_tokens + output_tokens)
        except Exception as e:
            logger.warning("Failed to write cache", key=key[:8], error=str(e))

    def clear(self) -> int:
        """Clear all cache entries. Returns count of cleared entries."""
        count = 0
        self._memory_cache.clear()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                pass

        self.stats = CacheStats()
        logger.info("Cache cleared", entries=count)
        return count

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self.stats.saved_cost = (self.stats.saved_tokens / 1_000_000) * self.COST_PER_1M_TOKENS
        return self.stats


class AnalysisCache:
    """Persistent cache for LLM analysis results."""

    def __init__(self, cache_dir: Path | None = None, ttl_hours: int = 24):
        self._cache = LLMResponseCache(
            cache_root=cache_dir,
            default_ttl=ttl_hours * 3600,
        )

    def _compute_key(self, content: str, context: dict[str, Any]) -> str:
        """Compute unique cache key based on content and context."""
        normalized_content = content.strip()
        payload = json.dumps({"content": normalized_content, "context": context}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def get(self, content: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """Retrieve cached analysis result."""
        key = self._compute_key(content, context)
        entry = self._cache.get(key, "analysis")
        if entry:
            try:
                return json.loads(entry.response)
            except Exception:
                return None
        return None

    def set(self, content: str, context: dict[str, Any], result: dict[str, Any] | BaseModel) -> None:
        """Store analysis result in cache."""
        key = self._compute_key(content, context)
        value = result.model_dump_json() if isinstance(result, BaseModel) else json.dumps(result)
        self._cache.set(key, "analysis", value)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        s = self._cache.get_stats()
        return {
            "size_bytes": 0,  # Not tracked in new implementation
            "count": s.size,
            "hits": s.hits,
            "misses": s.misses,
        }


# ---------------------------------------------------------------------------
# Embedding cache (Phase 225 Track-A)
# ---------------------------------------------------------------------------


def _default_embedding_cache_root() -> Path:
    """Resolve default embedding cache root."""
    env = os.environ.get("VDS_CACHE_ROOT")
    if env:
        return Path(env) / "embedding"
    return Path.home() / ".vds" / "cache" / "embedding"


class _EmbeddingCacheEntry(BaseModel):
    """Cached embedding vector entry."""

    key: str
    vector: list[float]
    model: str
    provider: str
    base_url: str
    created_at: float
    ttl_seconds: int

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)


class EmbeddingCache:
    """Cache for embedding vectors keyed by (provider, base_url, model, text).

    Keying by provider+base_url prevents cross-provider vector collisions —
    different providers produce different embedding spaces for the same text.
    """

    def __init__(
        self,
        cache_root: Path | str | None = None,
        default_ttl: int = 86400,
    ) -> None:
        self.cache_dir = Path(cache_root) if cache_root else _default_embedding_cache_root()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self.stats = CacheStats()
        self._memory_cache: dict[str, _EmbeddingCacheEntry] = {}

    def _compute_key(
        self,
        text: str,
        model: str,
        *,
        provider: str,
        base_url: str,
    ) -> str:
        content = f"{provider}:{base_url}:{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _get_cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(
        self,
        text: str,
        model: str,
        *,
        provider: str,
        base_url: str,
    ) -> list[float] | None:
        key = self._compute_key(text, model, provider=provider, base_url=base_url)
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired:
                self.stats.hits += 1
                return entry.vector
            del self._memory_cache[key]
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text())
                entry = _EmbeddingCacheEntry.model_validate(data)
                if not entry.is_expired:
                    self._memory_cache[key] = entry
                    self.stats.hits += 1
                    return entry.vector
                cache_path.unlink()
            except Exception as e:
                logger.warning("Failed to read embedding cache", key=key[:8], error=str(e))
        self.stats.misses += 1
        return None

    def set(
        self,
        text: str,
        model: str,
        vector: list[float],
        *,
        provider: str,
        base_url: str,
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._compute_key(text, model, provider=provider, base_url=base_url)
        entry = _EmbeddingCacheEntry(
            key=key,
            vector=vector,
            model=model,
            provider=provider,
            base_url=base_url,
            created_at=time.time(),
            ttl_seconds=ttl_seconds or self.default_ttl,
        )
        self._memory_cache[key] = entry
        try:
            self._get_cache_path(key).write_text(entry.model_dump_json())
            self.stats.size += 1
        except Exception as e:
            logger.warning("Failed to write embedding cache", key=key[:8], error=str(e))

    def clear(self) -> int:
        count = 0
        self._memory_cache.clear()
        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
                count += 1
            except Exception:
                pass
        self.stats = CacheStats()
        return count

    def get_stats(self) -> CacheStats:
        return self.stats
