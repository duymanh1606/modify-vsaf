"""Unit tests for confluence_sync module."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from vds_cli.confluence_sync import (
    ConfluenceHubConfig,
    PageConfig,
    RepoConfig,
    _get_hub_page_id,
    load_confluence_config,
    render_page_body,
    run_confluence_sync,
    sync_page,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_config() -> ConfluenceHubConfig:
    return ConfluenceHubConfig(
        parent_page_id="57250660",
        space_key="TTCN24",
        bitbucket_project="WHO",
        bitbucket_base_url="http://bitbucket.digital.vn",
        bitbucket_server="internal",
        repos=[
            RepoConfig(
                slug="vds-scripts",
                name="vds-scripts",
                active=True,
                description="Core scripts",
            ),
        ],
        pages=[
            PageConfig(
                title="WHO-Project Ecosystem Documentation",
                page_id="98997962",
                page_type="navigation_hub",
                description="Top-level nav",
                template="navigation_hub",
            ),
            PageConfig(
                title="Ecosystem Installation Guide",
                page_id="98997963",
                page_type="hybrid_guide",
                description="Setup guide",
                template="installation_guide",
            ),
            PageConfig(
                title="vds-scripts Quick Reference",
                page_id="98997964",
                page_type="quick_reference",
                description="CLI surface",
                template="quick_reference",
                source_files=["AGENTS.md"],
                bitbucket_links=[
                    {"path": "docs/ref.md", "label": "Ref"},
                ],
            ),
            PageConfig(
                title="vds-skills Quick Reference",
                page_id="98997965",
                page_type="quick_reference",
                description="Skill registry",
                template="quick_reference",
                repo="vds-skills",
                source_files=["AGENTS.md"],
            ),
            PageConfig(
                title="Documentation Health Dashboard",
                page_id="98997968",
                page_type="generated_dashboard",
                description="Health status",
                template="health_dashboard",
            ),
            PageConfig(
                title="Orphan Page",
                page_id=None,
                page_type="quick_reference",
                description="No page id yet",
                template="quick_reference",
            ),
        ],
    )


@pytest.fixture
def valid_confluence_yaml() -> str:
    return """
parent_page_id: "57250660"
space_key: "TTCN24"
bitbucket:
  project: "WHO"
  base_url: "http://bitbucket.digital.vn"
  server: "internal"
repos:
  - slug: vds-scripts
    name: vds-scripts
    active: true
    description: Core scripts
pages:
  - title: WHO-Project Ecosystem Documentation
    page_id: "98997962"
    type: navigation_hub
    description: Top-level nav
    template: navigation_hub
"""


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def test_load_confluence_config_parses_yaml(tmp_path: Path, valid_confluence_yaml: str) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / ".confluence.yaml").write_text(valid_confluence_yaml, encoding="utf-8")

    config = load_confluence_config(tmp_path)

    assert config.parent_page_id == "57250660"
    assert config.space_key == "TTCN24"
    assert config.bitbucket_project == "WHO"
    assert config.bitbucket_base_url == "http://bitbucket.digital.vn"
    assert config.bitbucket_server == "internal"
    assert len(config.repos) == 1
    assert config.repos[0].slug == "vds-scripts"
    assert config.repos[0].active is True
    assert len(config.pages) == 1
    assert config.pages[0].title == "WHO-Project Ecosystem Documentation"
    assert config.pages[0].page_id == "98997962"
    assert config.pages[0].page_type == "navigation_hub"


def test_load_confluence_config_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Confluence config not found"):
        load_confluence_config(tmp_path)


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def test_render_navigation_hub(sample_config: ConfluenceHubConfig) -> None:
    page = sample_config.pages[0]
    body = render_page_body(sample_config, page)

    assert "<h1>WHO-Project Ecosystem Documentation</h1>" in body
    assert "vds-scripts" in body
    assert "Core scripts" in body
    assert "http://bitbucket.digital.vn/projects/WHO" in body


def test_render_installation_guide(sample_config: ConfluenceHubConfig) -> None:
    page = sample_config.pages[1]
    body = render_page_body(sample_config, page)

    assert "<h1>Ecosystem Installation Guide</h1>" in body
    assert "git clone" in body
    assert "worktree_uv.sh sync" in body


def test_render_quick_reference_vds_scripts_fallback(sample_config: ConfluenceHubConfig) -> None:
    """vds-scripts quick_reference uses fallback content (no sibling worktree load)."""
    page = sample_config.pages[2]
    body = render_page_body(sample_config, page, repo_root=Path("/fake"))

    assert "<h1>vds-scripts Quick Reference</h1>" in body
    assert "CLI surface" in body
    assert "See linked Bitbucket documentation" in body
    assert "Ref" in body


def test_render_quick_reference_vds_skills_from_sibling_worktree(
    tmp_path: Path, sample_config: ConfluenceHubConfig
) -> None:
    """vds-skills quick_reference loads markdown from sibling worktree when present."""
    page = sample_config.pages[3]
    # Create sibling worktree structure: tmp_path is repo_root, parent is worktrees/
    worktrees = tmp_path.parent
    wt_skills = worktrees / "confluence-hub-skills" / "docs" / "confluence"
    wt_skills.mkdir(parents=True)
    (wt_skills / "vds-skills-quick-ref.md").write_text("# Skills\n\n- skill A\n", encoding="utf-8")

    body = render_page_body(sample_config, page, repo_root=tmp_path)

    assert "<h1>vds-skills Quick Reference</h1>" in body
    assert "Skill registry" in body
    assert "skill A" in body


def test_render_quick_reference_vds_skills_fallback_when_worktree_missing(
    tmp_path: Path, sample_config: ConfluenceHubConfig
) -> None:
    """vds-skills quick_reference falls back when sibling worktree file is absent."""
    page = sample_config.pages[3]
    # Ensure no stale sibling worktree from a prior test under the same pytest tmp root
    wt_dir = tmp_path.parent / "confluence-hub-skills"
    if wt_dir.exists():
        shutil.rmtree(wt_dir)

    body = render_page_body(sample_config, page, repo_root=tmp_path)

    assert "<h1>vds-skills Quick Reference</h1>" in body
    assert "See linked Bitbucket documentation" in body


def test_render_health_dashboard(sample_config: ConfluenceHubConfig) -> None:
    page = sample_config.pages[4]
    body = render_page_body(sample_config, page)

    assert "<h1>Documentation Health Dashboard</h1>" in body
    assert "Validation Results" in body
    assert "Ownership Model" in body


def test_render_unknown_template_fallback(sample_config: ConfluenceHubConfig) -> None:
    page = PageConfig(
        title="Custom Page",
        page_id="999",
        page_type="custom",
        description="A custom page",
        template="unknown_template",
    )
    body = render_page_body(sample_config, page)

    assert "<h1>Custom Page</h1>" in body
    assert "A custom page" in body


# ---------------------------------------------------------------------------
# Hub page id helper
# ---------------------------------------------------------------------------


def test_get_hub_page_id_returns_navigation_hub_id(sample_config: ConfluenceHubConfig) -> None:
    assert _get_hub_page_id(sample_config) == "98997962"


def test_get_hub_page_id_fallback_to_parent_when_no_hub(sample_config: ConfluenceHubConfig) -> None:
    config_no_hub = ConfluenceHubConfig(
        parent_page_id="111",
        space_key="S",
        bitbucket_project="P",
        bitbucket_base_url="http://bb",
        bitbucket_server="internal",
        repos=[],
        pages=[
            PageConfig(
                title="Other",
                page_id="222",
                page_type="quick_reference",
                description="desc",
                template="quick_reference",
            ),
        ],
    )
    assert _get_hub_page_id(config_no_hub) == "111"


# ---------------------------------------------------------------------------
# Sync page (dry-run and error paths)
# ---------------------------------------------------------------------------


def test_sync_page_dry_run_returns_dict_without_api_calls(sample_config: ConfluenceHubConfig, capsys) -> None:
    page = sample_config.pages[0]
    result = sync_page(sample_config, page, dry_run=True, repo_root=None)

    assert result == {"dry_run": True, "title": page.title}
    captured = capsys.readouterr()
    assert "DRY-RUN" in captured.out
    assert page.title in captured.out


def test_sync_page_skipped_when_no_page_id_and_no_create(sample_config: ConfluenceHubConfig, capsys) -> None:
    page = sample_config.pages[5]  # Orphan Page with no page_id
    result = sync_page(sample_config, page, dry_run=False, create_missing=False)

    assert result == {"skipped": True, "title": page.title}
    captured = capsys.readouterr()
    assert "Skipped" in captured.out


# ---------------------------------------------------------------------------
# Full orchestration
# ---------------------------------------------------------------------------


def test_run_confluence_sync_filters_by_page_title(tmp_path: Path, valid_confluence_yaml: str) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / ".confluence.yaml").write_text(valid_confluence_yaml, encoding="utf-8")

    results = run_confluence_sync(tmp_path, dry_run=True, page_title="WHO-Project Ecosystem Documentation")

    assert len(results) == 1
    assert results[0]["title"] == "WHO-Project Ecosystem Documentation"


def test_run_confluence_sync_processes_all_pages_when_no_filter(tmp_path: Path, valid_confluence_yaml: str) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / ".confluence.yaml").write_text(valid_confluence_yaml, encoding="utf-8")

    results = run_confluence_sync(tmp_path, dry_run=True)

    assert len(results) == 1
    assert results[0]["dry_run"] is True
