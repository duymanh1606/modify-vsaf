"""Runtime log cleanliness (NFR-225.10 CRITICAL).

No raw API keys / Bearer tokens in logs or raised exception messages.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from vds_agent_core.llm.embedding import (
    EmbeddingProviderError,
    EmbeddingRuntimeConfig,
    OpenAIEmbeddingClient,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "VDS_AGENT_CORE_EMBED__PROVIDER",
        "VDS_AGENT_CORE_EMBED__BASE_URL",
        "VDS_AGENT_CORE_EMBED__API_KEY",
        "VDS_AGENT_CORE_EMBED__MODEL_STANDARD",
    ]:
        monkeypatch.delenv(key, raising=False)


def _build_settings() -> EmbeddingRuntimeConfig:
    return EmbeddingRuntimeConfig(
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test-CONFIDENTIAL-12345",
        model_simple="text-embedding-3-small",
        model_standard="text-embedding-3-small",
        model_complex="text-embedding-3-small",
        dimension=1536,
    )


async def test_no_secrets_in_logs_or_exceptions_on_http_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg = _build_settings()

    # Forge an HTTPStatusError whose string repr leaks the bearer token
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = (
        '{"error":{"message":"invalid bearer token Bearer sk-test-CONFIDENTIAL-12345"}}'
    )

    leaky_msg = (
        "401 Unauthorized: Authorization: Bearer sk-test-CONFIDENTIAL-12345 invalid"
    )
    err = httpx.HTTPStatusError(leaky_msg, request=MagicMock(), response=mock_response)
    mock_response.raise_for_status = MagicMock(side_effect=err)

    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(return_value=mock_response)
    mock_async_client.aclose = AsyncMock()

    caplog.set_level(logging.DEBUG)

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        for _ in range(5):
            with pytest.raises(EmbeddingProviderError) as ei:
                await client.embed("hi", model="text-embedding-3-small")
            # Exception message must not contain raw key
            assert "sk-test-CONFIDENTIAL" not in str(ei.value)
            assert "Bearer sk-" not in str(ei.value)

    # All log records sanitized
    for record in caplog.records:
        msg = record.getMessage()
        full = str(record.__dict__)
        assert "sk-test-CONFIDENTIAL" not in msg
        assert "sk-test-CONFIDENTIAL" not in full
        assert "Bearer sk-" not in msg


async def test_no_secrets_in_logs_on_connect_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    cfg = _build_settings()

    leaky_msg = (
        "Connection refused while authenticating with Bearer sk-test-CONFIDENTIAL-12345"
    )
    mock_async_client = AsyncMock()
    mock_async_client.post = AsyncMock(side_effect=httpx.ConnectError(leaky_msg))
    mock_async_client.aclose = AsyncMock()

    caplog.set_level(logging.DEBUG)

    with patch("httpx.AsyncClient", return_value=mock_async_client):
        client = OpenAIEmbeddingClient.from_settings(cfg)
        for _ in range(5):
            with pytest.raises(EmbeddingProviderError) as ei:
                await client.embed("hi", model="text-embedding-3-small")
            assert "sk-test-CONFIDENTIAL" not in str(ei.value)
            assert "Bearer sk-" not in str(ei.value)

    for record in caplog.records:
        msg = record.getMessage()
        full = str(record.__dict__)
        assert "sk-test-CONFIDENTIAL" not in msg
        assert "sk-test-CONFIDENTIAL" not in full
