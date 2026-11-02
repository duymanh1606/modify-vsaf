"""Coverage uplift for vds_agent_core.skills.manager (W5.4).

Targets uncovered lines 41-45, 79, 121, 147-148, 154, 156, 175, 215, 217,
220, 231, 253, 287-293, 342-343, 353-355, 360-362, 369, 371 in SkillManager.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from vds_agent_core.skills.manager import ContentHashValidator, SkillManager


def _make_toolset(
    skills: dict[str, Any] | None = None,
    metadata: list[Any] | None = None,
    tools: dict[str, Any] | None = None,
) -> MagicMock:
    ts = MagicMock()
    ts.skills = skills if skills is not None else {}
    ts._vds_skill_metadata = metadata if metadata is not None else []
    ts.tools = tools if tools is not None else {}
    return ts


def _make_meta(name: str, *, has_path: bool = True, has_hash: bool = True) -> MagicMock:
    item = MagicMock()
    item.name = name
    if has_path:
        item.path = f"/skills/{name}"
    else:
        del item.path
    if has_hash:
        item.content_hash = "abc123"
    else:
        del item.content_hash
    return item


class TestLoadSkillRubric:
    """load_skill_rubric — lines 41-45 (read + error fallback)."""

    def test_reads_skill_md_content(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / "research-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Research Skill\nDoes research.", encoding="utf-8")
        # Clear lru_cache to avoid cross-test contamination
        SkillManager.load_skill_rubric.cache_clear()
        result = SkillManager.load_skill_rubric("research-skill", tmp_path)
        assert result == "# Research Skill\nDoes research."

    def test_returns_empty_string_on_missing_file(self, tmp_path: Path) -> None:
        SkillManager.load_skill_rubric.cache_clear()
        result = SkillManager.load_skill_rubric("nonexistent-skill", tmp_path)
        assert result == ""


class TestDropSkillFromToolsetsEdgePaths:
    """Targets lines 79, 121 — edge paths in drop_skill_from_toolsets."""

    def test_whitespace_only_skill_name_is_noop(self) -> None:
        # _build_skill_aliases("   ") returns empty set → line 79
        ts = _make_toolset(skills={"research-skill": object()})
        _updated, count = SkillManager.drop_skill_from_toolsets([ts], "   ")
        assert count == 0

    def test_toolset_with_metadata_only_no_match_appended(self) -> None:
        # Toolset has no skills dict but has metadata that does NOT match → line 121
        ts = MagicMock()
        ts.skills = None  # not a dict → falls through to metadata branch
        item = _make_meta("other-skill")
        ts._vds_skill_metadata = [item]
        updated, count = SkillManager.drop_skill_from_toolsets([ts], "research-skill")
        assert count == 0
        assert ts in updated  # line 121: toolset appended when no match

    def test_metadata_toolset_all_matched_and_empty_is_excluded(self) -> None:
        # metadata-only toolset where all items match → removed (not appended)
        ts = MagicMock()
        ts.skills = None
        item = _make_meta("research-skill")
        ts._vds_skill_metadata = [item]
        updated, count = SkillManager.drop_skill_from_toolsets([ts], "research-skill")
        assert count == 1
        assert ts not in updated


class TestPrevalidateSkillToolsetsEdgePaths:
    """Targets lines 147-148, 154, 156, 175, 177."""

    def test_non_dict_skills_map_passes_through(self) -> None:
        # Line 147-148: not isinstance(skills_map, dict) → append and continue
        validator = MagicMock(spec=ContentHashValidator)
        ts = MagicMock()
        ts.skills = "not-a-dict"
        ts._vds_skill_metadata = []
        log = MagicMock()
        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        assert ts in result

    def test_metadata_item_with_empty_name_skipped(self) -> None:
        # Line 154: empty skill_name → continue
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = True
        item = MagicMock()
        item.name = ""
        ts = _make_toolset(skills={"research-skill": object()}, metadata=[item])
        log = MagicMock()
        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        assert len(result) == 1

    def test_metadata_item_not_in_skills_map_skipped(self) -> None:
        # Line 156: skill_name not in skills_map → continue
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = False  # would reject if reached
        item = _make_meta("unknown-skill")
        ts = _make_toolset(skills={"research-skill": object()}, metadata=[item])
        log = MagicMock()
        # unknown-skill is not in skills_map, so validator.validate is never called
        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        # research-skill still present (unknown-skill was not in skills_map, validation skipped)
        assert len(result) == 1

    def test_skills_map_empty_after_rejection_warns_empty(self) -> None:
        # Line 177: skills_map becomes empty → warning logged
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = False
        item = _make_meta("bad-skill")
        ts = _make_toolset(skills={"bad-skill": object()}, metadata=[item])
        log = MagicMock()
        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        assert len(result) == 0
        log.warning.assert_any_call("agentic_skill_toolset_empty_after_prevalidation")

    def test_valid_skills_kept_in_map(self) -> None:
        # Line 175: skills_map still has entries → toolset appended
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = True
        item = _make_meta("good-skill")
        ts = _make_toolset(skills={"good-skill": object()}, metadata=[item])
        log = MagicMock()
        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        assert len(result) == 1


class TestCollectAvailableSkillNamesEdgePaths:
    """Targets lines 215, 217, 220, 231."""

    def test_metadata_fallback_skipped_when_not_allowed(self) -> None:
        # Line 215: allow_metadata_fallback=False → continue (skip metadata)
        ts = MagicMock()
        ts.skills = None
        item = MagicMock()
        item.name = "metadata-skill"
        ts._vds_skill_metadata = [item]
        result = SkillManager.collect_available_skill_names([ts], allow_metadata_fallback=False)
        assert "metadata-skill" not in result

    def test_metadata_fallback_skipped_when_runtime_map_exists(self) -> None:
        # Line 217: has_any_runtime_skills_map=True → metadata-only toolsets skipped
        ts_with_map = _make_toolset(skills={"real-skill": object()})
        ts_meta_only = MagicMock()
        ts_meta_only.skills = None
        item = MagicMock()
        item.name = "meta-skill"
        ts_meta_only._vds_skill_metadata = [item]
        result = SkillManager.collect_available_skill_names([ts_with_map, ts_meta_only])
        assert "real-skill" in result
        assert "meta-skill" not in result  # skipped because a runtime map exists

    def test_metadata_without_list_skipped(self) -> None:
        # Line 220: metadata is not a list → continue
        ts = MagicMock()
        ts.skills = None
        ts._vds_skill_metadata = "not-a-list"
        result = SkillManager.collect_available_skill_names([ts])
        assert result == []

    def test_empty_name_metadata_item_skipped(self) -> None:
        # Line 231: empty name → not appended
        ts = MagicMock()
        ts.skills = None
        item = MagicMock()
        item.name = ""
        ts._vds_skill_metadata = [item]
        result = SkillManager.collect_available_skill_names([ts])
        assert result == []


class TestNormalizeSkillToken:
    """_normalize_skill_token — line 231 (empty text early return)."""

    def test_empty_string_returns_empty(self) -> None:
        result = SkillManager._normalize_skill_token("")
        assert result == ""

    def test_whitespace_only_returns_empty(self) -> None:
        result = SkillManager._normalize_skill_token("   ")
        assert result == ""

    def test_normalizes_underscores(self) -> None:
        result = SkillManager._normalize_skill_token("research_skill")
        assert result == "research-skill"

    def test_collapses_multiple_dashes(self) -> None:
        result = SkillManager._normalize_skill_token("research--skill")
        assert result == "research-skill"


class TestResolveAvailableSkillMatchEdgePaths:
    """Targets line 253 — empty candidate aliases returns None."""

    def test_empty_candidate_returns_none(self) -> None:
        # Line 253: candidate_aliases empty → return None
        result = SkillManager._resolve_available_skill_match("", ["research-skill"])
        assert result is None

    def test_no_match_returns_none(self) -> None:
        result = SkillManager._resolve_available_skill_match("nonexistent-xyz", ["research-skill"])
        assert result is None


class TestRetainSkillsInToolsetsMetadataPath:
    """Targets lines 287-293 — metadata filter in retain_skills_in_toolsets."""

    def test_metadata_items_filtered_by_allowed_names(self) -> None:
        # Lines 287-293: metadata list is filtered
        item_keep = MagicMock()
        item_keep.name = "research-skill"
        item_remove = MagicMock()
        item_remove.name = "grepai-skill"
        ts = _make_toolset(
            skills={"research-skill": object(), "grepai-skill": object()},
            metadata=[item_keep, item_remove],
        )
        _, removed = SkillManager.retain_skills_in_toolsets(
            toolsets=[ts],
            allowed_skill_names=["research-skill"],
        )
        assert item_keep in ts._vds_skill_metadata
        assert item_remove not in ts._vds_skill_metadata
        assert removed >= 1

    def test_metadata_item_with_empty_name_not_counted_as_removed(self) -> None:
        # Line 292: item_name is empty → removed_entries NOT incremented
        item = MagicMock()
        item.name = ""
        ts = _make_toolset(skills={}, metadata=[item])
        _, removed = SkillManager.retain_skills_in_toolsets(
            toolsets=[ts],
            allowed_skill_names=["some-skill"],
        )
        assert removed == 0


class TestBuildPreloadedSkillContextEdgePaths:
    """Targets lines 342-343, 353-355, 360-362, 369, 371."""

    def _make_skill_toolset(
        self,
        skill_name: str,
        *,
        description: str = "",
        content: str = "",
        resources: list[str] | None = None,
        scripts: list[str] | None = None,
        get_skill_raises: bool = False,
    ) -> MagicMock:
        ts = MagicMock()
        ts.skills = {skill_name: object()}
        resource_items = [MagicMock(name=r) for r in (resources or [])]
        for i, name in enumerate(resources or []):
            resource_items[i].name = name
        script_items = [MagicMock() for _ in (scripts or [])]
        for i, name in enumerate(scripts or []):
            script_items[i].name = name

        skill = MagicMock()
        skill.description = description
        skill.content = content
        skill.resources = resource_items
        skill.scripts = script_items

        if get_skill_raises:
            ts.get_skill = MagicMock(side_effect=RuntimeError("load failed"))
        else:
            ts.get_skill = MagicMock(return_value=skill)
        return ts

    def test_get_skill_raises_continues_to_next(self) -> None:
        # Lines 342-343: get_skill raises → continue (try/except)
        ts_bad = self._make_skill_toolset("bad-skill", get_skill_raises=True)
        ts_bad.skills = {"bad-skill": object()}
        # No good toolset — result should be empty
        context, loaded = SkillManager.build_preloaded_skill_context(
            [ts_bad], ["bad-skill"]
        )
        assert context == ""
        assert loaded == []

    def test_no_callable_get_skill_skips_toolset(self) -> None:
        # Line 338-339: get_skill not callable → continue
        ts = MagicMock()
        ts.skills = {"some-skill": object()}
        ts.get_skill = "not-callable"
        context, _loaded = SkillManager.build_preloaded_skill_context([ts], ["some-skill"])
        assert context == ""

    def test_resources_added_to_snippet(self) -> None:
        # Lines 353-355: resource_names appended, then line 369 adds "Resources:" line
        ts = self._make_skill_toolset(
            "research-skill", description="Does research", resources=["guide.md", "ref.md"]
        )
        context, loaded = SkillManager.build_preloaded_skill_context([ts], ["research-skill"])
        assert "research-skill" in loaded
        assert "Resources:" in context
        assert "guide.md" in context

    def test_scripts_added_to_snippet(self) -> None:
        # Lines 360-362: script_names appended, then line 371 adds "Scripts:" line
        ts = self._make_skill_toolset(
            "research-skill", description="Does research", scripts=["run.sh", "setup.sh"]
        )
        context, _loaded = SkillManager.build_preloaded_skill_context([ts], ["research-skill"])
        assert "Scripts:" in context
        assert "run.sh" in context

    def test_max_skills_limit_respected(self) -> None:
        # Line 331-332: len(loaded_names) >= max_skills → break
        ts1 = self._make_skill_toolset("skill-a", description="A")
        ts2 = self._make_skill_toolset("skill-b", description="B")
        ts3 = self._make_skill_toolset("skill-c", description="C")
        _context, loaded = SkillManager.build_preloaded_skill_context(
            [ts1, ts2, ts3], ["skill-a", "skill-b", "skill-c"], max_skills=2
        )
        assert len(loaded) == 2

    def test_preferred_skill_names_prioritized(self) -> None:
        ts = self._make_skill_toolset("vds-scripts-skill", description="VDS Scripts")
        ts2 = self._make_skill_toolset("research-skill", description="Research")
        ts.skills.update(ts2.skills)
        combined = MagicMock()
        combined.skills = {"vds-scripts-skill": object(), "research-skill": object()}
        combined.get_skill = MagicMock(side_effect=lambda n: MagicMock(
            description=n, content="", resources=[], scripts=[]
        ))
        _context, loaded = SkillManager.build_preloaded_skill_context(
            [combined],
            ["vds-scripts-skill", "research-skill"],
            preferred_skill_names=["research-skill"],
            max_skills=1,
        )
        assert loaded == ["research-skill"]

    def test_content_truncated_at_max_chars(self) -> None:
        long_content = "x" * 3000
        ts = self._make_skill_toolset("skill-x", content=long_content)
        context, loaded = SkillManager.build_preloaded_skill_context(
            [ts], ["skill-x"], max_chars_per_skill=100
        )
        assert "skill-x" in loaded
        assert len(context) < 3000
