"""Unit tests for Wave 8 docs validation features (DOC-V2-023 through DOC-V2-026)."""

from pathlib import Path

from vds_cli.docs_cmd import (
    _check_cross_repo_links,
    _check_diataxis_headers,
    _check_orchestrator_docs,
    _check_skill_docs,
    _check_vi_docs,
)


class TestCheckViDocs:
    def test_missing_agents_vi(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        issues = _check_vi_docs("test-repo", tmp_path)
        assert any(i.check == "vi_translation_missing" for i in issues)

    def test_agents_vi_present(self, tmp_path: Path) -> None:
        (tmp_path / "AGENTS.md").write_text("# AGENTS\n")
        (tmp_path / "AGENTS.vi.md").write_text("# AGENTS VI\n")
        issues = _check_vi_docs("test-repo", tmp_path)
        assert not any(i.check == "vi_translation_missing" for i in issues)

    def test_missing_vi_docs_dir(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "agents").mkdir(parents=True)
        issues = _check_vi_docs("test-repo", tmp_path)
        assert any(i.check == "vi_docs_missing" for i in issues)

    def test_vi_docs_dir_present(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "agents").mkdir(parents=True)
        (tmp_path / "docs" / "vi" / "agents").mkdir(parents=True)
        issues = _check_vi_docs("test-repo", tmp_path)
        assert not any(i.check == "vi_docs_missing" for i in issues)

    def test_llms_missing_vi_link(self, tmp_path: Path) -> None:
        (tmp_path / "llms.txt").write_text("# Index\n")
        issues = _check_vi_docs("test-repo", tmp_path)
        assert any(i.check == "vi_llms_missing" for i in issues)

    def test_llms_has_vi_link(self, tmp_path: Path) -> None:
        (tmp_path / "llms.txt").write_text("# Index\n\n- [vi](docs/vi/)\n")
        issues = _check_vi_docs("test-repo", tmp_path)
        assert not any(i.check == "vi_llms_missing" for i in issues)


class TestCheckDiataxisHeaders:
    def test_valid_header(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("<!-- diátaxis: how-to -->\n# Test\n")
        issues = _check_diataxis_headers("test-repo", tmp_path)
        assert len(issues) == 0

    def test_missing_header(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("# Test\n")
        issues = _check_diataxis_headers("test-repo", tmp_path)
        assert any(i.check == "diataxis_header_missing" for i in issues)

    def test_invalid_quadrant(self, tmp_path: Path) -> None:
        docs = tmp_path / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("<!-- diátaxis: invalid -->\n# Test\n")
        issues = _check_diataxis_headers("test-repo", tmp_path)
        assert any(i.check == "diataxis_header_invalid" for i in issues)


class TestCheckCrossRepoLinks:
    def test_valid_cross_repo_link(self, tmp_path: Path) -> None:
        repo1 = tmp_path / "vds-scripts"
        repo2 = tmp_path / "vds-skills"
        repo1.mkdir()
        repo2.mkdir()
        docs = repo1 / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("[skill](../vds-skills/skills/test/SKILL.md)\n")
        (repo2 / "skills" / "test").mkdir(parents=True)
        (repo2 / "skills" / "test" / "SKILL.md").write_text("# Skill\n")
        issues = _check_cross_repo_links("vds-scripts", repo1, tmp_path)
        assert len(issues) == 0

    def test_broken_cross_repo_link(self, tmp_path: Path) -> None:
        repo1 = tmp_path / "vds-scripts"
        repo2 = tmp_path / "vds-skills"
        repo1.mkdir()
        repo2.mkdir()
        docs = repo1 / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("[skill](../vds-skills/skills/test/MISSING.md)\n")
        issues = _check_cross_repo_links("vds-scripts", repo1, tmp_path)
        assert any(i.check == "cross_repo_link_broken" for i in issues)

    def test_ignores_non_repo_links(self, tmp_path: Path) -> None:
        repo1 = tmp_path / "vds-scripts"
        repo1.mkdir()
        docs = repo1 / "docs" / "agents"
        docs.mkdir(parents=True)
        (docs / "test.md").write_text("[local](../reference/other.md)\n")
        issues = _check_cross_repo_links("vds-scripts", repo1, tmp_path)
        assert len(issues) == 0


class TestCheckOrchestratorDocs:
    def test_orchestrator_with_doc(self, tmp_path: Path) -> None:
        vds_cli = tmp_path / "vds_cli" / "src" / "vds_cli"
        vds_cli.mkdir(parents=True)
        (vds_cli / "router.py").write_text('"audit": {\n  "module": "audit"\n}\n')
        ref = tmp_path / "docs" / "agents" / "reference"
        ref.mkdir(parents=True)
        (ref / "audit-orchestrator.md").write_text("# Audit\n")
        issues = _check_orchestrator_docs("test-repo", tmp_path)
        assert len(issues) == 0

    def test_orchestrator_without_doc(self, tmp_path: Path) -> None:
        vds_cli = tmp_path / "vds_cli" / "src" / "vds_cli"
        vds_cli.mkdir(parents=True)
        (vds_cli / "router.py").write_text('"custom_orch": {\n  "module": "custom"\n}\n')
        ref = tmp_path / "docs" / "agents" / "reference"
        ref.mkdir(parents=True)
        issues = _check_orchestrator_docs("test-repo", tmp_path)
        assert any(i.check == "orchestrator_doc_missing" for i in issues)


class TestCheckSkillDocs:
    def test_skill_with_quality_and_refs(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        skills.mkdir()
        skill = skills / "test-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Skill\n")
        (skill / "QUALITY.md").write_text("# Quality\n")
        (skill / "references").mkdir()
        issues = _check_skill_docs("vds-skills", tmp_path)
        assert len(issues) == 0

    def test_skill_missing_quality(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        skills.mkdir()
        skill = skills / "test-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Skill\n")
        (skill / "references").mkdir()
        issues = _check_skill_docs("vds-skills", tmp_path)
        assert any(i.check == "skill_quality_doc" for i in issues)

    def test_skill_missing_refs(self, tmp_path: Path) -> None:
        skills = tmp_path / "skills"
        skills.mkdir()
        skill = skills / "test-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Skill\n")
        (skill / "QUALITY.md").write_text("# Quality\n")
        issues = _check_skill_docs("vds-skills", tmp_path)
        assert any(i.check == "skill_references" for i in issues)

    def test_skips_non_vds_skills_repo(self, tmp_path: Path) -> None:
        issues = _check_skill_docs("vds-scripts", tmp_path)
        assert len(issues) == 0
