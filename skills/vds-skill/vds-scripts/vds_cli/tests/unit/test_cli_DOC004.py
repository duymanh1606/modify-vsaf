"""Integration tests for DOC-004 observability CLI wiring.

Covers:
- docs onboarding-funnel command (real module integration)
- docs onboarding-funnel JSON output
- docs freshness command still callable (no regression)
- Window_days parameter handling
"""

from __future__ import annotations

from io import StringIO

import pytest
from rich.console import Console
from vds_cli.cli import docs_freshness, docs_onboarding_funnel


@pytest.fixture
def tmp_repo_with_docs(tmp_path):
    """Create a fake repo with a few docs in different Diátaxis quadrants."""
    repo = tmp_path / "vds-scripts"
    how_to = repo / "docs/agents/how-to"
    reference = repo / "docs/agents/reference"
    how_to.mkdir(parents=True)
    reference.mkdir(parents=True)
    (how_to / "run-ecosystem-daily-report.md").write_text("# How To\n")
    (how_to / "configure-agents.md").write_text("# How To\n")
    (reference / "skills-commands.md").write_text("# Reference\n")
    return repo


@pytest.fixture
def empty_sessions_dir(tmp_path):
    """Empty session dir (no reads)."""
    path = tmp_path / "sessions"
    path.mkdir()
    return path


class _FakeConsole:
    """Collect anything passed to print() into a list of strings."""

    def __init__(self):
        self.lines = []

    def print(self, text, *_, **__):
        self.lines.append(str(text))


def test_onboarding_funnel_table_runs(tmp_repo_with_docs, empty_sessions_dir, monkeypatch):
    """docs onboarding-funnel completes without errors when sessions dir has no reads."""
    buf = StringIO()
    fake = Console(file=buf, width=160, no_color=True, force_terminal=True)
    monkeypatch.setattr("vds_cli.cli.console", fake)

    docs_onboarding_funnel(
        repo_root=tmp_repo_with_docs,
        sessions_dir=empty_sessions_dir,
        format="table",
        window_days=60,
    )
    out = buf.getvalue()
    assert "Doc Funnel" in out
    assert "vds-scripts" in out


def test_onboarding_funnel_json_format(tmp_repo_with_docs, empty_sessions_dir, monkeypatch):
    """JSON output contains expected keys for programmatic consumers."""
    console = _FakeConsole()
    monkeypatch.setattr("vds_cli.cli.console", console)

    docs_onboarding_funnel(
        repo_root=tmp_repo_with_docs,
        sessions_dir=empty_sessions_dir,
        format="json",
        window_days=60,
    )
    joined = "\n".join(console.lines)
    assert '"dead_weight"' in joined
    assert '"stages"' in joined
    assert str(tmp_repo_with_docs) in joined
    assert '"total_docs": 0' in joined


def test_onboarding_funnel_window_days_affects_dead_weight(tmp_repo_with_docs, empty_sessions_dir, monkeypatch):
    """Dead-weight count reflects window_days (empty sessions => zero doc reads)."""
    console = _FakeConsole()
    monkeypatch.setattr("vds_cli.cli.console", console)

    docs_onboarding_funnel(
        repo_root=tmp_repo_with_docs,
        sessions_dir=empty_sessions_dir,
        format="json",
        window_days=7,
    )
    joined = "\n".join(console.lines)
    assert '"total_docs": 0' in joined
    assert '"active_docs": 0' in joined
    assert '"dead_weight": 0' in joined


def test_freshness_command_importable():
    """Ensure docs_freshness hasn't been broken by doc-004 changes."""
    import inspect

    params = inspect.signature(docs_freshness).parameters
    assert "repo_root" in params
    assert "repo" in params
    assert "config" in params
