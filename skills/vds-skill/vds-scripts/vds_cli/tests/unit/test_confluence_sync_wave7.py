"""Unit tests for confluence_sync Wave 7 additions (DOC-V2-017..022)."""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from vds_cli.confluence_sync import (
    ConfluenceHubConfig,
    DocEntry,
    PageConfig,
    check_bitbucket_links,
    check_word_count,
    render_inventory_table,
    render_page_body,
    render_team_view,
    scan_docs_tree,
)

# ---------------------------------------------------------------------------
# DOC-V2-017: check_word_count
# ---------------------------------------------------------------------------


def test_check_word_count_under_threshold_logs_nothing(caplog):
    body = "word " * 500  # 500 words
    with caplog.at_level(logging.WARNING):
        count = check_word_count(body, max_words=800)
    assert count == 500
    assert "exceeds" not in caplog.text


def test_check_word_count_over_threshold_logs_warning(caplog):
    body = "word " * 900  # 900 words
    with caplog.at_level(logging.WARNING):
        count = check_word_count(body, max_words=800)
    assert count == 900
    assert "exceeds" in caplog.text
    assert "900" in caplog.text


def test_check_word_count_custom_max():
    body = "a b c d e"
    assert check_word_count(body, max_words=10) == 5


# ---------------------------------------------------------------------------
# DOC-V2-018: scan_docs_tree
# ---------------------------------------------------------------------------


def test_scan_docs_tree_empty_when_no_docs_dir(tmp_path: Path) -> None:
    result = scan_docs_tree(tmp_path)
    assert result == []


def test_scan_docs_tree_reads_diataxis_header(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents" / "how-to"
    docs.mkdir(parents=True)
    (docs / "setup.md").write_text("# Setup Guide\n\n<!-- diátaxis: how-to -->\n\nDo this.\n", encoding="utf-8")

    entries = scan_docs_tree(tmp_path)
    assert len(entries) == 1
    assert entries[0].title == "Setup Guide"
    assert entries[0].quadrant == "how-to"
    assert entries[0].repo == tmp_path.name


def test_scan_docs_tree_reads_team_tag(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents" / "reference"
    docs.mkdir(parents=True)
    (docs / "api.md").write_text(
        "# API Ref\n\n<!-- diátaxis: reference -->\n<!-- team: core -->\n\nDetails.\n",
        encoding="utf-8",
    )

    entries = scan_docs_tree(tmp_path)
    assert len(entries) == 1
    assert entries[0].quadrant == "reference"
    assert entries[0].team_tag == "core"


def test_scan_docs_tree_uncategorized_when_no_header(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents" / "explanation"
    docs.mkdir(parents=True)
    (docs / "overview.md").write_text("# Overview\n\nSome text.\n", encoding="utf-8")

    entries = scan_docs_tree(tmp_path)
    assert entries[0].quadrant == "uncategorized"


def test_scan_docs_tree_sorts_by_quadrant_then_title(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents"
    docs.mkdir(parents=True)
    (docs / "b.md").write_text("# B\n\n<!-- diátaxis: tutorial -->\n", encoding="utf-8")
    (docs / "a.md").write_text("# A\n\n<!-- diátaxis: tutorial -->\n", encoding="utf-8")
    (docs / "z.md").write_text("# Z\n\n<!-- diátaxis: how-to -->\n", encoding="utf-8")

    entries = scan_docs_tree(tmp_path)
    titles = [e.title for e in entries]
    assert titles == ["Z", "A", "B"]


# ---------------------------------------------------------------------------
# DOC-V2-018: render_inventory_table
# ---------------------------------------------------------------------------


def test_render_inventory_table_empty() -> None:
    result = render_inventory_table([])
    assert "No documents found" in result


def test_render_inventory_table_generates_xhtml() -> None:
    docs = [
        DocEntry(
            path=Path("docs/agents/how-to/setup.md"),
            title="Setup Guide",
            quadrant="how-to",
            line_count=42,
            last_modified=0.0,
            repo="vds-scripts",
        ),
        DocEntry(
            path=Path("docs/agents/reference/api.md"),
            title="API Reference",
            quadrant="reference",
            line_count=100,
            last_modified=0.0,
            repo="vds-scripts",
        ),
    ]
    result = render_inventory_table(docs)
    assert result.startswith("<table>")
    assert result.endswith("</table>")
    assert "Setup Guide" in result
    assert "API Reference" in result
    assert "how-to" in result
    assert "reference" in result
    assert "42" in result
    assert "100" in result


# ---------------------------------------------------------------------------
# DOC-V2-020: render_team_view
# ---------------------------------------------------------------------------


def test_render_team_view_empty_when_no_match() -> None:
    docs = [
        DocEntry(
            path=Path("a.md"),
            title="A",
            quadrant="how-to",
            line_count=10,
            last_modified=0.0,
            repo="r",
            team_tag="other",
        ),
    ]
    result = render_team_view("core", docs)
    assert "No documents found" in result


def test_render_team_view_filters_by_team() -> None:
    docs = [
        DocEntry(
            path=Path("core.md"),
            title="Core Doc",
            quadrant="how-to",
            line_count=20,
            last_modified=0.0,
            repo="r",
            team_tag="core",
        ),
        DocEntry(
            path=Path("other.md"),
            title="Other Doc",
            quadrant="reference",
            line_count=30,
            last_modified=0.0,
            repo="r",
            team_tag="other",
        ),
    ]
    result = render_team_view("core", docs)
    assert "Core Doc" in result
    assert "Other Doc" not in result
    assert "<table>" in result


def test_render_team_view_case_insensitive() -> None:
    docs = [
        DocEntry(
            path=Path("a.md"),
            title="A",
            quadrant="how-to",
            line_count=10,
            last_modified=0.0,
            repo="r",
            team_tag="CORE",
        ),
    ]
    result = render_team_view("core", docs)
    assert "A" in result


# ---------------------------------------------------------------------------
# DOC-V2-022: check_bitbucket_links
# ---------------------------------------------------------------------------


def test_check_bitbucket_links_all_ok() -> None:
    config = ConfluenceHubConfig(
        parent_page_id="1",
        space_key="S",
        bitbucket_project="WHO",
        bitbucket_base_url="http://bb",
        bitbucket_server="internal",
        repos=[],
        pages=[
            PageConfig(
                title="Page",
                page_id="2",
                page_type="quick_reference",
                description="desc",
                template="quick_reference",
                repo="vds-scripts",
                bitbucket_links=[{"path": "README.md", "label": "Readme"}],
            ),
        ],
    )

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock_response):
        results = check_bitbucket_links(config)

    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["status_code"] == 200


def test_check_bitbucket_links_broken() -> None:
    config = ConfluenceHubConfig(
        parent_page_id="1",
        space_key="S",
        bitbucket_project="WHO",
        bitbucket_base_url="http://bb",
        bitbucket_server="internal",
        repos=[],
        pages=[
            PageConfig(
                title="Page",
                page_id="2",
                page_type="quick_reference",
                description="desc",
                template="quick_reference",
                repo="vds-scripts",
                bitbucket_links=[{"path": "MISSING.md", "label": "Missing"}],
            ),
        ],
    )

    with patch("urllib.request.urlopen", side_effect=Exception("404")):
        results = check_bitbucket_links(config)

    assert len(results) == 1
    assert results[0]["status"] == "broken"
    assert results[0]["status_code"] is None


# ---------------------------------------------------------------------------
# Template rendering: doc_inventory + team_view
# ---------------------------------------------------------------------------


def test_render_page_body_doc_inventory(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents" / "how-to"
    docs.mkdir(parents=True)
    (docs / "setup.md").write_text("# Setup\n\n<!-- diátaxis: how-to -->\n\nSteps.\n", encoding="utf-8")

    config = ConfluenceHubConfig(
        parent_page_id="1",
        space_key="S",
        bitbucket_project="WHO",
        bitbucket_base_url="http://bb",
        bitbucket_server="internal",
        repos=[],
        pages=[],
    )
    page = PageConfig(
        title="Inventory",
        page_id="2",
        page_type="doc_inventory",
        description="Auto inventory",
        template="doc_inventory",
    )

    body = render_page_body(config, page, repo_root=tmp_path)
    assert "<h1>Documentation Inventory</h1>" in body
    assert "how-to" in body
    assert "Setup" in body


def test_render_page_body_team_view(tmp_path: Path) -> None:
    docs = tmp_path / "docs" / "agents"
    docs.mkdir(parents=True)
    (docs / "core.md").write_text(
        "# Core Doc\n\n<!-- diátaxis: how-to -->\n<!-- team: core -->\n\nText.\n",
        encoding="utf-8",
    )

    config = ConfluenceHubConfig(
        parent_page_id="1",
        space_key="S",
        bitbucket_project="WHO",
        bitbucket_base_url="http://bb",
        bitbucket_server="internal",
        repos=[],
        pages=[],
    )
    page = PageConfig(
        title="Team View: Core",
        page_id="2",
        page_type="team_view",
        description="Team scope: core",
        template="team_view",
    )

    body = render_page_body(config, page, repo_root=tmp_path)
    assert "<h1>Team View: core</h1>" in body
    assert "Core Doc" in body


# ---------------------------------------------------------------------------
# Integration: run_confluence_sync with validate_links
# ---------------------------------------------------------------------------


def test_run_confluence_sync_validate_links_flag(tmp_path: Path) -> None:
    from vds_cli.confluence_sync import run_confluence_sync

    yaml_text = """
parent_page_id: "57250660"
space_key: "TTCN24"
bitbucket:
  project: "WHO"
  base_url: "http://bb"
  server: "internal"
repos: []
pages:
  - title: Test Page
    page_id: "999"
    type: quick_reference
    description: desc
    template: quick_reference
"""
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / ".confluence.yaml").write_text(yaml_text, encoding="utf-8")

    mock_response = MagicMock()
    mock_response.getcode.return_value = 200
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = False

    with patch("urllib.request.urlopen", return_value=mock_response):
        results = run_confluence_sync(tmp_path, dry_run=True, validate_links=True)

    assert len(results) == 1
    assert results[0]["dry_run"] is True
