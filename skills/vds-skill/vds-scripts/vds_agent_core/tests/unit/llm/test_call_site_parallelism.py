"""Verify EmbeddingClient mirrors LLMClient call-site shape (NFR-225.6)."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from vds_agent_core.llm.embedding import EmbeddingClient, EmbeddingSettings
from vds_agent_core.llm.provider import LLMClient, LLMSettings


def test_protocol_methods_parallel() -> None:
    """LLMClient and EmbeddingClient share the same call-site shape."""
    assert hasattr(LLMClient, "chat")
    assert hasattr(EmbeddingClient, "embed")
    assert hasattr(EmbeddingClient, "embed_batch")
    assert hasattr(EmbeddingClient, "estimate_cost")
    assert hasattr(EmbeddingClient, "aclose")


def test_settings_subclass_basesettings() -> None:
    """Both Settings classes inherit BaseSettings (env-var driven)."""
    assert issubclass(LLMSettings, BaseSettings)
    assert issubclass(EmbeddingSettings, BaseSettings)


def test_settings_have_factory_and_select_model() -> None:
    """Both expose `build_client()` + `select_model()` for parity."""
    assert hasattr(LLMSettings, "build_client")
    assert hasattr(LLMSettings, "select_model")
    assert hasattr(EmbeddingSettings, "build_client")
    assert hasattr(EmbeddingSettings, "select_model")
