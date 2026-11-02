"""Test isolation for vds_agent_core observability wiring.

Phase 3 wiring (TSK-P3-Theta) makes ``AgentTracer.__post_init__`` auto-register
a :class:`JsonlUsageExporter` whenever ``VDS_LLM_USAGE_JSONL_ENABLED`` is
unset or truthy. That default is correct for production but would have every
test that constructs an ``AgentTracer`` start writing to ``~/.vds/cache/``.

This conftest:

* **Disables** auto-registration globally for the test session by pinning
  ``VDS_LLM_USAGE_JSONL_ENABLED=false`` before any test imports the tracer.
* **Redirects** the JSONL cache directory to a per-session ``tmp_path`` via
  ``VDS_LLM_USAGE_DIR`` so even tests that explicitly opt-in stay sandboxed.
* Exposes a ``llm_usage_jsonl_dir`` fixture for tests that want a clean
  per-test directory plus the auto-register flag turned ON.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Pin the disable flag *before* anything imports vds_agent_core.observability.
# autouse=True at session scope is the standard way to do this — but that runs
# AFTER collection, by which time tracer modules may already be imported. The
# safest belt-and-braces approach is to also touch os.environ at module import
# time (i.e. now) so the import-time read in `_jsonl_auto_register_enabled`
# sees the disable.
os.environ.setdefault("VDS_LLM_USAGE_JSONL_ENABLED", "false")


@pytest.fixture(autouse=True)
def _isolate_llm_usage_env(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Force every test into a sandboxed JSONL cache directory.

    Even if a test forgets to disable the auto-register flag, writes will
    land in a ``tmp_path``-derived directory, never in ``~/.vds/cache/``.
    """
    sandbox = tmp_path_factory.mktemp("vds-llm-usage-sandbox")
    monkeypatch.setenv("VDS_LLM_USAGE_DIR", str(sandbox))
    monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", "false")


@pytest.fixture
def llm_usage_jsonl_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Per-test JSONL directory with auto-register turned ON.

    Returns the directory; tests can construct an ``AgentTracer`` and
    verify a JSONL file appears under it.
    """
    target = tmp_path / "llm-usage"
    monkeypatch.setenv("VDS_LLM_USAGE_DIR", str(target))
    monkeypatch.setenv("VDS_LLM_USAGE_JSONL_ENABLED", "true")
    return target
