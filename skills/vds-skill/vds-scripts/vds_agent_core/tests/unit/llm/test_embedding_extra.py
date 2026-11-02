"""Edge-case coverage for vds_agent_core.llm.embedding (Phase 225 W7).

Targets uncovered branches in embedding.py: lazy-import paths, request-error
paths, sanitization edge cases, EmbeddingSettings.from_config dynamic
subclass, and the dimension-disabled warning.
"""

from __future__ import annotations

import logging
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import structlog
from vds_agent_core.llm import embedding as embedding_module
from vds_agent_core.llm.embedding import (
    PROVIDER_DEFAULTS,
    EmbeddingProviderError,
    EmbeddingRuntimeConfig,
    EmbeddingSettings,
    HashEmbeddingClient,
    LiteLLMEmbeddingClient,
    LocalEmbeddingClient,
    OllamaEmbeddingClient,
    OpenAIEmbeddingClient,
    _check_qdrant_collection_dim,
    _parse_provider_from_model,
    _sanitize_error,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_embed_env(monkeypatch: pytest.MonkeyPatch) -> None:
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


@pytest.fixture()
def configure_structlog_for_caplog() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


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


# ---------------------------------------------------------------------------
# _sanitize_error edge cases
# ---------------------------------------------------------------------------


def test_sanitize_error_empty_string_returns_empty() -> None:
    assert _sanitize_error("") == ""


def test_sanitize_error_no_secrets_passthrough() -> None:
    assert _sanitize_error("plain message") == "plain message"


def test_sanitize_error_multiple_token_formats_in_one_string() -> None:
    msg = "Bearer sk-AAA111 inner sk-BBB222 hf_CCC333 done"
    out = _sanitize_error(msg)
    # All three secret patterns redacted.
    assert "sk-AAA111" not in out
    assert "sk-BBB222" not in out
    assert "hf_CCC333" not in out
    assert out.count("[REDACTED]") >= 1


def test_sanitize_error_non_str_coerced() -> None:
    """Non-string inputs are coerced to str via the function's str() call."""

    class WithStr:
        def __str__(self) -> str:
            return "Bearer sk-coerced"

    out = _sanitize_error(WithStr())  # type: ignore[arg-type]
    assert "sk-coerced" not in out
    assert "[REDACTED]" in out


# ---------------------------------------------------------------------------
# _parse_provider_from_model edge cases
# ---------------------------------------------------------------------------


def test_parse_provider_empty_string_returns_none() -> None:
    assert _parse_provider_from_model("") is None


def test_parse_provider_no_slash_returns_none() -> None:
    assert _parse_provider_from_model("bge-m3") is None


def test_parse_provider_leading_slash_returns_none() -> None:
    assert _parse_provider_from_model("/foo") is None


def test_parse_provider_double_slash_takes_first_segment() -> None:
    assert _parse_provider_from_model("openai/sub/model") == "openai"


# ---------------------------------------------------------------------------
# _check_qdrant_collection_dim placeholder behavior
# ---------------------------------------------------------------------------


def test_check_qdrant_collection_dim_returns_none_in_w1() -> None:
    """Stub returns None until W4 wires it up — contract lock."""
    assert _check_qdrant_collection_dim() is None


# ---------------------------------------------------------------------------
# OllamaEmbeddingClient — request-error paths (connect refused, timeout)
# ---------------------------------------------------------------------------


async def test_ollama_embed_request_error_raises_provider_error() -> None:
    cfg = _ollama_settings()
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError) as ei:
            await client.embed("x", model="bge-m3")
    assert ei.value.status is None
    assert ei.value.provider == "ollama"


async def test_ollama_embed_batch_request_error_raises() -> None:
    cfg = _ollama_settings()
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError):
            await client.embed_batch(["a", "b"], model="bge-m3")


async def test_ollama_embed_batch_http_error_raises() -> None:
    cfg = _ollama_settings()
    mock_response = MagicMock()
    mock_response.status_code = 503
    err = httpx.HTTPStatusError("svc unavail", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = MagicMock(side_effect=err)
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OllamaEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError) as ei:
            await client.embed_batch(["x"], model="bge-m3")
    assert ei.value.status == 503


def test_ollama_estimate_cost_zero() -> None:
    cfg = _ollama_settings()
    client = OllamaEmbeddingClient.from_settings(cfg)
    assert client.estimate_cost("anything", model="bge-m3") == 0.0


# ---------------------------------------------------------------------------
# OpenAIEmbeddingClient — error paths + base_url fallback + aclose
# ---------------------------------------------------------------------------


async def test_openai_embed_request_error_raises() -> None:
    cfg = EmbeddingRuntimeConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError) as ei:
            await client.embed("text", model="text-embedding-3-small")
    assert ei.value.status is None
    assert ei.value.provider == "openai"


async def test_openai_embed_http_error_raises() -> None:
    cfg = EmbeddingRuntimeConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )
    mock_response = MagicMock()
    mock_response.status_code = 401
    err = httpx.HTTPStatusError("unauth", request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = MagicMock(side_effect=err)
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        with pytest.raises(EmbeddingProviderError) as ei:
            await client.embed("x", model="text-embedding-3-small")
    assert ei.value.status == 401


async def test_openai_resolved_base_url_falls_back_when_default_ollama() -> None:
    """If base_url == ollama default + provider is openai, fall back to OpenAI URL."""
    cfg = EmbeddingRuntimeConfig(
        provider="openai",
        base_url=PROVIDER_DEFAULTS["ollama"]["base_url"],
        api_key="sk-test",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": [{"embedding": [0.0] * 1536}]}
    mock_response.raise_for_status = MagicMock()
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        await client.embed("x", model="text-embedding-3-small")
    # The resolved URL must hit the OpenAI provider default, not ollama's.
    url = mock_async_client.post.call_args.args[0]
    assert "api.openai.com" in url


async def test_openai_resolved_base_url_unknown_provider_falls_back_to_openai() -> None:
    """Unknown provider with default ollama URL -> falls back to OpenAI default."""
    # Use the real ollama default base_url so the equality check inside
    # _resolved_base_url() trips the provider-default lookup branch.
    cfg = _ollama_settings(base_url=PROVIDER_DEFAULTS["ollama"]["base_url"])
    # Manually instantiate w/ an unknown provider_name to trigger
    # `provider_default or "https://api.openai.com/v1"` final-or branch.
    client = OpenAIEmbeddingClient.from_settings(cfg, provider_name="totally_unknown")
    resolved = client._resolved_base_url()
    assert resolved == "https://api.openai.com/v1"


async def test_openai_aclose_closes_underlying_client() -> None:
    cfg = EmbeddingRuntimeConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )
    mock_async_client = AsyncMock()
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        await client.aclose()
    mock_async_client.aclose.assert_awaited()


def test_openai_estimate_cost_unknown_model_uses_default_rate() -> None:
    cfg = EmbeddingRuntimeConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )
    client = OpenAIEmbeddingClient.from_settings(cfg)
    cost = client.estimate_cost("a" * 4000, model="unknown-model")
    # Default fallback rate 0.0001 / 1k tokens.
    assert cost > 0


# ---------------------------------------------------------------------------
# LiteLLMEmbeddingClient — lazy import + error paths
# ---------------------------------------------------------------------------


async def test_litellm_embed_raises_import_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    # Force the lazy `import litellm` to fail by removing the module name from
    # both `sys.modules` and the import system.
    monkeypatch.setitem(sys.modules, "litellm", None)
    with pytest.raises(ImportError, match="vds-agent-core\\[litellm\\]"):
        await client.embed("x", model="bge-m3")


async def test_litellm_embed_batch_raises_import_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    monkeypatch.setitem(sys.modules, "litellm", None)
    with pytest.raises(ImportError, match="vds-agent-core\\[litellm\\]"):
        await client.embed_batch(["x"], model="bge-m3")


async def test_litellm_embed_provider_error_when_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If litellm import succeeds but aembedding raises, wrap as ProviderError."""
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    fake_litellm = MagicMock()
    fake_litellm.aembedding = AsyncMock(side_effect=RuntimeError("rate limited"))
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    with pytest.raises(EmbeddingProviderError) as ei:
        await client.embed("x", model="bge-m3")
    assert ei.value.provider == "litellm"


async def test_litellm_embed_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    fake_litellm = MagicMock()
    fake_litellm.aembedding = AsyncMock(return_value={"data": [{"embedding": [1.0, 2.0]}]})
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    out = await client.embed("hi", model="x")
    assert out == [1.0, 2.0]


async def test_litellm_embed_batch_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    fake_litellm = MagicMock()
    fake_litellm.aembedding = AsyncMock(
        return_value={"data": [{"embedding": [1.0]}, {"embedding": [2.0]}]}
    )
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    out = await client.embed_batch(["a", "b"], model="x")
    assert out == [[1.0], [2.0]]


async def test_litellm_embed_batch_provider_error_when_call_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    fake_litellm = MagicMock()
    fake_litellm.aembedding = AsyncMock(side_effect=ValueError("bad shape"))
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    with pytest.raises(EmbeddingProviderError):
        await client.embed_batch(["x"], model="bge-m3")


def test_litellm_estimate_cost_zero() -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    assert client.estimate_cost("anything", model="m") == 0.0


async def test_litellm_aclose_returns_none() -> None:
    cfg = _ollama_settings(provider="hash")
    client = LiteLLMEmbeddingClient.from_settings(cfg)
    assert await client.aclose() is None


# ---------------------------------------------------------------------------
# LocalEmbeddingClient — lazy-import path + encode flow
# ---------------------------------------------------------------------------


async def test_local_embed_raises_import_error_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(ImportError, match="sentence-transformers"):
        await client.embed("x", model="BAAI/bge-m3")


async def test_local_embed_uses_lazy_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    fake_model = MagicMock()
    fake_model.encode = MagicMock(return_value=[0.1, 0.2, 0.3])
    fake_module = MagicMock()
    fake_module.SentenceTransformer = MagicMock(return_value=fake_model)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    out = await client.embed("hi", model="BAAI/bge-m3")
    assert out == [0.1, 0.2, 0.3]


async def test_local_embed_batch_uses_lazy_loaded_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    fake_model = MagicMock()
    fake_model.encode = MagicMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    fake_module = MagicMock()
    fake_module.SentenceTransformer = MagicMock(return_value=fake_model)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    out = await client.embed_batch(["a", "b"], model="BAAI/bge-m3")
    assert out == [[0.1, 0.2], [0.3, 0.4]]


async def test_local_embed_model_load_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model loaded once, then cached on subsequent embed() calls."""
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    fake_model = MagicMock()
    fake_model.encode = MagicMock(return_value=[0.0])
    constructor = MagicMock(return_value=fake_model)
    fake_module = MagicMock()
    fake_module.SentenceTransformer = constructor
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    await client.embed("x", model="m")
    await client.embed("y", model="m")
    # SentenceTransformer constructor invoked exactly once.
    constructor.assert_called_once()


def test_local_estimate_cost_zero() -> None:
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    assert client.estimate_cost("anything", model="m") == 0.0


async def test_local_aclose_resets_model() -> None:
    cfg = _ollama_settings(provider="hash")
    client = LocalEmbeddingClient.from_settings(cfg)
    client._model = MagicMock()  # pretend loaded
    await client.aclose()
    assert client._model is None


# ---------------------------------------------------------------------------
# HashEmbeddingClient — additional surfaces
# ---------------------------------------------------------------------------


def test_hash_estimate_cost_zero() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    assert client.estimate_cost("text", model="m") == 0.0


async def test_hash_aclose_returns_none() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    assert await client.aclose() is None


async def test_hash_embed_batch_empty_list() -> None:
    cfg = _ollama_settings(provider="hash")
    client = HashEmbeddingClient.from_settings(cfg)
    out = await client.embed_batch([], model="m")
    assert out == []


async def test_hash_determinism_across_instances() -> None:
    """Same input + dim => same output, even from different instances."""
    cfg = _ollama_settings(provider="hash")
    c1 = HashEmbeddingClient.from_settings(cfg)
    c2 = HashEmbeddingClient.from_settings(cfg)
    v1 = await c1.embed("identical input", model="hash/v1")
    v2 = await c2.embed("identical input", model="hash/v1")
    assert v1 == v2


# ---------------------------------------------------------------------------
# EmbeddingSettings — dim-warning path + dynamic subclass
# ---------------------------------------------------------------------------


def test_embedding_settings_dim_warn_emits_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    configure_structlog_for_caplog: None,
) -> None:
    """verify_dim_against_qdrant=False emits a single warning (one-shot flag)."""
    monkeypatch.setattr(embedding_module, "_DIM_WARN_ISSUED", False)
    with caplog.at_level(logging.WARNING):
        EmbeddingSettings(
            provider="ollama",
            base_url="http://x",
            model_simple="bge-m3",
            model_standard="bge-m3",
            model_complex="bge-m3",
            dimension=1024,
            verify_dim_against_qdrant=False,
        )
        # Second instance should NOT re-emit (one-shot).
        EmbeddingSettings(
            provider="ollama",
            base_url="http://x",
            model_simple="bge-m3",
            model_standard="bge-m3",
            model_complex="bge-m3",
            dimension=1024,
            verify_dim_against_qdrant=False,
        )
    events = [
        rec.getMessage()
        for rec in caplog.records
        if "dimension_verification_disabled" in rec.getMessage()
    ]
    assert len(events) == 1


def test_embedding_settings_select_model_unknown_tier_returns_standard() -> None:
    settings = EmbeddingSettings(
        provider="ollama",
        base_url="http://x",
        model_simple="simp",
        model_standard="std",
        model_complex="cmp",
        dimension=1024,
    )
    assert settings.select_model("unknown") == "std"
    assert settings.select_model("simple") == "simp"
    assert settings.select_model("complex") == "cmp"
    assert settings.select_model() == "std"


def test_embedding_settings_from_config_default_path() -> None:
    """from_config without env_prefix simply forwards overrides."""
    s = EmbeddingSettings.from_config(
        provider="ollama",
        base_url="http://x",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
    )
    assert isinstance(s, EmbeddingSettings)
    assert s.provider == "ollama"


def test_embedding_settings_from_config_dynamic_subclass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """from_config(env_prefix=...) creates a dynamic subclass with the new prefix."""
    monkeypatch.setenv("VDS_TEST_FOO__BASE_URL", "http://from-prefix.local:11434")
    s = EmbeddingSettings.from_config(env_prefix="VDS_TEST_FOO__")
    assert s.base_url == "http://from-prefix.local:11434"
    # Class name is dynamically generated.
    assert "DynamicEmbeddingSettings" in type(s).__name__


# ---------------------------------------------------------------------------
# build_client — explicit provider differs from prefix triggers warn
# ---------------------------------------------------------------------------


def test_build_client_explicit_vs_prefix_logs_warn(
    caplog: pytest.LogCaptureFixture,
    configure_structlog_for_caplog: None,
) -> None:
    """Explicit provider+model with mismatched prefix emits provider_model_mismatch warn."""
    s = EmbeddingSettings(
        provider="ollama",  # explicit
        base_url="http://x",
        model_simple="openai/text-embedding-3-small",  # prefix says openai
        model_standard="openai/text-embedding-3-small",
        model_complex="openai/text-embedding-3-small",
        dimension=1024,
    )
    with caplog.at_level(logging.WARNING):
        client = s.build_client()
    assert isinstance(client, OllamaEmbeddingClient)
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "provider_model_mismatch" in joined


def test_build_client_no_prefix_uses_explicit_provider() -> None:
    """No prefix on model + explicit provider -> uses explicit."""
    s = EmbeddingSettings(
        provider="ollama",
        base_url="http://x",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
    )
    client = s.build_client()
    assert isinstance(client, OllamaEmbeddingClient)


def test_build_client_default_only_path() -> None:
    """No env vars, no kwargs, no model prefix -> uses BaseSettings defaults."""
    # model_validate({}) builds an instance where ``provider`` is NOT explicit
    # (model_fields_set is empty) and model_standard is the default "bge-m3"
    # (no prefix). This trips the `else: provider = self.provider` branch.
    s = EmbeddingSettings.model_validate({})
    client = s.build_client()
    assert isinstance(client, OllamaEmbeddingClient)


def test_validate_dimensions_collection_mismatch_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the Qdrant probe returns a dim that differs, ConfigError fires (FR-225.16a)."""
    from pydantic import ValidationError
    from vds_agent_core.llm.embedding import ConfigError as EmbedConfigError

    monkeypatch.setattr(embedding_module, "_check_qdrant_collection_dim", lambda: 768)
    with pytest.raises((EmbedConfigError, ValidationError), match="Dimension mismatch"):
        EmbeddingRuntimeConfig(
            provider="ollama",
            base_url="http://x",
            model_simple="bge-m3",
            model_standard="bge-m3",
            model_complex="bge-m3",
            dimension=1024,  # mismatches probed 768
        )


# ---------------------------------------------------------------------------
# health_check — full exception tuple coverage
# ---------------------------------------------------------------------------


async def test_health_check_with_unknown_provider_does_not_crash_finally() -> None:
    """ConfigError at build_client() must not trip the finally aclose() guard."""
    s = EmbeddingSettings(
        provider="bad-xyz-unknown",
        base_url="http://x",
        model_simple="m",
        model_standard="m",
        model_complex="m",
        dimension=1024,
        fail_open=True,
    )
    # ConfigError surfaces; fail_open=True logs warning + continues.
    await s.health_check()  # must not raise SystemExit / UnboundLocalError


async def test_health_check_request_error_fail_fast() -> None:
    s = EmbeddingSettings(
        provider="ollama",
        base_url="http://test.local:11434",
        model_simple="bge-m3",
        model_standard="bge-m3",
        model_complex="bge-m3",
        dimension=1024,
        fail_open=False,
    )
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
    mock_async_client.aclose = AsyncMock()
    with patch("httpx.AsyncClient", return_value=mock_async_client):
        with pytest.raises(SystemExit):
            await s.health_check()
