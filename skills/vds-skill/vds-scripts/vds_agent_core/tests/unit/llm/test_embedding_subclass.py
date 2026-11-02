"""Subclass discipline (NFR-225.6 LSP).

Audit / memory packages must be able to subclass `EmbeddingSettings` with
their own env_prefix and have everything still work.
"""

from __future__ import annotations

import pytest
from pydantic_settings import SettingsConfigDict
from vds_agent_core.config import VDS_BASE_SETTINGS_CONFIG
from vds_agent_core.llm.embedding import EmbeddingSettings, OllamaEmbeddingClient


class FakeAuditEmbedSettings(EmbeddingSettings):
    """Audit-flavored subclass with its own env namespace."""

    model_config = SettingsConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="VDS_AUDIT_EMBED__",
        **VDS_BASE_SETTINGS_CONFIG,
    )


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "VDS_AGENT_CORE_EMBED__PROVIDER",
        "VDS_AGENT_CORE_EMBED__BASE_URL",
        "VDS_AUDIT_EMBED__PROVIDER",
        "VDS_AUDIT_EMBED__BASE_URL",
        "VDS_AUDIT_EMBED__MODEL_STANDARD",
        "VDS_AUDIT_EMBED__DIMENSION",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_subclass_reads_its_own_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDS_AUDIT_EMBED__BASE_URL", "https://audit.example.com")
    s = FakeAuditEmbedSettings()
    assert s.base_url == "https://audit.example.com"


def test_subclass_build_client_works(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VDS_AUDIT_EMBED__PROVIDER", "ollama")
    monkeypatch.setenv("VDS_AUDIT_EMBED__BASE_URL", "http://test.local:11434")
    monkeypatch.setenv("VDS_AUDIT_EMBED__MODEL_STANDARD", "bge-m3")
    s = FakeAuditEmbedSettings()
    client = s.build_client()
    assert isinstance(client, OllamaEmbeddingClient)
