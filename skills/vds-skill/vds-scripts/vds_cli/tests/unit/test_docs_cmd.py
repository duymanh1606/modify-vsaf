"""Unit tests for docs command helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path

from vds_cli.docs_cmd import check_freshness, load_freshness_pairs, validate_docs


def test_validate_docs_reports_and_fixes_claude_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "vds-scripts"
    (repo / "docs" / "phases").mkdir(parents=True)
    (repo / "AGENTS.md").write_text("# AGENTS\n\n- docs/phases/CHANGELOG.md\n", encoding="utf-8")
    (repo / "llms.txt").write_text("# Index\n\n- [agents](./AGENTS.md)\n", encoding="utf-8")
    (repo / "CLAUDE.md").write_text("legacy copy", encoding="utf-8")
    (repo / "docs" / "phases" / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    before = validate_docs(repo, repo=None, fix=False)
    assert any(issue.check == "claude_symlink" for issue in before)

    after = validate_docs(repo, repo=None, fix=True)
    assert any(issue.check == "claude_symlink" and issue.fixed for issue in after)
    assert (repo / "CLAUDE.md").is_symlink()
    assert (repo / "CLAUDE.md").readlink() == Path("AGENTS.md")


def test_load_freshness_pairs_parses_yaml_shape(tmp_path: Path) -> None:
    config = tmp_path / ".freshness.yaml"
    config.write_text(
        "pairs:\n  - doc: docs/a.md\n    source: src/a.py\n    max_lag_days: 3\n",
        encoding="utf-8",
    )

    pairs = load_freshness_pairs(config)
    assert len(pairs) == 1
    assert pairs[0].doc == "docs/a.md"
    assert pairs[0].source == "src/a.py"
    assert pairs[0].max_lag_days == 3


def test_check_freshness_uses_mtime_and_flags_lag(tmp_path: Path) -> None:
    repo = tmp_path / "vds-scripts"
    (repo / "docs").mkdir(parents=True)
    (repo / "src").mkdir(parents=True)

    doc = repo / "docs" / "a.md"
    src = repo / "src" / "a.py"
    doc.write_text("doc", encoding="utf-8")
    src.write_text("source", encoding="utf-8")

    now = time.time()
    os.utime(doc, (now - 86400 * 3, now - 86400 * 3))
    os.utime(src, (now, now))

    config = repo / "docs" / ".freshness.yaml"
    config.write_text(
        "pairs:\n  - doc: docs/a.md\n    source: src/a.py\n    max_lag_days: 1\n",
        encoding="utf-8",
    )

    issues = check_freshness(repo, config)
    assert len(issues) == 1
    assert issues[0].doc == "docs/a.md"
    assert issues[0].source == "src/a.py"


def test_validate_docs_check_ecosystem_pass(tmp_path: Path) -> None:
    repo = tmp_path / "vds-scripts"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# AGENTS", encoding="utf-8")
    (repo / "llms.txt").write_text("# Index", encoding="utf-8")
    (repo / "ECOSYSTEM-CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (repo / "ECOSYSTEM-DOCS.md").write_text("# Index\n", encoding="utf-8")
    issues = validate_docs(repo, check_ecosystem=True)
    assert not any(issue.check.startswith("ecosystem") for issue in issues)


def test_validate_docs_check_ecosystem_missing(tmp_path: Path) -> None:
    repo = tmp_path / "vds-scripts"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# AGENTS", encoding="utf-8")
    (repo / "llms.txt").write_text("# Index", encoding="utf-8")
    issues = validate_docs(repo, check_ecosystem=True)
    ecosystem_issues = [i for i in issues if i.check.startswith("ecosystem")]
    assert len(ecosystem_issues) == 2
    assert any("ECOSYSTEM-DOCS.md" in i.message for i in ecosystem_issues)
    assert any("ECOSYSTEM-CHANGELOG.md" in i.message for i in ecosystem_issues)
