"""Embedding client abstraction — Protocol + provider registry.

Phase 225 Track-A foundation. Provides a uniform `EmbeddingClient` Protocol
backed by a registry of provider factories (`EMBEDDING_PROVIDERS`) so new
providers can be wired in without modifying core agent_core source files
(per NFR-225.9 drop-in extensibility).

Boundary discipline:
    - All provider HTTP calls go through httpx.AsyncClient (mockable).
    - Error messages are sanitized (no secrets in logs).
    - No provider-specific env vars (`VDS_AGENT_CORE_EMBED__OLLAMA_*` etc.) —
      the namespace stays clean per NFR-225.8.
    - `for_agent()` lives in W2 (per-agent provider config) — not here.
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
from collections.abc import Callable
from threading import Lock
from typing import Any, Protocol, runtime_checkable

import httpx
import structlog
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vds_agent_core.config import VDS_BASE_SETTINGS_CONFIG
from vds_agent_core.security.credentials import sanitize_text

logger = structlog.get_logger(__name__)

# One-shot warn flag for NFR-225.11 (dim-verification disabled warning).
_DIM_WARN_ISSUED = False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigError(ValueError):
    """Raised when embedding configuration is invalid (FR-225.16)."""


class EmbeddingProviderError(Exception):
    """Raised when an embedding provider returns an error.

    `message` MUST already be sanitized (no raw API keys / Bearer tokens).
    """

    def __init__(self, status: int | None, provider: str, message: str) -> None:
        self.status = status
        self.provider = provider
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.provider}] HTTP {self.status}: {self.message}"


# ---------------------------------------------------------------------------
# Sanitization helper (NFR-225.10) — W7 v20.6.1 dedup-D-2 + logic-B-2/HIGH-1:
# canonical patterns live in vds_agent_core.security.credentials. This shim
# preserves the module-private name for backward compat with W1-W6 internal
# call sites (and the W6 test files that import _sanitize_error directly).
# ---------------------------------------------------------------------------


def _sanitize_error(msg: str | None) -> str:
    """Strip secrets from an error message before logging or re-raising.

    Delegates to ``vds_agent_core.security.credentials.sanitize_text``.
    The canonical patterns now also redact URL query params and JSON body
    credential fields (W7 logic-HIGH-1 + B-2 fix).
    """
    return sanitize_text(msg)


# ---------------------------------------------------------------------------
# Provider defaults (FR-225.20)
# ---------------------------------------------------------------------------


PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "ollama": {
        "model": "bge-m3",
        "dimension": 1024,
        "base_url": "http://host.docker.internal:11434",
    },
    "openai": {
        "model": "text-embedding-3-small",
        "dimension": 1536,
        "base_url": "https://api.openai.com/v1",
    },
    "cohere": {
        "model": "embed-english-v3.0",
        "dimension": 1024,
        "base_url": "https://api.cohere.ai/v1",
    },
    "voyage": {
        "model": "voyage-3",
        "dimension": 1024,
        "base_url": "https://api.voyageai.com/v1",
    },
    "mistral": {
        "model": "mistral-embed",
        "dimension": 1024,
        "base_url": "https://api.mistral.ai/v1",
    },
    "jina": {
        "model": "jina-embeddings-v3",
        "dimension": 1024,
        "base_url": "https://api.jina.ai/v1",
    },
    "local": {
        "model": "BAAI/bge-m3",
        "dimension": 1024,
        "base_url": None,
    },
    "hash": {},
    "litellm": {},
}


# ---------------------------------------------------------------------------
# Provider registry (FR-225.19, ADR-99)
# ---------------------------------------------------------------------------


# Populated at module bottom AFTER all client classes are defined.
EMBEDDING_PROVIDERS: dict[str, Callable[[EmbeddingRuntimeConfig], EmbeddingClient]] = {}

# W7 v20.6.1 logic-B-3 fix: serialize register/dispatch concurrent updates.
# Python dict assignment is GIL-atomic for individual ops, but the
# check-then-set pattern (line 152: ``if not force and name in dict``) needs
# atomicity across both operations to honor the conflict rule.
_PROVIDER_REGISTRY_LOCK = Lock()


def register_provider(
    name: str,
    factory: Callable[[EmbeddingRuntimeConfig], EmbeddingClient],
    *,
    force: bool = False,
) -> None:
    """Register a new embedding provider factory.

    Per ADR-99 H-3 conflict rule: collisions fail fast unless ``force=True``.
    W7 v20.6.1 logic-B-3 fix: check-then-set wrapped in
    ``_PROVIDER_REGISTRY_LOCK`` so two threads racing on the same key cannot
    both pass the conflict check.
    """
    with _PROVIDER_REGISTRY_LOCK:
        if not force and name in EMBEDDING_PROVIDERS:
            raise ConfigError(
                f"Provider {name!r} already registered. Pass force=True to override."
            )
        EMBEDDING_PROVIDERS[name] = factory


def _parse_provider_from_model(model_str: str) -> str | None:
    """Return provider prefix for ``provider/model`` strings, else ``None``.

    W7 v20.6.1 logic-HIGH-2 fix: tolerate a leading slash so an operator
    typo (``"/openai/text-embedding-3-small"``) still routes to ``openai``
    instead of silently falling back to the default provider.
    """
    if not model_str:
        return None
    cleaned = model_str.lstrip("/")
    if "/" not in cleaned:
        return None
    prefix, _, _ = cleaned.partition("/")
    return prefix or None


def _check_qdrant_collection_dim() -> int | None:
    """Return live Qdrant collection dimension, or None if unavailable.

    Stub for W1 — W4 wires this to a real Qdrant probe.
    """
    return None


def _compose_http_error(exc: httpx.HTTPStatusError) -> str:
    """Build the full sanitization input from an HTTPStatusError.

    W7 v20.6.1 logic-B-2 fix: the previous code passed only ``str(exc)`` to
    ``_sanitize_error``. ``str(exc)`` does NOT include the response body,
    which is where providers (notably OpenAI) sometimes echo the bearer
    token in their JSON error message. This helper concatenates the
    exception summary with ``exc.response.text`` so the sanitizer can
    redact tokens regardless of where they appear.
    """
    parts: list[str] = [str(exc)]
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            body = response.text
        except Exception:
            body = ""
        # Coerce body to str — under unittest.mock, ``response.text`` may be
        # a MagicMock attribute access result; only str values can join.
        if body and isinstance(body, str):
            parts.append(body)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingClient(Protocol):
    """Generic embedding client contract. All providers satisfy this."""

    async def embed(self, text: str, *, model: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]: ...

    def estimate_cost(self, text: str, *, model: str) -> float: ...

    async def aclose(self) -> None: ...


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


_COST_PER_1K_TOKENS: dict[str, float] = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "embed-english-v3.0": 0.0001,
    "voyage-3": 0.00012,
}


def _estimate_tokens(text: str) -> int:
    """Rough heuristic: ~4 chars per token, min 1."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Client implementations
# ---------------------------------------------------------------------------


class OllamaEmbeddingClient:
    """Local Ollama embedding client (default for VDS).

    Uses `/api/embed` (Ollama 0.2+ unified endpoint).
    """

    provider_name = "ollama"

    def __init__(self, config: EmbeddingRuntimeConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    @classmethod
    def from_settings(cls, config: EmbeddingRuntimeConfig) -> OllamaEmbeddingClient:
        return cls(config)

    async def embed(self, text: str, *, model: str) -> list[float]:
        url = f"{self._config.base_url.rstrip('/')}/api/embed"
        try:
            resp = await self._client.post(url, json={"model": model, "input": text})
            resp.raise_for_status()
            data = resp.json()
            # W7 v20.6.1 logic-B-1 fix: guard against empty embeddings arrays
            # (Ollama returning ``{"embeddings": []}`` previously crashed with
            # IndexError instead of a controlled provider error).
            embeddings = data.get("embeddings") or []
            if not embeddings:
                raise EmbeddingProviderError(
                    None, self.provider_name, "empty embeddings array from provider"
                )
            return list(embeddings[0])
        except httpx.HTTPStatusError as exc:
            msg = _sanitize_error(_compose_http_error(exc))
            logger.warning("ollama_embed_http_error", error=msg)
            raise EmbeddingProviderError(exc.response.status_code, self.provider_name, msg) from None
        except httpx.RequestError as exc:
            msg = _sanitize_error(str(exc))
            logger.warning("ollama_embed_request_error", error=msg)
            raise EmbeddingProviderError(None, self.provider_name, msg) from None

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]:
        url = f"{self._config.base_url.rstrip('/')}/api/embed"
        try:
            resp = await self._client.post(url, json={"model": model, "input": texts})
            resp.raise_for_status()
            data = resp.json()
            # W7 v20.6.1 logic-B-1 fix: empty list still allowed for batch
            # (caller may pass empty texts), but None is rejected.
            embeddings = data.get("embeddings")
            if embeddings is None:
                raise EmbeddingProviderError(
                    None, self.provider_name, "missing embeddings field from provider"
                )
            return [list(v) for v in embeddings]
        except httpx.HTTPStatusError as exc:
            msg = _sanitize_error(_compose_http_error(exc))
            logger.warning("ollama_embed_batch_http_error", error=msg)
            raise EmbeddingProviderError(exc.response.status_code, self.provider_name, msg) from None
        except httpx.RequestError as exc:
            msg = _sanitize_error(str(exc))
            logger.warning("ollama_embed_batch_request_error", error=msg)
            raise EmbeddingProviderError(None, self.provider_name, msg) from None

    def estimate_cost(self, text: str, *, model: str) -> float:
        return 0.0

    async def aclose(self) -> None:
        await self._client.aclose()


class OpenAIEmbeddingClient:
    """OpenAI-compatible embedding client.

    Used by openai/cohere/voyage/mistral/jina via `provider_name` discriminator.
    All these providers expose `/embeddings` with the OpenAI shape (matryoshka
    `dimensions` parameter is OpenAI-specific but harmlessly accepted by others
    where supported).
    """

    def __init__(self, config: EmbeddingRuntimeConfig, *, provider_name: str = "openai") -> None:
        self._config = config
        self.provider_name = provider_name
        self._client = httpx.AsyncClient(timeout=config.timeout_seconds)

    @classmethod
    def from_settings(
        cls,
        config: EmbeddingRuntimeConfig,
        *,
        provider_name: str = "openai",
    ) -> OpenAIEmbeddingClient:
        return cls(config, provider_name=provider_name)

    def _resolved_base_url(self) -> str:
        """If operator left default ollama base_url, fall back to provider default."""
        ollama_default = PROVIDER_DEFAULTS["ollama"]["base_url"]
        if self._config.base_url == ollama_default:
            provider_default = PROVIDER_DEFAULTS.get(self.provider_name, {}).get("base_url")
            return provider_default or "https://api.openai.com/v1"
        return self._config.base_url

    async def embed(self, text: str, *, model: str) -> list[float]:
        results = await self.embed_batch([text], model=model)
        return results[0]

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]:
        url = f"{self._resolved_base_url().rstrip('/')}/embeddings"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        payload: dict[str, Any] = {
            "model": model,
            "input": texts,
            "dimensions": self._config.dimension,
        }
        try:
            resp = await self._client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return [list(d["embedding"]) for d in data["data"]]
        except httpx.HTTPStatusError as exc:
            # W7 v20.6.1 logic-B-2 fix: include the response body so any
            # token echoed in the JSON error payload (e.g. OpenAI 401 saying
            # "invalid token sk-leak") is sanitized. ``_sanitize_error``
            # delegates to the canonical ``security.credentials.sanitize_text``
            # which now also redacts URL params and JSON body fields.
            msg = _sanitize_error(_compose_http_error(exc))
            logger.warning(
                "openai_compat_embed_http_error",
                provider=self.provider_name,
                error=msg,
            )
            raise EmbeddingProviderError(exc.response.status_code, self.provider_name, msg) from None
        except httpx.RequestError as exc:
            msg = _sanitize_error(str(exc))
            logger.warning(
                "openai_compat_embed_request_error",
                provider=self.provider_name,
                error=msg,
            )
            raise EmbeddingProviderError(None, self.provider_name, msg) from None

    def estimate_cost(self, text: str, *, model: str) -> float:
        # Strip provider/ prefix if present (e.g. "openai/text-embedding-3-small")
        bare_model = model.rsplit("/", maxsplit=1)[-1]
        rate = _COST_PER_1K_TOKENS.get(bare_model, 0.0001)
        tokens = _estimate_tokens(text)
        return rate * (tokens / 1000.0)

    async def aclose(self) -> None:
        await self._client.aclose()


class LiteLLMEmbeddingClient:
    """LiteLLM-backed embedding client (one of N supported backends).

    Lazy import of `litellm` — gives a clear error if the optional dep is
    absent. LiteLLM tracks cost on its own; estimate_cost() returns 0.0.
    """

    provider_name = "litellm"

    def __init__(self, config: EmbeddingRuntimeConfig) -> None:
        self._config = config

    @classmethod
    def from_settings(cls, config: EmbeddingRuntimeConfig) -> LiteLLMEmbeddingClient:
        return cls(config)

    async def embed(self, text: str, *, model: str) -> list[float]:
        try:
            import litellm
        except ImportError as e:
            raise ImportError(
                "Install vds-agent-core[litellm] for LiteLLM embedding support"
            ) from e
        try:
            resp = await litellm.aembedding(model=model, input=text)
            return list(resp["data"][0]["embedding"])
        except Exception as exc:
            msg = _sanitize_error(str(exc))
            logger.warning("litellm_embed_error", error=msg)
            raise EmbeddingProviderError(None, self.provider_name, msg) from None

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]:
        try:
            import litellm
        except ImportError as e:
            raise ImportError(
                "Install vds-agent-core[litellm] for LiteLLM embedding support"
            ) from e
        try:
            resp = await litellm.aembedding(model=model, input=texts)
            return [list(d["embedding"]) for d in resp["data"]]
        except Exception as exc:
            msg = _sanitize_error(str(exc))
            logger.warning("litellm_embed_batch_error", error=msg)
            raise EmbeddingProviderError(None, self.provider_name, msg) from None

    def estimate_cost(self, text: str, *, model: str) -> float:
        return 0.0

    async def aclose(self) -> None:
        return None


class LocalEmbeddingClient:
    """sentence-transformers-backed local embedding client.

    Lazy import + lazy model load — heavyweight torch deps stay opt-in.
    """

    provider_name = "local"

    def __init__(self, config: EmbeddingRuntimeConfig) -> None:
        self._config = config
        self._model: Any = None

    @classmethod
    def from_settings(cls, config: EmbeddingRuntimeConfig) -> LocalEmbeddingClient:
        return cls(config)

    def _get_model(self, model_name: str) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                raise ImportError(
                    "Install sentence-transformers for local embedding support "
                    "(pip install sentence-transformers)"
                ) from e
            self._model = SentenceTransformer(model_name)
        return self._model

    async def embed(self, text: str, *, model: str) -> list[float]:
        m = self._get_model(model)
        vec = await asyncio.to_thread(m.encode, text)
        # numpy → list
        return [float(x) for x in vec]

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]:
        m = self._get_model(model)
        arr = await asyncio.to_thread(m.encode, texts)
        return [[float(x) for x in row] for row in arr]

    def estimate_cost(self, text: str, *, model: str) -> float:
        return 0.0

    async def aclose(self) -> None:
        self._model = None


class HashEmbeddingClient:
    """Deterministic placeholder embedding for tests / fail-open.

    Generates a fixed-dimension vector via SHA-256 byte tiling. Same input
    → same output; useful for cache hits and structural test paths.
    """

    provider_name = "hash"

    def __init__(self, config: EmbeddingRuntimeConfig) -> None:
        self._config = config

    @classmethod
    def from_settings(cls, config: EmbeddingRuntimeConfig) -> HashEmbeddingClient:
        return cls(config)

    def _vector_for(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()  # 32 bytes
        dim = self._config.dimension
        out: list[float] = []
        for i in range(dim):
            b = digest[i % len(digest)]
            out.append((b - 128) / 128.0)
        return out

    async def embed(self, text: str, *, model: str) -> list[float]:
        return self._vector_for(text)

    async def embed_batch(self, texts: list[str], *, model: str) -> list[list[float]]:
        return [self._vector_for(t) for t in texts]

    def estimate_cost(self, text: str, *, model: str) -> float:
        return 0.0

    async def aclose(self) -> None:
        return None


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class EmbeddingRuntimeConfig(BaseSettings):
    """Embedding runtime configuration.

    env_prefix=`VDS_AGENT_CORE_EMBED__` — open-set provider string keeps the
    namespace clean (no per-provider env vars, NFR-225.8).

    Subclasses (audit, memory) override `model_config` with their own
    env_prefix to avoid stomping shared keys.
    """

    model_config = SettingsConfigDict(
        env_prefix="VDS_AGENT_CORE_EMBED__",
        **VDS_BASE_SETTINGS_CONFIG,
    )

    enabled: bool = True
    provider: str = "ollama"
    base_url: str = "http://host.docker.internal:11434"
    api_key: str | None = None
    model_simple: str = "bge-m3"
    model_standard: str = "bge-m3"
    model_complex: str = "bge-m3"
    dimension: int = Field(default=1024, gt=0)
    cache_ttl_seconds: int = 86400
    fail_open: bool = False
    timeout_seconds: float = 30.0
    verify_dim_against_qdrant: bool = True

    @model_validator(mode="after")
    def _validate_dimensions(self) -> EmbeddingRuntimeConfig:
        # (a) Dim stability vs live Qdrant collection (FR-225.16a)
        if self.verify_dim_against_qdrant:
            collection_dim = _check_qdrant_collection_dim()
            if collection_dim is not None and collection_dim != self.dimension:
                raise ConfigError(
                    f"Dimension mismatch: collection={collection_dim}, "
                    f"requested={self.dimension}. Run migration first."
                )

        # (b) OpenAI matryoshka safety (FR-225.16b)
        if (
            self.provider == "openai"
            and self.model_standard.endswith("text-embedding-3-small")
            and self.dimension != 1536
        ):
            raise ConfigError(
                "text-embedding-3-small does not support dimension truncation; "
                "native dim is 1536. Use text-embedding-3-large for matryoshka, "
                "or set DIMENSION=1536."
            )

        # (c) First-deploy guard (FR-225.16c, v20.6.1 H-6).
        # If `provider` was left default but model prefix names a different
        # provider, use the prefix-derived provider for this check — the
        # auto-route resolution will use the prefix at build_client() time,
        # so we must validate against the same provider the client will use.
        explicit_provider = "provider" in self.model_fields_set
        prefix_provider = _parse_provider_from_model(self.model_standard)
        check_provider = self.provider
        if not explicit_provider and prefix_provider and prefix_provider in PROVIDER_DEFAULTS:
            check_provider = prefix_provider

        expected = PROVIDER_DEFAULTS.get(check_provider, {}).get("dimension")
        if expected is not None and self.dimension not in (expected, 1024):
            raise ConfigError(
                f"Dimension {self.dimension} invalid for provider "
                f"{check_provider!r}; expected {expected} or 1024"
            )

        return self


class EmbeddingSettings(EmbeddingRuntimeConfig):
    """Config-backed factory for EmbeddingClient instances.

    Build a client via `build_client()`. For health probes (FR-225.14), call
    `await settings.health_check()` at boot.
    """

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        global _DIM_WARN_ISSUED
        if not self.verify_dim_against_qdrant and not _DIM_WARN_ISSUED:
            _DIM_WARN_ISSUED = True
            logger.warning(
                "dimension_verification_disabled",
                message=(
                    "Dimension verification against Qdrant is DISABLED. "
                    "Switching embedding models without running migration "
                    "may corrupt the collection."
                ),
            )

    @classmethod
    def for_agent(
        cls,
        agent_id: str,
        *,
        profile: str | None = None,
        api_settings: Any = None,
        overrides: dict[str, Any] | None = None,
    ) -> EmbeddingSettings:
        """Build per-agent embedding settings via the 3-layer cascade (FR-226.2).

        Mirrors :meth:`vds_agent_core.llm.provider.LLMSettings.for_agent`. Reads
        Path A from ``VDS_AGENT_<AGENT_ID>_EMBED__*`` env vars and Path B from
        ``api_settings.embedding_settings``. Path B wins on conflict; the
        construction is side-effect-free (FR-226.11).
        """
        from vds_agent_core.llm._cascade import resolve_for_agent

        return resolve_for_agent(
            cls,
            agent_id,
            kind="embedding",
            env_prefix_template="VDS_AGENT_{sanitized}_EMBED__",
            api_attr="embedding_settings",
            profile=profile,
            api_settings=api_settings,
            overrides=overrides,
        )

    def select_model(self, tier: str = "standard") -> str:
        models = {
            "simple": self.model_simple,
            "standard": self.model_standard,
            "complex": self.model_complex,
        }
        return models.get(tier, self.model_standard)

    def build_client(self) -> EmbeddingClient:
        """Build an EmbeddingClient per FR-225.6 explicit-vs-defaulted resolution."""
        explicit_provider = "provider" in self.model_fields_set
        prefix_provider = _parse_provider_from_model(self.model_standard)

        if explicit_provider:
            provider = self.provider
            if prefix_provider and prefix_provider != provider:
                logger.warning(
                    "provider_model_mismatch",
                    provider=provider,
                    model=self.model_standard,
                    message=(
                        f"Explicit provider={provider!r} differs from model "
                        f"prefix {prefix_provider!r}"
                    ),
                )
        elif prefix_provider:
            provider = prefix_provider
        else:
            provider = self.provider  # default "ollama"

        factory = EMBEDDING_PROVIDERS.get(provider)
        if factory is None:
            raise ConfigError(
                f"Unknown embedding provider: {provider!r}. "
                f"Registered: {sorted(EMBEDDING_PROVIDERS)}"
            )
        return factory(self)

    @classmethod
    def from_config(
        cls,
        *,
        env_prefix: str | None = None,
        **overrides: Any,
    ) -> EmbeddingSettings:
        """Construct settings, optionally overriding env_prefix.

        For per-package env namespacing, prefer subclassing with a custom
        `model_config`. This shorthand simply forwards overrides.
        """
        if env_prefix is not None:
            new_config = SettingsConfigDict(
                env_prefix=env_prefix,
                **VDS_BASE_SETTINGS_CONFIG,
            )
            subcls = type(
                f"_DynamicEmbeddingSettings_{env_prefix.strip('_')}",
                (cls,),
                {"model_config": new_config},
            )
            return subcls(**overrides)
        return cls(**overrides)

    async def health_check(self) -> None:
        """Probe the configured provider at boot (FR-225.14, R-225.8).

        On success: silent.
        On failure with fail_open=False: log error and sys.exit(1).
        On failure with fail_open=True: log warning and continue.

        HIGH-2 (W6 v20.6.1 fix): ``client`` is bound to ``None`` BEFORE the
        ``try:`` so a ``ConfigError`` from ``build_client()`` (e.g. unknown
        provider) does not trigger ``UnboundLocalError`` in the ``finally``.
        The ``finally`` now guards the ``aclose()`` against an uninitialized
        client.
        """
        client: EmbeddingClient | None = None
        try:
            client = self.build_client()
            vector = await client.embed(
                "health-probe",
                model=self.select_model("standard"),
            )
            if len(vector) != self.dimension:
                raise ConfigError(
                    f"Provider {self.provider!r} model "
                    f"{self.select_model('standard')!r} returned "
                    f"{len(vector)} dims; expected {self.dimension}"
                )
        except (httpx.RequestError, EmbeddingProviderError, ConfigError) as exc:
            if self.fail_open:
                logger.warning(
                    "embedding_health_check_failed_fallback_to_hash",
                    error=_sanitize_error(str(exc)),
                )
            else:
                logger.error(
                    "embedding_health_check_failed_fatal",
                    error=_sanitize_error(str(exc)),
                )
                sys.exit(1)
        finally:
            if client is not None:
                await client.aclose()


# ---------------------------------------------------------------------------
# Registry population (must come AFTER all client classes are defined)
# ---------------------------------------------------------------------------


# OpenAI-compatible providers all dispatch to OpenAIEmbeddingClient with a
# provider_name discriminator. W7 v20.6.1 dedup-D-3 fix: build the factory
# entries from a list (closure-bound provider_name) rather than four
# duplicated lambdas. Adding a new OpenAI-compat provider is now a one-line
# tuple extension.
_OPENAI_COMPAT_PROVIDERS: tuple[str, ...] = ("cohere", "voyage", "mistral", "jina")


def _make_openai_compat_factory(
    provider_name: str,
) -> Callable[[EmbeddingRuntimeConfig], EmbeddingClient]:
    """Bind ``provider_name`` into the factory closure.

    Defined as a top-level function (rather than a lambda inside a
    comprehension) so the closure semantics are explicit and the factory
    is repr-friendly during debugging.
    """

    def _factory(config: EmbeddingRuntimeConfig) -> EmbeddingClient:
        return OpenAIEmbeddingClient.from_settings(config, provider_name=provider_name)

    _factory.__name__ = f"_openai_compat_factory_{provider_name}"
    return _factory


EMBEDDING_PROVIDERS.update(
    {
        "ollama": OllamaEmbeddingClient.from_settings,
        "openai": OpenAIEmbeddingClient.from_settings,
        **{name: _make_openai_compat_factory(name) for name in _OPENAI_COMPAT_PROVIDERS},
        "litellm": LiteLLMEmbeddingClient.from_settings,
        "local": LocalEmbeddingClient.from_settings,
        "hash": HashEmbeddingClient.from_settings,
    }
)
