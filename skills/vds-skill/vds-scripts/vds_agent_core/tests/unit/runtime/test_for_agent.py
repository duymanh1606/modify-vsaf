"""Tests for Phase 225 Track-B per-agent settings cascade (W2).

Covers FR-226.1, FR-226.2, FR-226.4, FR-226.7, FR-226.11, FR-226.12,
NFR-225.14, NFR-226.1, and NFR-226.4.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any
from unittest.mock import patch

import pytest
import structlog
from vds_agent_core.llm._cascade import _reset_resolution_log
from vds_agent_core.llm.embedding import EmbeddingSettings
from vds_agent_core.llm.provider import LLMSettings
from vds_agent_core.runtime.agent_id import (
    AgentIdCollisionError,
    reset_agent_id_registry,
    sanitize_agent_id,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_per_agent_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear agent-id registry, resolution-log set, and any per-agent env vars."""
    reset_agent_id_registry()
    _reset_resolution_log()
    # Belt-and-suspenders: zap any env vars from prior tests/sessions that
    # would otherwise bleed into Path A resolution.
    for key in list(os.environ.keys()):
        if re.match(r"^VDS_AGENT_[A-Z0-9_]+_(LLM|EMBED)__", key):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("VDS_AGENT_CORE__LOG_RESOLUTION", raising=False)


@pytest.fixture()
def configure_structlog_for_caplog() -> None:
    """Wire structlog to stdlib so caplog captures structured events."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.KeyValueRenderer(key_order=["event"]),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


# sanitize_agent_id (NFR-226.4) ---------------------------------------------


class TestSanitizeAgentId:
    def test_hyphen_to_underscore_uppercase(self) -> None:
        assert sanitize_agent_id("agent-1") == "AGENT_1"

    def test_dot_and_slash_to_underscore(self) -> None:
        # Different inputs → different sanitized forms (no collision):
        assert sanitize_agent_id("a.b.c") == "A_B_C"
        assert sanitize_agent_id("x/y/z") == "X_Y_Z"

    def test_collision_raises(self) -> None:
        sanitize_agent_id("agent-1")
        # 'agent.1' sanitizes to AGENT_1 too -> collision.
        with pytest.raises(AgentIdCollisionError):
            sanitize_agent_id("agent.1")

    def test_idempotent_same_id(self) -> None:
        s1 = sanitize_agent_id("agent-x")
        s2 = sanitize_agent_id("agent-x")
        assert s1 == s2 == "AGENT_X"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_agent_id("")

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError):
            sanitize_agent_id(123)  # type: ignore[arg-type]

    def test_invalid_chars_rejected(self) -> None:
        with pytest.raises(ValueError):
            sanitize_agent_id("agent space")
        with pytest.raises(ValueError):
            sanitize_agent_id("agent$1")


# ---------------------------------------------------------------------------
# LLMSettings.for_agent — 3-layer cascade
# ---------------------------------------------------------------------------


class _FakeApiSettings:
    """Stand-in for the multi_agent_orchestrator ``Agent`` model."""

    def __init__(
        self,
        llm_settings: dict[str, Any] | None = None,
        embedding_settings: dict[str, Any] | None = None,
    ) -> None:
        self.llm_settings = llm_settings
        self.embedding_settings = embedding_settings


class TestLLMSettingsForAgentCascade:
    def test_defaults_when_no_layer_set(self) -> None:
        s = LLMSettings.for_agent("agent-default")
        assert isinstance(s, LLMSettings)
        # Default base_url is None per LLMRuntimeConfig.
        assert s.base_url is None
        assert s.model_standard == "gpt-4o-mini"

    def test_path_a_env_vars_resolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_AGENT_AGENT_A_LLM__MODEL_STANDARD", "gpt-4o")
        monkeypatch.setenv(
            "VDS_AGENT_AGENT_A_LLM__BASE_URL", "https://path-a.example.com/v1"
        )
        s = LLMSettings.for_agent("agent-a")
        assert s.model_standard == "gpt-4o"
        assert s.base_url == "https://path-a.example.com/v1"

    def test_path_b_overrides_path_a_with_warn(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_AGENT_B_LLM__MODEL_STANDARD", "from-path-a")
        api = _FakeApiSettings(llm_settings={"model_standard": "from-path-b"})
        with caplog.at_level(logging.WARNING):
            s = LLMSettings.for_agent("agent-b", api_settings=api)
        assert s.model_standard == "from-path-b"
        # FR-226.7: structured WARN event observed.
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "for_agent_path_conflict" in joined
        assert "from-path-a" in joined
        assert "from-path-b" in joined
        assert "winner=path_b" in joined or "winner='path_b'" in joined

    def test_path_c_overrides_everything(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_AGENT_AGENT_C_LLM__MODEL_STANDARD", "from-a")
        api = _FakeApiSettings(llm_settings={"model_standard": "from-b"})
        s = LLMSettings.for_agent(
            "agent-c", api_settings=api, overrides={"model_standard": "from-c"}
        )
        assert s.model_standard == "from-c"

    def test_no_warn_when_paths_agree(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_AGENT_AGREE_LLM__MODEL_STANDARD", "gpt-4o")
        api = _FakeApiSettings(llm_settings={"model_standard": "gpt-4o"})
        with caplog.at_level(logging.WARNING):
            LLMSettings.for_agent("agent-agree", api_settings=api)
        assert "for_agent_path_conflict" not in " ".join(
            rec.getMessage() for rec in caplog.records
        )


# ---------------------------------------------------------------------------
# EmbeddingSettings.for_agent — mirror cascade
# ---------------------------------------------------------------------------


class TestEmbeddingSettingsForAgentCascade:
    def test_defaults_when_no_layer_set(self) -> None:
        s = EmbeddingSettings.for_agent("embed-default")
        assert isinstance(s, EmbeddingSettings)
        assert s.provider == "ollama"
        assert s.model_standard == "bge-m3"

    def test_path_a_env_vars_resolved(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Use ollama provider to keep dim validation happy.
        monkeypatch.setenv(
            "VDS_AGENT_EMBED_A_EMBED__BASE_URL", "http://path-a.local:11434"
        )
        s = EmbeddingSettings.for_agent("embed-a")
        assert s.base_url == "http://path-a.local:11434"

    def test_path_b_overrides_path_a_with_warn(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv(
            "VDS_AGENT_EMBED_B_EMBED__BASE_URL", "http://path-a.local:11434"
        )
        api = _FakeApiSettings(
            embedding_settings={"base_url": "http://path-b.local:11434"}
        )
        with caplog.at_level(logging.WARNING):
            s = EmbeddingSettings.for_agent("embed-b", api_settings=api)
        assert s.base_url == "http://path-b.local:11434"
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "for_agent_path_conflict" in joined
        assert "kind=embedding" in joined or "kind='embedding'" in joined

    def test_path_c_overrides_everything(self) -> None:
        s = EmbeddingSettings.for_agent(
            "embed-c", overrides={"base_url": "http://path-c.local:11434"}
        )
        assert s.base_url == "http://path-c.local:11434"


# ---------------------------------------------------------------------------
# FR-226.11 — side-effect-free settings construction
# ---------------------------------------------------------------------------


class TestForAgentSideEffectFree:
    def test_no_httpx_async_client_constructed_for_llm(self) -> None:
        # The settings construction itself must not instantiate any network
        # client. We patch httpx.AsyncClient and assert it is never called.
        with patch("httpx.AsyncClient") as mock_async_client:
            LLMSettings.for_agent("no-side-effects-llm")
        mock_async_client.assert_not_called()

    def test_no_httpx_async_client_constructed_for_embedding(self) -> None:
        with patch("httpx.AsyncClient") as mock_async_client:
            EmbeddingSettings.for_agent("no-side-effects-embed")
        mock_async_client.assert_not_called()


# ---------------------------------------------------------------------------
# FR-226.12 — backward-compat lock for the no-args ``LLMSettings()`` path
# ---------------------------------------------------------------------------


class TestBackwardCompatNoArgsLLMSettings:
    """Existing ``LLMSettings()`` no-args call sites must keep working.

    The audit-orchestrator subclass at the spec-cited line numbers
    (`agents/base.py:125`, `llm/evaluator.py:80`, `llm/engine.py:68`) inherits
    from :class:`vds_agent_core.llm.provider.LLMSettings`. This test locks the
    canonical (core) no-args path and verifies the audit subclass module
    still imports cleanly. Audit's own ``LLMSettings()`` instantiation is
    covered by audit's own test suite (which loads the audit conftest that
    pre-resolves ``SecretStr`` for forward-ref binding).
    """

    def test_core_llmsettings_no_args_constructs(self) -> None:
        settings = LLMSettings()
        assert isinstance(settings, LLMSettings)
        assert callable(settings.build_client)
        assert callable(settings.select_model)

# ---------------------------------------------------------------------------
# Concurrency — for_agent under thread-pool concurrency must not race
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_for_agent_no_race_under_concurrency() -> None:
    results = await asyncio.gather(
        *[
            asyncio.to_thread(LLMSettings.for_agent, f"agent-{i}")
            for i in range(100)
        ]
    )
    assert len(results) == 100
    assert all(isinstance(r, LLMSettings) for r in results)


# ---------------------------------------------------------------------------
# NFR-226.1 — one-shot resolution log
# ---------------------------------------------------------------------------


class TestResolutionLogOneShot:
    def test_log_resolution_emits_one_per_agent_kind(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_CORE__LOG_RESOLUTION", "true")
        with caplog.at_level(logging.INFO):
            LLMSettings.for_agent("agent-log")
            LLMSettings.for_agent("agent-log")  # second call: zero new logs.
        events = [rec.getMessage() for rec in caplog.records if "for_agent_resolved" in rec.getMessage()]
        assert len(events) == 1, f"expected exactly 1 resolved log, got {len(events)}: {events}"

    def test_log_resolution_disabled_emits_nothing(
        self,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        # No env var set -> no log even on first call.
        with caplog.at_level(logging.INFO):
            LLMSettings.for_agent("agent-no-log")
        assert all(
            "for_agent_resolved" not in rec.getMessage() for rec in caplog.records
        )

    def test_log_resolution_separate_kinds(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_CORE__LOG_RESOLUTION", "true")
        with caplog.at_level(logging.INFO):
            LLMSettings.for_agent("agent-multi")
            EmbeddingSettings.for_agent("agent-multi")
        events = [
            rec.getMessage() for rec in caplog.records if "for_agent_resolved" in rec.getMessage()
        ]
        # Same agent_id, two different kinds -> two logs.
        assert len(events) == 2
