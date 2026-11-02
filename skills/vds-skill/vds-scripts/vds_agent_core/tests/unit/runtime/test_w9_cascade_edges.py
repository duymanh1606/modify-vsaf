"""Phase 225 W9 broader-coverage — _cascade.py edge cases not yet locked.

The existing ``test_for_agent.py`` covers Path A alone, Path B-overrides-A
WARN, Path C precedence, and the one-shot resolution log. This file
widens coverage to:

* Path A ``api_settings=None`` AND env-var Path A both set → Path A wins.
* All three paths set the same value → no WARN, deterministic precedence.
* WARN log content shape (FR-226.7) — fields ``path_a_value``,
  ``path_b_value``, ``winner=path_b``, ``field`` all present, ``kind`` set.
* WARN does NOT fire when Path A is unset and only Path B is set.
* Multi-field conflict — every conflicting field emits its own WARN.
* Path A reads only the matching ``env_prefix`` (no leakage from other
  agents' env vars with similar prefixes).
* Path B with non-dict attribute is gracefully ignored.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from unittest.mock import patch

import pytest
import structlog
from vds_agent_core.llm._cascade import _reset_resolution_log, resolve_for_agent
from vds_agent_core.llm.embedding import EmbeddingSettings
from vds_agent_core.llm.provider import LLMSettings
from vds_agent_core.runtime.agent_id import reset_agent_id_registry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_per_agent_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same belt-and-suspenders cleanup as test_for_agent.py."""
    reset_agent_id_registry()
    _reset_resolution_log()
    for key in list(os.environ.keys()):
        if re.match(r"^VDS_AGENT_[A-Z0-9_]+_(LLM|EMBED)__", key):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("VDS_AGENT_CORE__LOG_RESOLUTION", raising=False)


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


class _FakeApi:
    """Stand-in for the multi_agent_orchestrator Agent model."""

    def __init__(
        self,
        *,
        llm_settings: dict[str, Any] | None = None,
        embedding_settings: dict[str, Any] | None = None,
    ) -> None:
        self.llm_settings = llm_settings
        self.embedding_settings = embedding_settings


# ---------------------------------------------------------------------------
# Combinatorial coverage — api_settings=None + env Path A set
# ---------------------------------------------------------------------------


class TestPathANoneApiSettings:
    """When ``api_settings`` is None and Path A env vars are set, the cascade
    must still resolve Path A's value (no implicit dependency on Path B
    being present)."""

    def test_llm_path_a_alone_resolves(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_AGENT_LONELY_A_LLM__MODEL_STANDARD", "gpt-4o-only-a")
        s = LLMSettings.for_agent("lonely-a", api_settings=None)
        assert s.model_standard == "gpt-4o-only-a"

    def test_llm_path_a_no_warn_emitted_without_path_b(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        """Path B absent → no for_agent_path_conflict event."""
        monkeypatch.setenv("VDS_AGENT_LONELY_NOWARN_LLM__MODEL_STANDARD", "from-a")
        with caplog.at_level(logging.WARNING):
            LLMSettings.for_agent("lonely-nowarn", api_settings=None)
        assert "for_agent_path_conflict" not in " ".join(
            rec.getMessage() for rec in caplog.records
        )

    def test_embedding_path_a_alone_resolves(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(
            "VDS_AGENT_LONELY_E_EMBED__BASE_URL", "http://lonely-e:11434"
        )
        s = EmbeddingSettings.for_agent("lonely-e", api_settings=None)
        assert s.base_url == "http://lonely-e:11434"


# ---------------------------------------------------------------------------
# Deterministic precedence — all three paths agree → C value, no WARN
# ---------------------------------------------------------------------------


class TestAllThreePathsAgree:
    """When env var, api_settings, and overrides all set the same field to
    the same value, no WARN fires (because Path A == Path B), and the final
    resolved value matches that shared value (Path C is the strongest writer
    but writes the same string)."""

    def test_all_agree_no_warn(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_TRIPLE_LLM__MODEL_STANDARD", "gpt-4o")
        api = _FakeApi(llm_settings={"model_standard": "gpt-4o"})
        with caplog.at_level(logging.WARNING):
            s = LLMSettings.for_agent(
                "triple",
                api_settings=api,
                overrides={"model_standard": "gpt-4o"},
            )
        assert s.model_standard == "gpt-4o"
        assert "for_agent_path_conflict" not in " ".join(
            rec.getMessage() for rec in caplog.records
        )

    def test_all_three_disagree_path_c_wins(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        """A ≠ B ≠ C → C is the final winner, but only A vs B emits the WARN
        (because the implementation diff-checks Path A against Path B before
        applying Path C)."""
        monkeypatch.setenv("VDS_AGENT_TRIPLE_DIFF_LLM__MODEL_STANDARD", "from-a")
        api = _FakeApi(llm_settings={"model_standard": "from-b"})
        with caplog.at_level(logging.WARNING):
            s = LLMSettings.for_agent(
                "triple-diff",
                api_settings=api,
                overrides={"model_standard": "from-c"},
            )
        assert s.model_standard == "from-c"
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        # The A-vs-B WARN must still fire.
        assert "for_agent_path_conflict" in joined
        assert "from-a" in joined
        assert "from-b" in joined
        # winner=path_b (the diff is computed on A vs B; C is applied after).
        assert "winner=path_b" in joined or "winner='path_b'" in joined


# ---------------------------------------------------------------------------
# WARN log shape — FR-226.7 contract
# ---------------------------------------------------------------------------


class TestWarnLogShape:
    def test_warn_includes_required_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_WARN_FIELDS_LLM__MODEL_STANDARD", "v-a")
        api = _FakeApi(llm_settings={"model_standard": "v-b"})
        with caplog.at_level(logging.WARNING):
            LLMSettings.for_agent("warn-fields", api_settings=api)
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "for_agent_path_conflict" in joined
        # FR-226.7: agent_id, kind, field, path_a_value, path_b_value, winner.
        assert "agent_id=warn-fields" in joined or "agent_id='warn-fields'" in joined
        assert "kind=llm" in joined or "kind='llm'" in joined
        assert "field=model_standard" in joined or "field='model_standard'" in joined
        assert "path_a_value=v-a" in joined or "path_a_value='v-a'" in joined
        assert "path_b_value=v-b" in joined or "path_b_value='v-b'" in joined

    def test_warn_kind_embedding_when_embedding_cascade(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv(
            "VDS_AGENT_WARN_KIND_EMBED__BASE_URL", "http://a:11434"
        )
        api = _FakeApi(embedding_settings={"base_url": "http://b:11434"})
        with caplog.at_level(logging.WARNING):
            EmbeddingSettings.for_agent("warn-kind", api_settings=api)
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "kind=embedding" in joined or "kind='embedding'" in joined


# ---------------------------------------------------------------------------
# Multi-field conflict — each conflicting field gets its own WARN
# ---------------------------------------------------------------------------


class TestMultipleFieldConflicts:
    def test_two_fields_conflict_emit_two_warns(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        configure_structlog_for_caplog: None,
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_MULTIWARN_LLM__MODEL_STANDARD", "model-a")
        monkeypatch.setenv("VDS_AGENT_MULTIWARN_LLM__BASE_URL", "http://a:9000/v1")
        api = _FakeApi(
            llm_settings={
                "model_standard": "model-b",
                "base_url": "http://b:9000/v1",
            }
        )
        with caplog.at_level(logging.WARNING):
            LLMSettings.for_agent("multiwarn", api_settings=api)
        # Count distinct conflict events.
        conflicts = [
            rec.getMessage()
            for rec in caplog.records
            if "for_agent_path_conflict" in rec.getMessage()
        ]
        assert len(conflicts) == 2, f"expected 2 WARNs, got {len(conflicts)}: {conflicts}"
        joined = " ".join(conflicts)
        assert "model_standard" in joined
        assert "base_url" in joined


# ---------------------------------------------------------------------------
# Path A env-prefix isolation — no cross-agent leakage
# ---------------------------------------------------------------------------


class TestPathAPrefixIsolation:
    def test_other_agents_env_vars_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Set env vars for OTHER agents — must not bleed into our resolution.
        monkeypatch.setenv("VDS_AGENT_OTHER_LLM__MODEL_STANDARD", "wrong-1")
        monkeypatch.setenv("VDS_AGENT_TARGET_LLM__MODEL_STANDARD", "right-target")
        monkeypatch.setenv("VDS_AGENT_TARGET_X_LLM__MODEL_STANDARD", "wrong-2")
        s = LLMSettings.for_agent("target")
        assert s.model_standard == "right-target"

    def test_kind_prefix_isolation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``LLM__`` prefix must not be confused with ``EMBED__`` prefix."""
        monkeypatch.setenv("VDS_AGENT_KIND_ISO_EMBED__BASE_URL", "http://embed:1")
        # No LLM prefix set for this agent → Path A empty for LLM.
        s = LLMSettings.for_agent("kind-iso")
        # base_url stays at the default (None) because the EMBED env var
        # belongs to the embedding cascade, not the LLM cascade.
        assert s.base_url is None


# ---------------------------------------------------------------------------
# Path B graceful handling
# ---------------------------------------------------------------------------


class TestPathBGracefulHandling:
    def test_api_settings_with_no_attr_ignored(self) -> None:
        """If api_settings has no ``llm_settings`` attribute, Path B is skipped."""

        class _Naked:
            pass

        # Should not raise; falls back to defaults.
        s = LLMSettings.for_agent("naked", api_settings=_Naked())
        assert isinstance(s, LLMSettings)

    def test_api_settings_with_none_attr_ignored(self) -> None:
        """``api_settings.llm_settings = None`` → Path B contributes nothing."""
        api = _FakeApi(llm_settings=None)
        s = LLMSettings.for_agent("none-attr", api_settings=api)
        assert s.model_standard == "gpt-4o-mini"  # default

    def test_api_settings_with_non_dict_attr_ignored(self) -> None:
        """``api_settings.llm_settings = "not a dict"`` → Path B skipped."""
        api = _FakeApi()
        api.llm_settings = "not a dict"  # type: ignore[assignment]
        # Cascade must not raise on non-dict; resolves to default.
        s = LLMSettings.for_agent("non-dict-attr", api_settings=api)
        assert isinstance(s, LLMSettings)

    def test_api_settings_unknown_field_dropped(self) -> None:
        """Path B keys that aren't model fields are silently dropped."""
        api = _FakeApi(llm_settings={"this_field_does_not_exist": "X"})
        s = LLMSettings.for_agent("unknown-key", api_settings=api)
        assert isinstance(s, LLMSettings)
        # The unknown key wasn't set as an attribute either.
        assert not hasattr(s, "this_field_does_not_exist")


# ---------------------------------------------------------------------------
# resolve_for_agent direct invocation — covers the function in isolation
# ---------------------------------------------------------------------------


class TestResolveForAgentDirect:
    """The ``resolve_for_agent`` function is the underlying cascade primitive;
    most tests go through ``LLMSettings.for_agent`` / ``EmbeddingSettings.for_agent``.
    Calling the primitive directly locks the function signature."""

    def test_overrides_unknown_keys_dropped(self) -> None:
        """Overrides containing keys absent from the model are silently
        dropped (defense-in-depth — the same logic Path B uses)."""
        s = resolve_for_agent(
            LLMSettings,
            "direct-1",
            kind="llm",
            env_prefix_template="VDS_AGENT_{sanitized}_LLM__",
            api_attr="llm_settings",
            api_settings=None,
            overrides={"model_standard": "gpt-4o", "this_does_not_exist": "x"},
        )
        assert s.model_standard == "gpt-4o"
        assert not hasattr(s, "this_does_not_exist")

    def test_no_overrides_no_api_no_env_returns_defaults(self) -> None:
        """Empty cascade returns the equivalent of ``cls()`` plus defaults."""
        s = resolve_for_agent(
            LLMSettings,
            "direct-defaults",
            kind="llm",
            env_prefix_template="VDS_AGENT_{sanitized}_LLM__",
            api_attr="llm_settings",
        )
        assert isinstance(s, LLMSettings)
        assert s.model_standard == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Side-effect-free under cascade with all paths populated
# ---------------------------------------------------------------------------


class TestSideEffectFreeUnderFullCascade:
    """FR-226.11 — settings construction must remain side-effect-free even
    when every path is populated (tests today only run with empty paths)."""

    def test_no_httpx_under_full_path_population(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("VDS_AGENT_FULL_SIDE_LLM__MODEL_STANDARD", "from-a")
        api = _FakeApi(llm_settings={"model_standard": "from-b"})
        with patch("httpx.AsyncClient") as mock_async_client:
            LLMSettings.for_agent(
                "full-side",
                api_settings=api,
                overrides={"model_standard": "from-c"},
            )
        mock_async_client.assert_not_called()
