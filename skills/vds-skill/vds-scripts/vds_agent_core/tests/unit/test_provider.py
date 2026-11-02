"""Tests for vds_agent_core.llm.provider."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel
from vds_agent_core.llm.provider import (
    HttpxDirectClient,
    LiteLLMClient,
    LLMSettings,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SampleSchema(BaseModel):
    answer: str
    score: float


# ---------------------------------------------------------------------------
# Protocol structural conformance
# ---------------------------------------------------------------------------


def test_litellm_client_satisfies_protocol() -> None:
    """LiteLLMClient structurally conforms to LLMClient Protocol."""
    client = LiteLLMClient()
    assert hasattr(client, "chat")
    assert hasattr(client, "chat_json")
    # Verify async callables
    assert inspect.iscoroutinefunction(client.chat)
    assert inspect.iscoroutinefunction(client.chat_json)


def test_httpx_client_satisfies_protocol() -> None:
    """HttpxDirectClient structurally conforms to LLMClient Protocol."""
    client = HttpxDirectClient()
    assert hasattr(client, "chat")
    assert hasattr(client, "chat_json")
    assert inspect.iscoroutinefunction(client.chat)
    assert inspect.iscoroutinefunction(client.chat_json)


# ---------------------------------------------------------------------------
# LLMSettings — instantiation and select_model
# ---------------------------------------------------------------------------


def test_llm_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLMSettings loads with sane defaults."""
    # Clear any env vars that might interfere
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)
    monkeypatch.delenv("VDS_AGENT_CORE__BASE_URL", raising=False)
    settings = LLMSettings()
    assert settings.model_standard == "gpt-4o-mini"
    assert settings.model_complex == "gpt-4o"


def test_select_model_tiers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)
    settings = LLMSettings()
    assert settings.select_model("simple") == settings.model_simple
    assert settings.select_model("standard") == settings.model_standard
    assert settings.select_model("complex") == settings.model_complex


def test_select_model_unknown_tier_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)
    settings = LLMSettings()
    assert settings.select_model("nonexistent") == settings.model_standard


# ---------------------------------------------------------------------------
# build_client — litellm available vs not
# ---------------------------------------------------------------------------


def test_build_client_returns_httpx_when_litellm_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)
    settings = LLMSettings(base_url="https://example.com/v1", api_key="test-key")

    with patch.dict("sys.modules", {"litellm": None}):
        # Force ImportError on litellm
        import builtins

        real_import = builtins.__import__

        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "litellm":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        client = settings.build_client()

    assert isinstance(client, HttpxDirectClient)
    assert client._base_url == "https://example.com/v1"
    assert client._api_key == "test-key"


def test_build_client_returns_litellm_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)
    settings = LLMSettings()

    mock_litellm = MagicMock()
    with patch.dict("sys.modules", {"litellm": mock_litellm}):
        client = settings.build_client()

    assert isinstance(client, LiteLLMClient)


# ---------------------------------------------------------------------------
# HttpxDirectClient.chat — mocked httpx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_httpx_chat_success() -> None:
    client = HttpxDirectClient(base_url="https://test.api/v1", api_key="sk-test")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from LLM"}}],
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await client.chat(
            [{"role": "user", "content": "hi"}],
            model="gpt-4o",
        )

    assert result == "Hello from LLM"
    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args
    assert "Bearer sk-test" in str(call_kwargs)


@pytest.mark.asyncio
async def test_httpx_chat_json_strips_fences() -> None:
    client = HttpxDirectClient()

    json_content = '```json\n{"answer": "yes", "score": 0.95}\n```'
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json_content}}],
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await client.chat_json(
            [{"role": "user", "content": "test"}],
            model="gpt-4o",
            schema=_SampleSchema,
        )

    assert isinstance(result, _SampleSchema)
    assert result.answer == "yes"
    assert result.score == 0.95


# ---------------------------------------------------------------------------
# HttpxDirectClient — no api_key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_httpx_chat_no_api_key() -> None:
    """When no api_key, Authorization header is omitted."""
    client = HttpxDirectClient(api_key=None)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}],
    }
    mock_response.raise_for_status = MagicMock()

    mock_http_client = AsyncMock()
    mock_http_client.post.return_value = mock_response
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        result = await client.chat(
            [{"role": "user", "content": "hi"}],
            model="gpt-4o",
        )

    assert result == "ok"
    call_args = mock_http_client.post.call_args
    headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# LiteLLMClient — ImportError on missing dep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_litellm_chat_raises_on_missing_dep(monkeypatch: pytest.MonkeyPatch) -> None:
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "litellm":
            raise ImportError("mocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    client = LiteLLMClient()
    with pytest.raises(ImportError, match="vds-agent-core\\[litellm\\]"):
        await client.chat([{"role": "user", "content": "hi"}], model="gpt-4o")


# ---------------------------------------------------------------------------
# LiteLLMClient — ImportError on chat_json missing dep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_litellm_chat_json_raises_on_missing_dep(monkeypatch: pytest.MonkeyPatch) -> None:
    """LiteLLMClient.chat_json raises ImportError when litellm not installed."""
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "litellm":
            raise ImportError("mocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    class _Schema(BaseModel):
        result: str

    client = LiteLLMClient()
    with pytest.raises(ImportError, match="vds-agent-core\\[litellm\\]"):
        await client.chat_json(
            [{"role": "user", "content": "hi"}],
            model="gpt-4o",
            schema=_Schema,
        )


# ---------------------------------------------------------------------------
# LLMSettings.build_pydantic_ai_model — ImportError on missing pydantic_ai
# ---------------------------------------------------------------------------


def test_build_pydantic_ai_model_raises_on_missing_pydantic_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_pydantic_ai_model raises ImportError when pydantic_ai.providers.litellm is absent."""
    import builtins

    real_import = builtins.__import__

    def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in ("pydantic_ai.providers.litellm", "pydantic_ai.models.openai"):
            raise ImportError("mocked pydantic_ai")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.delenv("VDS_AGENT_CORE__API_KEY", raising=False)

    settings = LLMSettings(api_key="test", base_url="http://localhost:4000")
    with pytest.raises(ImportError):
        settings.build_pydantic_ai_model()


# ---------------------------------------------------------------------------
# LiteLLMClient — successful chat (mocked litellm)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_litellm_chat_success_with_mock() -> None:
    """LiteLLMClient.chat returns content when litellm is available."""
    import types

    mock_litellm = types.ModuleType("litellm")

    async def fake_acompletion(**kwargs: Any) -> Any:
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "mocked response"
        return response

    mock_litellm.acompletion = fake_acompletion  # type: ignore[attr-defined]

    with patch.dict("sys.modules", {"litellm": mock_litellm}):
        client = LiteLLMClient()
        result = await client.chat([{"role": "user", "content": "hi"}], model="openai/gpt-4o")

    assert result == "mocked response"
