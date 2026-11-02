"""TDD tests for the JSONL exporter auto-wiring at AgentTracer construction.

TSK-P3-Theta (ecosystem-daily-report Phase 3, post-merge wiring).

The exporter has been a passive observer since Wave 0.2 — these tests assert
that the production wiring at ``AgentTracer.__post_init__`` actually closes
the loop, so a real LLM call ends up in
``~/.vds/cache/llm-usage/<UTC-date>.jsonl`` (or the redirected sandbox).

Test surface:

* Default-on: a tracer constructed with the env flag truthy auto-registers
  the exporter and ``record_llm_call`` produces a JSONL file.
* Opt-out: with the flag set to "false", no exporter is registered and no
  JSONL is written.
* Test isolation: the conftest's ``_isolate_llm_usage_env`` autouse fixture
  guarantees neither the user's HOME nor the project tree is touched.
* ``bootstrap_observability`` is the explicit Option-C alternative and works
  regardless of the env flag.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class TestAutoRegisterDefaultOn:
    """Auto-registration fires when the env flag is truthy."""

    def test_llm_call_writes_jsonl(self, llm_usage_jsonl_dir: Path) -> None:
        """End-to-end: tracer.record_llm_call → JSONL file appears.

        Uses the ``llm_usage_jsonl_dir`` fixture, which sets the auto-register
        flag to true and points the cache at ``tmp_path``. We disable OTel
        (``enabled=False``) so this test passes whether or not opentelemetry
        is installed — the JSONL path is independent of the OTel span path.
        """
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="wiring-test", enabled=False)
        # No explicit ``register_usage_observer`` call — the wiring should
        # have already happened in __post_init__.
        tracer.record_llm_call(
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            provider="openai",
            request_id="req_wired",
            timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
        )

        files = list(llm_usage_jsonl_dir.glob("*.jsonl"))
        assert files, f"expected JSONL file under {llm_usage_jsonl_dir}, got nothing"
        records = _read_jsonl(files[0])
        assert records, "expected at least one record"
        rec = records[0]
        assert rec["provider"] == "openai"
        assert rec["model"] == "gpt-4o"
        assert rec["prompt_tokens"] == 100
        assert rec["completion_tokens"] == 50
        assert rec["request_id"] == "req_wired"

    def test_unset_flag_treated_as_enabled(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An unset env var means production wants the wiring on."""
        from vds_agent_core.observability import AgentTracer

        target = tmp_path / "unset-default"
        monkeypatch.setenv("VDS_LLM_USAGE_DIR", str(target))
        monkeypatch.delenv("VDS_LLM_USAGE_JSONL_ENABLED", raising=False)

        tracer = AgentTracer(service_name="default-on", enabled=False)
        tracer.record_llm_call(
            model="m",
            prompt_tokens=1,
            completion_tokens=1,
            provider="p",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        assert any(target.glob("*.jsonl"))


class TestAutoRegisterOptOut:
    """Setting the flag to false disables auto-registration."""

    def test_disabled_flag_skips_wiring(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """No JSONL appears when ``VDS_LLM_USAGE_JSONL_ENABLED=false``."""
        from vds_agent_core.observability import AgentTracer

        target = tmp_path / "disabled"
        monkeypatch.setenv("VDS_LLM_USAGE_DIR", str(target))
        monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", "false")

        tracer = AgentTracer(service_name="opt-out", enabled=False)
        tracer.record_llm_call(
            model="m",
            prompt_tokens=1,
            completion_tokens=1,
            provider="p",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        # Either no directory at all, or no JSONL files in it.
        if target.exists():
            assert not list(target.glob("*.jsonl"))

    def test_truthy_variants_all_enable_wiring(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``true``, ``1``, ``yes``, ``on`` all enable; others disable."""
        from vds_agent_core.observability import AgentTracer

        for raw, enabled in [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("0", False),
            ("", False),
            ("nope", False),
        ]:
            target = tmp_path / f"flag-{raw or 'empty'}-{enabled}"
            monkeypatch.setenv("VDS_LLM_USAGE_DIR", str(target))
            monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", raw)

            tracer = AgentTracer(service_name=f"variant-{raw}", enabled=False)
            tracer.record_llm_call(
                model="m",
                prompt_tokens=1,
                completion_tokens=1,
                provider="p",
                request_id=f"r-{raw}-{enabled}",
                timestamp=datetime(2026, 4, 30, tzinfo=UTC),
            )
            files = list(target.glob("*.jsonl")) if target.exists() else []
            if enabled:
                assert files, f"expected JSONL for raw={raw!r} (enabled)"
            else:
                assert not files, f"expected NO JSONL for raw={raw!r} (disabled)"


class TestTestIsolation:
    """The conftest must keep tests away from the real cache directory."""

    def test_conftest_sandbox_redirects_default_dir(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Even if a test forgets to disable the flag, writes go to tmp_path."""
        # Re-enable wiring without setting an explicit base dir.
        # The conftest fixture already pinned VDS_LLM_USAGE_DIR to a sandbox.
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import (
            DEFAULT_BASE_DIR,
            ENV_BASE_DIR,
        )

        monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", "true")
        sandbox = Path(__import__("os").environ[ENV_BASE_DIR])
        # The sandbox must be set and must NOT be the real default.
        assert sandbox != DEFAULT_BASE_DIR
        assert "vds-llm-usage-sandbox" in str(sandbox)

        tracer = AgentTracer(service_name="iso", enabled=False)
        tracer.record_llm_call(
            model="m",
            prompt_tokens=1,
            completion_tokens=1,
            provider="p",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        assert any(sandbox.glob("*.jsonl"))

    def test_real_home_cache_untouched_when_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The default ``~/.vds/cache/llm-usage`` is never written by tests.

        Verified by snapshotting the directory listing before/after: the
        test run must NOT add a today-dated JSONL there.
        """
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.jsonl_exporter import DEFAULT_BASE_DIR

        # Conftest sets the flag to false; this test is the regression spot-check.
        monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", "false")

        before = set(DEFAULT_BASE_DIR.glob("*.jsonl")) if DEFAULT_BASE_DIR.exists() else set()
        tracer = AgentTracer(service_name="no-leak", enabled=False)
        tracer.record_llm_call(
            model="m",
            prompt_tokens=1,
            completion_tokens=1,
            provider="p",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        after = set(DEFAULT_BASE_DIR.glob("*.jsonl")) if DEFAULT_BASE_DIR.exists() else set()
        # No NEW file appeared. (Existing files from prior production runs
        # are tolerated — the assertion is "we didn't create anything".)
        assert after == before


class TestBootstrapHelper:
    """``bootstrap_observability`` is the explicit Option-C entry point."""

    def test_bootstrap_wires_explicit_base_dir(self, tmp_path: Path) -> None:
        """``bootstrap_observability`` honors an explicit base_dir override."""
        from vds_agent_core.observability import (
            AgentTracer,
            bootstrap_observability,
        )

        target = tmp_path / "explicit-bootstrap"
        # Even with the conftest's flag off, the explicit bootstrap fires.
        tracer = AgentTracer(service_name="bootstrap", enabled=False)
        unregister = bootstrap_observability(tracer, base_dir=target)
        try:
            tracer.record_llm_call(
                model="claude-sonnet-4-5",
                prompt_tokens=10,
                completion_tokens=20,
                provider="anthropic",
                request_id="boot",
                timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC),
            )
        finally:
            unregister()

        files = list(target.glob("*.jsonl"))
        assert files
        rec = _read_jsonl(files[0])[0]
        assert rec["provider"] == "anthropic"
        assert rec["request_id"] == "boot"

    def test_bootstrap_unregister_stops_writes(self, tmp_path: Path) -> None:
        """The unregister callable lets callers tear down cleanly."""
        from vds_agent_core.observability import (
            AgentTracer,
            bootstrap_observability,
        )

        target = tmp_path / "unreg"
        tracer = AgentTracer(service_name="unreg", enabled=False)
        unregister = bootstrap_observability(tracer, base_dir=target)
        unregister()

        tracer.record_llm_call(
            model="m",
            prompt_tokens=1,
            completion_tokens=1,
            provider="p",
            request_id="r",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        assert not (target.exists() and list(target.glob("*.jsonl")))


class TestModuleSingletonIntegration:
    """The decorator-singleton tracer also gets the wiring."""

    def test_module_tracer_singleton_writes_jsonl(
        self,
        llm_usage_jsonl_dir: Path,
    ) -> None:
        """``decorators._module_tracer()`` reuses the auto-wired tracer.

        Reset the singleton first so __post_init__ runs under the
        ``llm_usage_jsonl_dir`` fixture's env vars, not whatever the
        previous test had pinned.
        """
        from vds_agent_core.observability import decorators as dec_mod

        dec_mod._TRACER = None  # force re-construction under fresh env
        tracer = dec_mod._module_tracer()

        tracer.record_llm_call(
            model="m",
            prompt_tokens=2,
            completion_tokens=3,
            provider="p",
            request_id="singleton",
            timestamp=datetime(2026, 4, 30, tzinfo=UTC),
        )
        assert any(llm_usage_jsonl_dir.glob("*.jsonl"))

        # Cleanup: drop the auto-registered observer so the next test
        # sees a clean module state.
        dec_mod._TRACER = None
