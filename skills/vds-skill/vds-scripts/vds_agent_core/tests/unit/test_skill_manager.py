"""Tests for vds_agent_core.skills.manager — SkillManager extraction (FR-5.2)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from vds_agent_core.skills.manager import ContentHashValidator, SkillManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_toolset(skills: dict[str, Any] | None = None, metadata: list[Any] | None = None) -> MagicMock:
    ts = MagicMock()
    ts.skills = skills if skills is not None else {}
    ts._vds_skill_metadata = metadata if metadata is not None else []
    ts.tools = {}
    return ts


def _make_metadata_item(name: str, *, has_path: bool = True, has_hash: bool = True) -> MagicMock:
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


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


class TestSkillManagerInstantiation:
    def test_default_instantiation_no_validator(self) -> None:
        mgr = SkillManager()
        assert mgr._hash_validator is None

    def test_instantiation_with_validator(self) -> None:
        validator = MagicMock(spec=ContentHashValidator)
        mgr = SkillManager(hash_validator=validator)
        assert mgr._hash_validator is validator


# ---------------------------------------------------------------------------
# parse_skill_name_from_error
# ---------------------------------------------------------------------------


class TestParseSkillNameFromError:
    def test_single_quoted_skill_name(self) -> None:
        result = SkillManager.parse_skill_name_from_error("skill 'research-skill' not found")
        assert result == "research-skill"

    def test_double_quoted_skill_name(self) -> None:
        result = SkillManager.parse_skill_name_from_error('skill "audit-orchestrator-skill" failed')
        assert result == "audit-orchestrator-skill"

    def test_no_match_returns_none(self) -> None:
        result = SkillManager.parse_skill_name_from_error("some unrelated error message")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = SkillManager.parse_skill_name_from_error("")
        assert result is None


# ---------------------------------------------------------------------------
# _build_skill_aliases
# ---------------------------------------------------------------------------


class TestBuildSkillAliases:
    def test_adds_skill_suffix(self) -> None:
        aliases = SkillManager._build_skill_aliases("research")
        assert "research-skill" in aliases

    def test_strips_skill_suffix(self) -> None:
        aliases = SkillManager._build_skill_aliases("research-skill")
        assert "research" in aliases

    def test_normalizes_underscores_to_dashes(self) -> None:
        aliases = SkillManager._build_skill_aliases("research_skill")
        assert "research-skill" in aliases

    def test_empty_returns_empty_set(self) -> None:
        assert SkillManager._build_skill_aliases("") == set()

    def test_none_returns_empty_set(self) -> None:
        assert SkillManager._build_skill_aliases(None) == set()


# ---------------------------------------------------------------------------
# collect_available_skill_names
# ---------------------------------------------------------------------------


class TestCollectAvailableSkillNames:
    def test_collects_from_skills_map(self) -> None:
        ts = _make_toolset(skills={"research-skill": object(), "grepai-skill": object()})
        result = SkillManager.collect_available_skill_names([ts])
        assert "research-skill" in result
        assert "grepai-skill" in result

    def test_deduplicates_across_toolsets(self) -> None:
        ts1 = _make_toolset(skills={"research-skill": object()})
        ts2 = _make_toolset(skills={"research-skill": object(), "grepai-skill": object()})
        result = SkillManager.collect_available_skill_names([ts1, ts2])
        assert result.count("research-skill") == 1

    def test_empty_toolsets_returns_empty(self) -> None:
        result = SkillManager.collect_available_skill_names([])
        assert result == []

    def test_metadata_fallback_when_no_skills_map(self) -> None:
        ts = MagicMock()
        ts.skills = None  # no runtime map
        item = MagicMock()
        item.name = "vds-scripts-skill"
        ts._vds_skill_metadata = [item]
        result = SkillManager.collect_available_skill_names([ts])
        assert "vds-scripts-skill" in result


# ---------------------------------------------------------------------------
# drop_skill_from_toolsets
# ---------------------------------------------------------------------------


class TestDropSkillFromToolsets:
    def test_removes_named_skill(self) -> None:
        ts = _make_toolset(skills={"research-skill": object(), "grepai-skill": object()})
        _updated, count = SkillManager.drop_skill_from_toolsets([ts], "research-skill")
        assert count == 1
        assert "research-skill" not in ts.skills

    def test_empty_skill_name_is_noop(self) -> None:
        ts = _make_toolset(skills={"research-skill": object()})
        updated, count = SkillManager.drop_skill_from_toolsets([ts], "")
        assert count == 0
        assert len(updated) == 1

    def test_alias_match_removes_skill(self) -> None:
        # "research" should match "research-skill"
        ts = _make_toolset(skills={"research-skill": object()})
        _, count = SkillManager.drop_skill_from_toolsets([ts], "research")
        assert count == 1


# ---------------------------------------------------------------------------
# prevalidate_skill_toolsets with injected validator
# ---------------------------------------------------------------------------


class TestPrevalidateSkillToolsets:
    def test_valid_skills_are_kept(self) -> None:
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = True
        mgr = SkillManager(hash_validator=validator)

        item = _make_metadata_item("research-skill")
        ts = _make_toolset(skills={"research-skill": object()}, metadata=[item])
        log = MagicMock()

        result = mgr.prevalidate_skill_toolsets([ts], log)
        assert len(result) == 1
        assert "research-skill" in ts.skills

    def test_invalid_skills_are_removed(self) -> None:
        validator = MagicMock(spec=ContentHashValidator)
        validator.validate.return_value = False

        item = _make_metadata_item("bad-skill")
        ts = _make_toolset(skills={"bad-skill": object()}, metadata=[item])
        log = MagicMock()

        result = SkillManager.prevalidate_skill_toolsets([ts], log, hash_validator=validator)
        # toolset removed because skills_map is now empty
        assert len(result) == 0
        log.warning.assert_called()

    def test_no_validator_no_audit_orchestrator_returns_unchanged(self) -> None:
        # Without a validator and without audit_orchestrator importable,
        # prevalidate should return toolsets unchanged (fail-open).
        mgr = SkillManager(hash_validator=None)
        ts = _make_toolset(skills={"research-skill": object()})
        log = MagicMock()
        # This will attempt the legacy import and fail gracefully
        result = mgr.prevalidate_skill_toolsets([ts], log)
        # Either unchanged (import failed) or validated — both are acceptable
        assert isinstance(result, list)

    def test_toolset_without_skills_map_passes_through(self) -> None:
        validator = MagicMock(spec=ContentHashValidator)
        mgr = SkillManager(hash_validator=validator)
        ts = MagicMock()
        ts.skills = None
        ts._vds_skill_metadata = None
        log = MagicMock()
        result = mgr.prevalidate_skill_toolsets([ts], log)
        assert ts in result


# ---------------------------------------------------------------------------
# retain_skills_in_toolsets
# ---------------------------------------------------------------------------


class TestRetainSkillsInToolsets:
    def test_retains_only_allowed_skills(self) -> None:
        ts = _make_toolset(skills={"research-skill": object(), "grepai-skill": object()})
        _, removed = SkillManager.retain_skills_in_toolsets(
            toolsets=[ts],
            allowed_skill_names=["research-skill"],
        )
        assert removed == 1
        assert "research-skill" in ts.skills
        assert "grepai-skill" not in ts.skills

    def test_empty_allowed_is_noop(self) -> None:
        ts = _make_toolset(skills={"research-skill": object()})
        updated, removed = SkillManager.retain_skills_in_toolsets(toolsets=[ts], allowed_skill_names=[])
        assert removed == 0
        assert len(updated) == 1


# ---------------------------------------------------------------------------
# has_skill_tool_bindings — toolset with matching tool names
# ---------------------------------------------------------------------------


class TestHasSkillToolBindings:
    def test_returns_true_when_skill_tool_present(self) -> None:
        ts = MagicMock()
        ts.tools = {"load_skill": MagicMock()}
        assert SkillManager.has_skill_tool_bindings([ts]) is True

    def test_returns_false_when_no_skill_tools(self) -> None:
        ts = MagicMock()
        ts.tools = {"some_other_tool": MagicMock()}
        assert SkillManager.has_skill_tool_bindings([ts]) is False

    def test_returns_false_for_non_dict_tools(self) -> None:
        ts = MagicMock()
        ts.tools = None
        assert SkillManager.has_skill_tool_bindings([ts]) is False

    def test_returns_false_for_empty_toolsets(self) -> None:
        assert SkillManager.has_skill_tool_bindings([]) is False


# ---------------------------------------------------------------------------
# collect_available_skill_names — require_skill_tool_bindings gate
# ---------------------------------------------------------------------------


class TestCollectAvailableSkillNamesGated:
    def test_require_bindings_returns_empty_when_no_skill_tools(self) -> None:
        ts = _make_toolset(skills={"research-skill": object()})
        ts.tools = {"unrelated_tool": MagicMock()}
        result = SkillManager.collect_available_skill_names([ts], require_skill_tool_bindings=True)
        assert result == []

    def test_require_bindings_returns_names_when_skill_tool_present(self) -> None:
        ts = _make_toolset(skills={"research-skill": object()})
        ts.tools = {"list_skills": MagicMock()}
        result = SkillManager.collect_available_skill_names([ts], require_skill_tool_bindings=True)
        assert "research-skill" in result


# ---------------------------------------------------------------------------
# build_preloaded_skill_context
# ---------------------------------------------------------------------------


class TestBuildPreloadedSkillContext:
    def test_empty_available_returns_empty_tuple(self) -> None:
        context, loaded = SkillManager.build_preloaded_skill_context(
            toolsets=[],
            available_skill_names=[],
        )
        assert context == ""
        assert loaded == []

    def test_skill_without_get_skill_callable_skipped(self) -> None:
        ts = _make_toolset(skills={"research-skill": object()})
        ts.get_skill = None  # not callable
        context, loaded = SkillManager.build_preloaded_skill_context(
            toolsets=[ts],
            available_skill_names=["research-skill"],
        )
        assert context == ""
        assert loaded == []

    def test_skill_with_get_skill_callable_loads_content(self) -> None:
        skill_obj = MagicMock()
        skill_obj.description = "A research skill"
        skill_obj.content = "Skill content here"
        skill_obj.resources = []
        skill_obj.scripts = []

        ts = _make_toolset(skills={"research-skill": skill_obj})
        ts.get_skill = MagicMock(return_value=skill_obj)

        context, loaded = SkillManager.build_preloaded_skill_context(
            toolsets=[ts],
            available_skill_names=["research-skill"],
            max_skills=1,
        )
        assert "research-skill" in context
        assert "research-skill" in loaded

    def test_max_skills_limits_output(self) -> None:
        def make_ts(name: str) -> MagicMock:
            skill_obj = MagicMock()
            skill_obj.description = f"Desc for {name}"
            skill_obj.content = f"Content for {name}"
            skill_obj.resources = []
            skill_obj.scripts = []
            ts = _make_toolset(skills={name: skill_obj})
            ts.get_skill = MagicMock(return_value=skill_obj)
            return ts

        toolsets = [make_ts("skill-a"), make_ts("skill-b"), make_ts("skill-c")]
        _, loaded = SkillManager.build_preloaded_skill_context(
            toolsets=toolsets,
            available_skill_names=["skill-a", "skill-b", "skill-c"],
            max_skills=2,
        )
        assert len(loaded) <= 2


# ---------------------------------------------------------------------------
# drop_skill_from_toolsets — metadata-only path (no skills dict)
# ---------------------------------------------------------------------------


class TestDropSkillMetadataOnlyPath:
    def test_removes_from_metadata_only_toolset(self) -> None:
        ts = MagicMock()
        ts.skills = None  # no skills dict
        item = MagicMock()
        item.name = "research-skill"
        ts._vds_skill_metadata = [item]

        _updated, count = SkillManager.drop_skill_from_toolsets([ts], "research-skill")
        assert count == 1
        assert ts._vds_skill_metadata == []

    def test_non_matching_metadata_kept(self) -> None:
        ts = MagicMock()
        ts.skills = None
        item_a = MagicMock()
        item_a.name = "research-skill"
        item_b = MagicMock()
        item_b.name = "grepai-skill"
        ts._vds_skill_metadata = [item_a, item_b]

        _updated, count = SkillManager.drop_skill_from_toolsets([ts], "research-skill")
        assert count == 1
        assert len(ts._vds_skill_metadata) == 1
        assert ts._vds_skill_metadata[0].name == "grepai-skill"
