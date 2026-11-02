"""Tests for SkillManager.load_skill_rubric (FR-A2)."""

from __future__ import annotations

from pathlib import Path

from vds_agent_core.skills.manager import SkillManager


class TestLoadSkillRubric:
    """FR-A2: rubric-only skill loading via lru_cache."""

    def test_load_existing_skill_md(self, tmp_path: Path) -> None:
        """Existing SKILL.md returns its content."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# My Skill\nRubric content here.", encoding="utf-8")

        # Clear any prior cached state
        SkillManager.load_skill_rubric.cache_clear()

        result = SkillManager.load_skill_rubric("my-skill", tmp_path)
        assert result == "# My Skill\nRubric content here."

    def test_load_missing_skill_returns_empty(self, tmp_path: Path) -> None:
        """Missing skill directory returns empty string, no exception."""
        SkillManager.load_skill_rubric.cache_clear()

        result = SkillManager.load_skill_rubric("nonexistent-skill", tmp_path)
        assert result == ""

    def test_caching_works(self, tmp_path: Path) -> None:
        """Second call returns cached result (verify via cache_info)."""
        skill_dir = tmp_path / "cached-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("cached content", encoding="utf-8")

        SkillManager.load_skill_rubric.cache_clear()

        SkillManager.load_skill_rubric("cached-skill", tmp_path)
        SkillManager.load_skill_rubric("cached-skill", tmp_path)

        info = SkillManager.load_skill_rubric.cache_info()
        assert info.hits >= 1
        assert info.misses >= 1
