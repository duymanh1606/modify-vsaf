"""Tests for docs.consumption.scanner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from vds_cli.docs.consumption.scanner import (
    scan_consumption,
)

if TYPE_CHECKING:
    import pytest


def _make_event(file_path: str | list[str], tool_name: str = "Read", timestamp: str | None = None) -> dict:
    """Build a minimal assistant tool_use event."""
    content: list[dict] = [
        {
            "type": "tool_use",
            "name": tool_name,
            "input": {"file_path": file_path},
        }
    ]
    return {
        "type": "assistant",
        "timestamp": timestamp or "2026-01-15T12:00:00Z",
        "message": {"content": content},
    }


def test_reads_single_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Three valid tool_use events → three DocReads with correct paths."""
    repo = tmp_path / "repo"
    repo.mkdir()
    docs_dir = repo / "docs" / "agents"
    docs_dir.mkdir(parents=True)
    (docs_dir / "agent_a.md").write_text("<!-- diátaxis: tutorial -->\n# A\n", encoding="utf-8")
    (docs_dir / "agent_b.md").write_text("# B\n", encoding="utf-8")
    (docs_dir / "agent_c.md").write_text("<!-- diátaxis: how-to -->\n# C\n", encoding="utf-8")

    # Build a session directory with one JSONL file
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    jsonl = session_dir / "session-abc.jsonl"
    events = [
        _make_event("docs/agents/agent_a.md"),
        _make_event("docs/agents/agent_b.md"),
        _make_event("docs/agents/agent_c.md", timestamp="2026-01-15T12:05:00Z"),
    ]
    jsonl.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    reads = scan_consumption(repo, session_dir=session_dir)
    assert len(reads) == 3

    # All should belong to the same session
    assert {r.session_id for r in reads} == {"session-abc"}

    paths = sorted(str(r.path) for r in reads)
    assert paths == sorted(
        [
            str(repo / "docs" / "agents" / "agent_a.md"),
            str(repo / "docs" / "agents" / "agent_b.md"),
            str(repo / "docs" / "agents" / "agent_c.md"),
        ]
    )

    diataxis_map = {str(r.path): r.diataxis for r in reads}
    assert diataxis_map[str(repo / "docs" / "agents" / "agent_a.md")] == "tutorial"
    assert diataxis_map[str(repo / "docs" / "agents" / "agent_b.md")] is None
    assert diataxis_map[str(repo / "docs" / "agents" / "agent_c.md")] == "how-to"


def test_home_redaction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Paths under $HOME are emitted with ~ prefix."""
    # Mock home to tmp_path
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    repo = tmp_path / "repo"
    repo.mkdir()
    home_doc = tmp_path / "docs" / "agents" / "agent_x.md"
    home_doc.parent.mkdir(parents=True)
    home_doc.write_text("# X\n", encoding="utf-8")

    # Use absolute path that lives under mocked home
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    jsonl = session_dir / "session-redact.jsonl"
    jsonl.write_text(
        json.dumps(_make_event(str(home_doc))) + "\n",
        encoding="utf-8",
    )

    reads = scan_consumption(repo, session_dir=session_dir)
    assert len(reads) == 1
    assert reads[0].path == Path("~") / "docs" / "agents" / "agent_x.md"


def test_missing_file_graceful(tmp_path: Path) -> None:
    """Missing or empty JSONL directory returns empty list."""
    repo = tmp_path / "repo"
    repo.mkdir()

    missing_dir = tmp_path / "nonexistent"
    assert scan_consumption(repo, session_dir=missing_dir) == []

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert scan_consumption(repo, session_dir=empty_dir) == []


def test_session_deduplication(tmp_path: Path) -> None:
    """Same doc in same session counted once; different sessions counted separately."""
    repo = tmp_path / "repo"
    repo.mkdir()
    doc = repo / "docs" / "agents" / "agent_y.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("# Y\n", encoding="utf-8")

    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    s1 = session_dir / "session-s1.jsonl"
    s1.write_text(
        json.dumps(_make_event("docs/agents/agent_y.md"))
        + "\n"
        + json.dumps(_make_event("docs/agents/agent_y.md"))
        + "\n",
        encoding="utf-8",
    )

    s2 = session_dir / "session-s2.jsonl"
    s2.write_text(
        json.dumps(_make_event("docs/agents/agent_y.md")) + "\n",
        encoding="utf-8",
    )

    reads = scan_consumption(repo, session_dir=session_dir)
    assert len(reads) == 2

    sessions = [r.session_id for r in reads]
    assert sessions.count("session-s1") == 1
    assert sessions.count("session-s2") == 1
