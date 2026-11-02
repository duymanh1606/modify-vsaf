"""Tests for vds_agent_core.llm.embedding (Phase 225 Track-A)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError
from vds_agent_core.llm.embedding import (
    EMBEDDING_PROVIDERS,
    ConfigError,
    EmbeddingProviderError,
    EmbeddingRuntimeConfig,
    EmbeddingSettings,
    HashEmbeddingClient,
    OllamaEmbeddingClient,
    OpenAIEmbeddingClient,
    _sanitize_error,
    register_provider,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear embedding env vars to avoid bleed between tests."""
    for key in [
        "VDS_AGENT_CORE_EMBED__PROVIDER",
        "VDS_AGENT_CORE_EMBED__BASE_URL",
        "VDS_AGENT_CORE_EMBED__API_KEY",
        "VDS_AGENT_CORE_EMBED__MODEL_STANDARD",
        "VDS_AGENT_CORE_EMBED__MODEL_SIMPLE",
        "VDS_AGENT_CORE_EMBED__MODEL_COMPLEX",
        "VDS_AGENT_CORE_EMBED__DIMENSION",
        "VDS_AGENT_CORE_EMBED__FAIL_OPEN",
        "VDS_AGENT_CORE_EMBED__VERIFY_DIM_AGAINST_QDRANT",
    ]:
        monkeypatch.delenv(key, raising=False)


def _ollama_settings(**overrides: Any) -> EmbeddingRuntimeConfig:
    base = {
        "provider": "ollama",
        "base_url": "http://test.local:11434",
        "model_simple": "bge-m3",
        "model_standard": "bge-m3",
        "model_complex": "bge-m3",
        "dimension": 1024,
    }
    base.update(overrides)
    return EmbeddingRuntimeConfig(**base)


def _openai_settings(**overrides: Any) -> EmbeddingRuntimeConfig:
    base = {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test",
        "model_simple": "text-embedding-3-small",
        "model_standard": "text-embedding-3-small",
        "model_complex": "text-embedding-3-small",
        "dimension": 1536,
    }
    base.update(overrides)
    return EmbeddingRuntimeConfig(**base)


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def test_sanitize_redacts_bearer() -> None:
    s = _sanitize_error("Authorization: Bearer sk-abc123secret")
    assert "sk-abc" not in s
    assert "[REDACTED]" in s


def test_sanitize_redacts_sk_keys() -> None:
    s = _sanitize_error("error with key sk-test-CONFIDENTIAL-12345 inside")
    assert "CONFIDENTIAL" not in s
    assert "[REDACTED]" in s


def test_sanitize_redacts_hf_tokens() -> None:
    s = _sanitize_error("hf_AAAABBBBCCCCDDDD failed")
    assert "AAAABBBB" not in s


def test_sanitize_handles_none() -> None:
    assert _sanitize_error(None) == ""


# ---------------------------------------------------------------------------
# OllamaEmbeddingClient — mocked httpx
# ---------------------------------------------------------------------------


async def test_ollama_embed_returns_vector() -> None:
    cfg = _ollama_settings()

    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        vec = await client.embed("hello world", model="bge-m3")

    assert vec == [0.1, 0.2, 0.3]
    call = mock_async_client.post.call_args
    assert call.args[0].endswith("/api/embed")
    assert call.kwargs["json"] == {"model": "bge-m3", "input": "hello world"}


async def test_ollama_embed_batch_returns_matrix() -> None:
    cfg = _ollama_settings()

    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[1.0, 2.0], [3.0, 4.0]]}
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        out = await client.embed_batch(["a", "b"], model="bge-m3")

    assert out == [[1.0, 2.0], [3.0, 4.0]]
    call = mock_async_client.post.call_args
    assert call.kwargs["json"]["input"] == ["a", "b"]


async def test_ollama_embed_http_error_raises_provider_error() -> None:
    cfg = _ollama_settings()

    mock_response = MagicMock()
    mock_response.status_code = 500
    err = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = MagicMock(side_effect=err)

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError) as ei:
            await client.embed("hi", model="bge-m3")
    assert ei.value.status == 500
    assert ei.value.provider == "ollama"


# ---------------------------------------------------------------------------
# OpenAIEmbeddingClient — mocked httpx
# ---------------------------------------------------------------------------


async def test_openai_embed_includes_dimensions_and_auth() -> None:
    cfg = _openai_settings()

    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"embedding": [0.5] * 1536}]}
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        vec = await client.embed("hi", model="text-embedding-3-small")

    assert len(vec) == 1536
    call = mock_async_client.post.call_args
    payload = call.kwargs["json"]
    assert payload["dimensions"] == 1536
    assert payload["input"] == ["hi"]
    headers = call.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"


def test_openai_estimate_cost_uses_per_token_rate() -> None:
    cfg = _openai_settings()
    client = OpenAIEmbeddingClient.from_settings(cfg)
    cost = client.estimate_cost("a" * 4000, model="text-embedding-3-small")
    # ~1000 tokens * 0.00002 / 1000 = 0.00002
    assert cost > 0
    assert cost < 0.01


# ---------------------------------------------------------------------------
# HashEmbeddingClient — deterministic placeholder
# ---------------------------------------------------------------------------


async def test_hash_embed_deterministic() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    v1 = await client.embed("same text", model="hash/v1")
    v2 = await client.embed("same text", model="hash/v1")
    assert v1 == v2
    assert len(v1) == cfg.dimension


async def test_hash_embed_different_inputs_differ() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    v1 = await client.embed("alpha", model="hash/v1")
    v2 = await client.embed("beta", model="hash/v1")
    assert v1 != v2


async def test_hash_embed_batch() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    out = await client.embed_batch(["x", "y", "z"], model="hash/v1")
    assert len(out) == 3
    for v in out:
        assert len(v) == cfg.dimension


# ---------------------------------------------------------------------------
# EmbeddingRuntimeConfig validators
# ---------------------------------------------------------------------------


def test_matryoshka_mismatch_raises() -> None:
    # pydantic-settings wraps validator errors in ValidationError; the
    # ConfigError message is preserved in the ValidationError body.
    with pytest.raises((ConfigError, ValidationError), match="text-embedding-3-small"):
        EmbeddingRuntimeConfig(
            provider="openai",
            base_url="https://api.openai.com/v1",
            model_simple="text-embedding-3-small",
            model_standard="text-embedding-3-small",
            model_complex="text-embedding-3-small",
            dimension=1024,
        )


def test_first_deploy_dim_guard_raises_for_invalid_dim() -> None:
    with pytest.raises((ConfigError, ValidationError), match="invalid for provider 'cohere'"):
        EmbeddingRuntimeConfig(
            provider="cohere",
            base_url="https://api.cohere.ai/v1",
            model_simple="embed-english-v3.0",
            model_standard="embed-english-v3.0",
            model_complex="embed-english-v3.0",
            dimension=999,
        )


def test_first_deploy_dim_guard_accepts_provider_default() -> None:
    cfg = EmbeddingRuntimeConfig(
        provider="cohere",
        base_url="https://api.cohere.ai/v1",
        model_simple="embed-english-v3.0",
        model_standard="embed-english-v3.0",
        model_complex="embed-english-v3.0",
        dimension=1024,
    )
    assert cfg.dimension == 1024


# ---------------------------------------------------------------------------
# EmbeddingSettings.build_client — registry routing
# ---------------------------------------------------------------------------


def test_build_client_unknown_provider_raises() -> None:
    # Use hash provider keys but pretend "bad" — we must bypass validators
    # for unknown providers (no PROVIDER_DEFAULTS entry → expected=None →
    # first-deploy guard skips). Provider is supplied explicitly.
    settings = EmbeddingSettings(
        provider="bad-provider-xyz",
        base_url="http://x",
        model_simple="m",
        model_standard="m",
        model_complex="m",
        dimension=1024,
    )
    with pytest.raises(ConfigError, match=r"Unknown embedding provider: 'bad-provider-xyz'.*Registered:"):
        settings.build_client()


def _fake_factory(c: EmbeddingRuntimeConfig) -> HashEmbeddingClient:
    return HashEmbeddingClient.from_settings(c)


def _other_fake_factory(c: EmbeddingRuntimeConfig) -> HashEmbeddingClient:
    return HashEmbeddingClient.from_settings(c)


def test_register_provider_collision_fails_fast() -> None:
    name = "_dup_test_provider"
    register_provider(name, _fake_factory)
    try:
        with pytest.raises(ConfigError, match="already registered"):
            register_provider(name, _fake_factory)
    finally:
        EMBEDDING_PROVIDERS.pop(name, None)


def test_register_provider_force_overrides() -> None:
    name = "_dup_test_provider2"
    register_provider(name, _fake_factory)
    try:
        register_provider(name, _other_fake_factory, force=True)
        assert EMBEDDING_PROVIDERS[name] is _other_fake_factory
    finally:
        EMBEDDING_PROVIDERS.pop(name, None)


# ---------------------------------------------------------------------------
# Health check fail-fast / fail-open
# ---------------------------------------------------------------------------


async def test_health_check_fails_fast_on_connect_error() -> None:
    settings = EmbeddingSettings(
        provider="ollama",
        base_url="http://test.local:11434",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
        fail_open=False,
    )

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        with pytest.raises(SystemExit):
            await settings.health_check()


async def test_health_check_fail_open_does_not_exit() -> None:
    settings = EmbeddingSettings(
        provider="ollama",
        base_url="http://test.local:11434",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
        fail_open=True,
    )

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        # Must not raise / exit
        await settings.health_check()


async def test_health_check_dimension_mismatch_fails() -> None:
    settings = EmbeddingSettings(
        provider="ollama",
        base_url="http://test.local:11434",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
        fail_open=False,
    )

    # Return a 768-dim vector when 1024 is configured
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[0.0] * 768]}
    mock_response.raise_for_status = MagicMock()

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        with pytest.raises(SystemExit):
            await settings.health_check()
