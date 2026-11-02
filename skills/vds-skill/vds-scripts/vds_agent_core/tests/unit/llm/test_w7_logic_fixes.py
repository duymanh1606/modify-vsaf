"""W7 v20.6.1 regression tests for the logic-agent BLOCKER + HIGH fixes.

Each test locks one specific fix from the W7 logic walkthrough so a future
refactor can't silently regress them. All tests mock httpx — no real network.
"""

from __future__ import annotations

import threading
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from vds_agent_core.llm.embedding import (
    _PROVIDER_REGISTRY_LOCK,
    EMBEDDING_PROVIDERS,
    ConfigError,
    EmbeddingProviderError,
    EmbeddingSettings,
    OllamaEmbeddingClient,
    _parse_provider_from_model,
    register_provider,
)


@pytest.fixture(autouse=True)
def _registry_snapshot():
    """Save/restore EMBEDDING_PROVIDERS so tests can register fakes safely."""
    snap = dict(EMBEDDING_PROVIDERS)
    yield
    EMBEDDING_PROVIDERS.clear()
    EMBEDDING_PROVIDERS.update(snap)


# ---------------------------------------------------------------------------
# W7 logic-B-1: empty embeddings array guard
# ---------------------------------------------------------------------------


class TestOllamaEmptyEmbeddingsGuard:
    """Ollama returning ``{"embeddings": []}`` MUST raise EmbeddingProviderError,
    NOT IndexError."""

    @pytest.mark.asyncio
    async def test_embed_empty_array_raises_provider_error(self) -> None:
        config = MagicMock()
        config.base_url = "http://localhost:11434"
        config.timeout_seconds = 30.0
        client = OllamaEmbeddingClient(config)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"embeddings": []})
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.aclose = AsyncMock()
        with pytest.raises(EmbeddingProviderError, match="empty embeddings array"):
            await client.embed("hi", model="bge-m3")
        await client.aclose()

    @pytest.mark.asyncio
    async def test_embed_missing_field_raises_provider_error(self) -> None:
        config = MagicMock()
        config.base_url = "http://localhost:11434"
        config.timeout_seconds = 30.0
        client = OllamaEmbeddingClient(config)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"other": "field"})
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.aclose = AsyncMock()
        with pytest.raises(EmbeddingProviderError, match="empty embeddings array"):
            await client.embed("hi", model="bge-m3")
        await client.aclose()

    @pytest.mark.asyncio
    async def test_embed_batch_missing_field_raises(self) -> None:
        config = MagicMock()
        config.base_url = "http://localhost:11434"
        config.timeout_seconds = 30.0
        client = OllamaEmbeddingClient(config)
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"data": []})
        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)
        client._client.aclose = AsyncMock()
        with pytest.raises(EmbeddingProviderError, match="missing embeddings field"):
            await client.embed_batch(["a", "b"], model="bge-m3")
        await client.aclose()


# ---------------------------------------------------------------------------
# W7 logic-B-3: register_provider lock
# ---------------------------------------------------------------------------


class TestRegisterProviderLock:
    """Concurrent ``register_provider`` calls must be serialized."""

    def test_lock_exists_and_is_lock_type(self) -> None:
        # The lock module attribute must exist and be a threading lock.
        assert _PROVIDER_REGISTRY_LOCK is not None
        # threading.Lock() returns a _thread.lock; check it has the lock contract.
        assert hasattr(_PROVIDER_REGISTRY_LOCK, "acquire")
        assert hasattr(_PROVIDER_REGISTRY_LOCK, "release")

    def test_concurrent_registrations_serialized(self) -> None:
        """Stress test: 50 threads racing on the same key + force=True."""
        results: list[bool] = []

        def factory(_c: object) -> object:
            return MagicMock()

        def worker() -> None:
            try:
                register_provider("racer", factory, force=True)
                results.append(True)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # All 50 should succeed (force=True). The key point is no
        # data-race-induced exceptions or partial state corruption.
        assert all(results)
        assert "racer" in EMBEDDING_PROVIDERS

    def test_collision_without_force_raises(self) -> None:
        register_provider("dup_key", lambda c: MagicMock(), force=True)
        with pytest.raises(ConfigError, match="already registered"):
            register_provider("dup_key", lambda c: MagicMock(), force=False)


# ---------------------------------------------------------------------------
# W7 logic-HIGH-2: leading-slash provider parse
# ---------------------------------------------------------------------------


class TestLeadingSlashProviderParse:
    """Leading slash typos must still resolve to the provider prefix."""

    @pytest.mark.parametrize(
        ("input_str", "expected"),
        [
            ("openai/text-embedding-3-small", "openai"),
            ("/openai/text-embedding-3-small", "openai"),  # W7 fix
            ("//openai/text-embedding-3-small", "openai"),  # double-slash also tolerated
            ("ollama/bge-m3", "ollama"),
            ("/ollama/bge-m3", "ollama"),  # W7 fix
            ("nokey", None),
            ("", None),
            ("/", None),
            ("//", None),
        ],
    )
    def test_parse_provider(self, input_str: str, expected: str | None) -> None:
        assert _parse_provider_from_model(input_str) == expected


# ---------------------------------------------------------------------------
# W7 logic-B-2: response body sanitization in OpenAI client
# ---------------------------------------------------------------------------


class TestOpenAIResponseBodySanitization:
    """When OpenAI returns 401 with the token echoed in JSON body, sanitize it."""

    @pytest.mark.asyncio
    async def test_response_body_token_redacted_in_error(self) -> None:
        from vds_agent_core.llm.embedding import OpenAIEmbeddingClient

        config = MagicMock()
        config.base_url = "https://api.openai.com/v1"
        config.timeout_seconds = 30.0
        config.api_key = "sk-test-CONFIDENTIAL-12345"
        config.dimension = 1536
        client = OpenAIEmbeddingClient(config, provider_name="openai")

        # Build a fake HTTPStatusError whose response.text contains the token.
        fake_request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
        fake_response = httpx.Response(
            401,
            request=fake_request,
            content=b'{"error": {"message": "Invalid API key sk-test-CONFIDENTIAL-12345"}}',
        )
        exc = httpx.HTTPStatusError("401 Unauthorized", request=fake_request, response=fake_response)

        client._client = MagicMock()
        client._client.post = AsyncMock(side_effect=exc)
        client._client.aclose = AsyncMock()

        with pytest.raises(EmbeddingProviderError) as exc_info:
            await client.embed("hello", model="text-embedding-3-small")
        # Token MUST NOT appear in the sanitized error message.
        assert "sk-test-CONFIDENTIAL-12345" not in exc_info.value.message
        assert "[REDACTED]" in exc_info.value.message
        await client.aclose()


# ---------------------------------------------------------------------------
# W7 dedup-D-3: OpenAI-compat factory dispatch
# ---------------------------------------------------------------------------


class TestOpenAICompatFactories:
    """Each OpenAI-compat provider key must dispatch to OpenAIEmbeddingClient
    with the correct ``provider_name`` discriminator."""

    @pytest.mark.parametrize("provider", ["cohere", "voyage", "mistral", "jina"])
    def test_factory_dispatch(self, provider: str, monkeypatch) -> None:
        # Use dimension that bypasses the matryoshka + first-deploy validators.
        # cohere/voyage/mistral/jina all have dimension=1024 in PROVIDER_DEFAULTS.
        settings = EmbeddingSettings(provider=provider, model_standard=f"{provider}/foo", dimension=1024)
        client = settings.build_client()
        assert client.provider_name == provider
