"""Provider auto-routing from model prefix (FR-225.19)."""

from __future__ import annotations

import pytest
from vds_agent_core.llm.embedding import (
    EmbeddingSettings,
    HashEmbeddingClient,
    OllamaEmbeddingClient,
    OpenAIEmbeddingClient,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "VDS_AGENT_CORE_EMBED__PROVIDER",
        "VDS_AGENT_CORE_EMBED__BASE_URL",
        "VDS_AGENT_CORE_EMBED__MODEL_STANDARD",
        "VDS_AGENT_CORE_EMBED__DIMENSION",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    "model_str,dim,expected_class",
    [
        ("ollama/bge-m3", 1024, OllamaEmbeddingClient),
        ("openai/text-embedding-3-small", 1536, OpenAIEmbeddingClient),
        ("cohere/embed-english-v3.0", 1024, OpenAIEmbeddingClient),
        ("hash/v1", 1024, HashEmbeddingClient),
    ],
)
def test_auto_route_from_model_prefix(
    model_str: str, dim: int, expected_class: type
) -> None:
    """No explicit provider set — routing comes from the model prefix."""
    settings = EmbeddingSettings.model_validate(
        {
            "base_url": "http://test.local:11434",
            "model_simple": model_str,
            "model_standard": model_str,
            "model_complex": model_str,
            "dimension": dim,
        }
    )
    client = settings.build_client()
    assert isinstance(client, expected_class)
