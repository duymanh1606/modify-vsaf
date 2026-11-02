"""Drop-in provider extensibility (NFR-225.9).

A new provider can be registered via `register_provider()` without touching
agent_core source files.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from vds_agent_core.llm.embedding import (
    EMBEDDING_PROVIDERS,
    EmbeddingRuntimeConfig,
    EmbeddingSettings,
    HashEmbeddingClient,
    register_provider,
)


def _hash_factory(cfg: EmbeddingRuntimeConfig) -> HashEmbeddingClient:
    return HashEmbeddingClient.from_settings(cfg)


@pytest.fixture
def fake_provider() -> Iterator[None]:
    """Register + restore a fake 'my_fake' provider around each test."""
    name = "my_fake"
    saved = EMBEDDING_PROVIDERS.pop(name, None)
    try:
        register_provider(name, _hash_factory)
        yield
    finally:
        EMBEDDING_PROVIDERS.pop(name, None)
        if saved is not None:
            EMBEDDING_PROVIDERS[name] = saved


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "VDS_AGENT_CORE_EMBED__PROVIDER",
        "VDS_AGENT_CORE_EMBED__BASE_URL",
        "VDS_AGENT_CORE_EMBED__MODEL_STANDARD",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_drop_in_provider_routes_via_explicit_provider(fake_provider: None) -> None:
    settings = EmbeddingSettings(
        provider="my_fake",
        base_url="http://x",
        model_simple="my_fake/v1",
        model_standard="my_fake/v1",
        model_complex="my_fake/v1",
        dimension=1024,
    )
    client = settings.build_client()
    assert isinstance(client, HashEmbeddingClient)


def test_drop_in_provider_routes_via_model_prefix(fake_provider: None) -> None:
    # Don't set provider explicitly — let prefix routing pick it up
    # Default provider="ollama" sticks unless we set model prefix.
    settings = EmbeddingSettings.model_validate(
        {
            "base_url": "http://x",
            "model_simple": "my_fake/v1",
            "model_standard": "my_fake/v1",
            "model_complex": "my_fake/v1",
            "dimension": 1024,
        }
    )
    client = settings.build_client()
    assert isinstance(client, HashEmbeddingClient)
