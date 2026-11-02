"""Tests for ecosystem_docs module."""

from vds_cli.ecosystem_docs import discover_repos, scan_repo_docs


class TestDiscoverRepos:
    def test_no_repos_found(self, tmp_path):
        found = discover_repos(tmp_path)
        assert found == []

    def test_finds_repos_with_agents_md(self, tmp_path):
        for name in ["vds-scripts", "vds-skills"]:
            repo = tmp_path / name
            repo.mkdir()
            (repo / "AGENTS.md").write_text("# Test")
        found = discover_repos(tmp_path)
        assert len(found) == 2
        assert {f.name for f in found} == {"vds-scripts", "vds-skills"}


class TestScanRepoDocs:
    def test_empty_repo(self, tmp_path):
        entries = scan_repo_docs(tmp_path)
        assert entries == []

    def test_finds_doc_with_diataxis_header(self, tmp_path):
        docs = tmp_path / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("# Test Doc\n<!-- diátaxis: how-to -->\n")
        entries = scan_repo_docs(tmp_path)
        assert len(entries) == 1
        assert entries[0].quadrant == "how-to"
        assert entries[0].title == "Test Doc"


    def test_finds_doc_with_yaml_frontmatter_diátaxis(self, tmp_path):
        """Phase 180 docs use YAML frontmatter instead of HTML comments."""
        docs = tmp_path / "docs" / "agents" / "explanation"
        docs.mkdir(parents=True)
        (tmp_path / "docs" / "AGENTS.md").write_text("# AGENTS", encoding="utf-8")
        (docs / "whats-new.md").write_text(
            "---\n"
            "diátaxis: explanation\n"
            "phase_ref: 180\n"
            "---\n\n"
            "# New Changes\n\nRecent changes.\n",
            encoding="utf-8",
        )
        entries = scan_repo_docs(tmp_path)
        assert len(entries) == 1
        assert entries[0].quadrant == "explanation"
        assert entries[0].title == "New Changes"

    def test_title_falls_back_to_stem_when_no_heading(self, tmp_path):
        """Docs with neither YAML frontmatter nor H1 use filename stem."""
        docs = tmp_path / "docs" / "agents" / "reference"
        docs.mkdir(parents=True)
        (tmp_path / "docs" / "AGENTS.md").write_text("# AGENTS", encoding="utf-8")
        (docs / "bare-doc.md").write_text("Just body text.\n", encoding="utf-8")
        entries = scan_repo_docs(tmp_path)
        assert len(entries) == 1
        assert entries[0].title == "Bare Doc"
        assert entries[0].quadrant == "uncategorized"
