"""Coverage uplift for vds_agent_core.profiles (W5.4).

Targets uncovered branches in private validators and public utility functions.
All tests are behavior contracts — no env mutations without monkeypatch.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

# Public API under test
# Private validators — tested directly for coverage
from vds_agent_core.profiles import (
    _derive_dspy_model,
    _resolve_dspy_expected_prefix,
    _validate_agent_runtime_mode,
    _validate_agent_tool_allowlists,
    _validate_non_progress_preset,
    _validate_row_backend_value,
    _validate_skill_directory_list,
    _validate_skill_name_list,
    _validate_skill_trust_tier,
    _validate_skill_trust_tier_list,
    _validate_skill_trust_tier_map,
    is_agent_allowed_for_profile,
    list_runtime_profile_names,
    resolve_agentic_tool_first_scalar,
    resolve_default_failover_profiles,
    resolve_skill_directory_path,
)

# ---------------------------------------------------------------------------
# list_runtime_profile_names — line 354 (empty/invalid profile entry skipped)
# ---------------------------------------------------------------------------


class TestListRuntimeProfileNames:
    def test_skips_empty_name_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        profiles_file = tmp_path / "audit.profiles.yaml"
        profiles_file.write_text(
            yaml.dump({"profiles": {"": {"model": {}}, "real-profile": {"model": {}}}}),
            encoding="utf-8",
        )
        monkeypatch.setenv("VDS_RUNTIME_PROFILES_FILE", str(profiles_file))
        # Patch resolve_runtime_profiles_path to return our file
        import vds_agent_core.profiles as mod
        monkeypatch.setattr(mod, "resolve_runtime_profiles_path", lambda: profiles_file)
        names = list_runtime_profile_names()
        assert "real-profile" in names
        assert "" not in names

    def test_skips_non_dict_payload_entry(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        profiles_file = tmp_path / "audit.profiles.yaml"
        profiles_file.write_text(
            yaml.dump({"profiles": {"invalid": "not-a-dict", "valid": {"model": {}}}}),
            encoding="utf-8",
        )
        import vds_agent_core.profiles as mod
        monkeypatch.setattr(mod, "resolve_runtime_profiles_path", lambda: profiles_file)
        names = list_runtime_profile_names()
        assert "valid" in names
        assert "invalid" not in names


# ---------------------------------------------------------------------------
# resolve_default_failover_profiles — line 365 (deduplication + active skip)
# ---------------------------------------------------------------------------


class TestResolveDefaultFailoverProfiles:
    def test_excludes_active_profile(self) -> None:
        result = resolve_default_failover_profiles("fast", all_profiles=["fast", "default", "ultra"])
        assert "fast" not in result
        assert "default" in result

    def test_deduplicates(self) -> None:
        result = resolve_default_failover_profiles("fast", all_profiles=["default", "default", "ultra"])
        assert result.count("default") == 1

    def test_skips_empty_names(self) -> None:
        result = resolve_default_failover_profiles("fast", all_profiles=["", "default", "  "])
        assert "" not in result
        assert "   " not in result
        assert "default" in result

    def test_reads_from_file_when_all_profiles_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        profiles_file = tmp_path / "audit.profiles.yaml"
        profiles_file.write_text(
            yaml.dump({"profiles": {"fast": {}, "default": {}}}),
            encoding="utf-8",
        )
        import vds_agent_core.profiles as mod
        monkeypatch.setattr(mod, "resolve_runtime_profiles_path", lambda: profiles_file)
        result = resolve_default_failover_profiles("fast")
        assert "default" in result


# ---------------------------------------------------------------------------
# resolve_agentic_tool_first_scalar — lines 393-396 (error + zero int)
# ---------------------------------------------------------------------------


class TestResolveAgenticToolFirstScalar:
    def test_returns_default_when_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS", raising=False)
        result = resolve_agentic_tool_first_scalar("tool_first_max_steps", default=5)
        assert result == 5

    def test_returns_default_on_invalid_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS", "not-a-number")
        result = resolve_agentic_tool_first_scalar("tool_first_max_steps", default=5)
        assert result == 5

    def test_returns_zero_for_zero_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS", "0")
        result = resolve_agentic_tool_first_scalar("tool_first_max_steps", default=5)
        assert result == 0

    def test_bounds_clamping(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # tool_first_max_steps max is 200 from the bounds table
        monkeypatch.setenv("VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS", "999")
        result = resolve_agentic_tool_first_scalar("tool_first_max_steps", default=5)
        assert result <= 200


# ---------------------------------------------------------------------------
# is_agent_allowed_for_profile — lines 857, 863 (non-str pattern skip, glob match)
# ---------------------------------------------------------------------------


class TestIsAgentAllowedForProfile:
    def _profile(self, allowed_agents: Any) -> dict[str, Any]:
        return {"allowed_agents": allowed_agents}

    def test_non_string_pattern_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Line 857: non-str pattern in list → continue; no match → False
        profiles = {"default": self._profile([123, None, "agent-*"])}
        result = is_agent_allowed_for_profile("default", "agent-42", profiles=profiles)
        assert result is True  # "agent-*" still matches

    def test_glob_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Line 863: fnmatch match → True
        profiles = {"default": self._profile(["audit-*", "research-*"])}
        assert is_agent_allowed_for_profile("default", "audit-loop-v2", profiles=profiles)
        assert not is_agent_allowed_for_profile("default", "unknown-agent", profiles=profiles)

    def test_non_list_allowed_agents_raises(self) -> None:
        from vds_agent_core.profiles import ProfileValidationError
        profiles = {"default": {"allowed_agents": "not-a-list"}}
        with pytest.raises(ProfileValidationError):
            is_agent_allowed_for_profile("default", "any-agent", profiles=profiles)


# ---------------------------------------------------------------------------
# resolve_skill_directory_path — line 857, 863
# ---------------------------------------------------------------------------


class TestResolveSkillDirectoryPath:
    def test_absolute_path_resolved_directly(self, tmp_path: Path) -> None:
        result = resolve_skill_directory_path(tmp_path)
        assert result == tmp_path.resolve()

    def test_relative_resolves_from_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("VDS_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        (tmp_path / "skills").mkdir()
        result = resolve_skill_directory_path("skills")
        assert result == (tmp_path / "skills").resolve()

    def test_relative_resolves_from_vds_project_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        monkeypatch.setenv("VDS_PROJECT_DIR", str(tmp_path))
        result = resolve_skill_directory_path("skills")
        assert result == skills_dir.resolve()


# ---------------------------------------------------------------------------
# _validate_skill_trust_tier — lines 1596, 1610, 1612
# ---------------------------------------------------------------------------


class TestValidateSkillTrustTier:
    def test_valid_tier(self) -> None:
        result = _validate_skill_trust_tier(
            profile_name="test", key="tier", raw_value="internal"
        )
        assert result == "internal"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="expected trust-tier"):
            _validate_skill_trust_tier(profile_name="test", key="tier", raw_value=42)

    def test_invalid_tier_string_raises(self) -> None:
        with pytest.raises(ValueError, match="allowed:"):
            _validate_skill_trust_tier(profile_name="test", key="tier", raw_value="admin")


class TestValidateSkillTrustTierList:
    def test_valid_list(self) -> None:
        result = _validate_skill_trust_tier_list(
            profile_name="test", key="tiers", raw_value=["internal", "external-verified"]
        )
        assert "internal" in result

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="expected list"):
            _validate_skill_trust_tier_list(profile_name="test", key="tiers", raw_value="internal")

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_skill_trust_tier_list(profile_name="test", key="tiers", raw_value=[])

    def test_deduplicates(self) -> None:
        result = _validate_skill_trust_tier_list(
            profile_name="test", key="tiers", raw_value=["internal", "internal"]
        )
        assert result.count("internal") == 1


class TestValidateSkillNameList:
    def test_valid_list(self) -> None:
        result = _validate_skill_name_list(
            profile_name="test", key="names", raw_value=["research-skill", "grepai-skill"]
        )
        assert result == ["research-skill", "grepai-skill"]

    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="expected list"):
            _validate_skill_name_list(profile_name="test", key="names", raw_value="research")

    def test_empty_string_item_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_skill_name_list(profile_name="test", key="names", raw_value=[""])

    def test_non_string_item_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_skill_name_list(profile_name="test", key="names", raw_value=[42])


class TestValidateSkillDirectoryList:
    def test_non_list_raises(self) -> None:
        with pytest.raises(ValueError, match="expected list"):
            _validate_skill_directory_list(profile_name="test", key="dirs", raw_value="not-a-list")

    def test_empty_list_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_skill_directory_list(profile_name="test", key="dirs", raw_value=[])

    def test_non_string_item_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_skill_directory_list(profile_name="test", key="dirs", raw_value=[42])

    def test_valid_absolute_path(self, tmp_path: Path) -> None:
        result = _validate_skill_directory_list(
            profile_name="test", key="dirs", raw_value=[str(tmp_path)]
        )
        assert str(tmp_path.resolve()) in result


class TestValidateSkillTrustTierMap:
    def test_valid_map(self) -> None:
        result = _validate_skill_trust_tier_map(
            profile_name="test",
            key="trust_tiers",
            raw_value={"research-skill": "internal"},
        )
        assert result["research-skill"] == "internal"

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="expected object map"):
            _validate_skill_trust_tier_map(profile_name="test", key="trust_tiers", raw_value=[])

    def test_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_skill_trust_tier_map(
                profile_name="test", key="trust_tiers", raw_value={"": "internal"}
            )


# ---------------------------------------------------------------------------
# _validate_row_backend_value — lines 1755, 1807
# ---------------------------------------------------------------------------


class TestValidateRowBackendValue:
    def test_valid_backend(self) -> None:
        result = _validate_row_backend_value(
            profile_name="test", key="backend", raw_value="prompt_evaluator"
        )
        assert result == "prompt_evaluator"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="expected backend string"):
            _validate_row_backend_value(profile_name="test", key="backend", raw_value=42)

    def test_invalid_backend_raises(self) -> None:
        with pytest.raises(ValueError, match="allowed:"):
            _validate_row_backend_value(
                profile_name="test", key="backend", raw_value="invalid-backend"
            )


# ---------------------------------------------------------------------------
# _validate_agent_runtime_mode — lines 1821, 1825, 1829
# ---------------------------------------------------------------------------


class TestValidateAgentRuntimeMode:
    def test_valid_mode(self) -> None:
        result = _validate_agent_runtime_mode(
            profile_name="test", key="mode", raw_value="pydanticai"
        )
        assert result == "pydanticai"

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="expected runtime mode string"):
            _validate_agent_runtime_mode(profile_name="test", key="mode", raw_value=True)

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="allowed:"):
            _validate_agent_runtime_mode(
                profile_name="test", key="mode", raw_value="langchain"
            )


# ---------------------------------------------------------------------------
# _validate_agent_tool_allowlists — lines 1835, 1848
# ---------------------------------------------------------------------------


class TestValidateAgentToolAllowlists:
    def test_valid_allowlist(self) -> None:
        result = _validate_agent_tool_allowlists(
            profile_name="test",
            key="tool_allowlists",
            raw_value={"audit-agent": ["run_tool", "read_file"]},
        )
        assert "audit-agent" in result
        assert "run_tool" in result["audit-agent"]

    def test_non_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="expected object map"):
            _validate_agent_tool_allowlists(
                profile_name="test", key="tool_allowlists", raw_value=["not", "dict"]
            )

    def test_empty_agent_key_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_agent_tool_allowlists(
                profile_name="test", key="tool_allowlists", raw_value={"": ["tool"]}
            )

    def test_non_list_tools_raises(self) -> None:
        with pytest.raises(ValueError, match="expected list"):
            _validate_agent_tool_allowlists(
                profile_name="test", key="tool_allowlists", raw_value={"agent": "not-a-list"}
            )

    def test_empty_tool_name_raises(self) -> None:
        with pytest.raises(ValueError, match="expected non-empty string"):
            _validate_agent_tool_allowlists(
                profile_name="test", key="tool_allowlists", raw_value={"agent": [""]}
            )

    def test_deduplicates_tool_names(self) -> None:
        result = _validate_agent_tool_allowlists(
            profile_name="test",
            key="tool_allowlists",
            raw_value={"agent": ["read_file", "read_file"]},
        )
        assert result["agent"].count("read_file") == 1


# ---------------------------------------------------------------------------
# _validate_non_progress_preset — lines 1894
# ---------------------------------------------------------------------------


class TestValidateNonProgressPreset:
    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="expected preset string"):
            _validate_non_progress_preset(profile_name="test", key="preset", raw_value=42)

    def test_invalid_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="allowed:"):
            _validate_non_progress_preset(
                profile_name="test", key="preset", raw_value="invalid-preset"
            )


# ---------------------------------------------------------------------------
# _derive_dspy_model + _resolve_dspy_expected_prefix — lines 1942-1961
# ---------------------------------------------------------------------------


class TestDeriveDspyModel:
    def test_empty_model_returns_empty(self) -> None:
        result = _derive_dspy_model(protocol="anthropic", llm_model_standard="")
        assert result == ""

    def test_gemini_google_prefix_converted(self) -> None:
        result = _derive_dspy_model(protocol="gemini", llm_model_standard="google/gemini-2.0")
        assert result == "gemini/gemini-2.0"

    def test_gemini_already_prefixed_kept(self) -> None:
        result = _derive_dspy_model(protocol="gemini", llm_model_standard="gemini/2.0-flash")
        assert result == "gemini/2.0-flash"

    def test_gemini_no_slash_gets_prefix(self) -> None:
        result = _derive_dspy_model(protocol="gemini", llm_model_standard="gemini-2.0-flash")
        assert result == "gemini/gemini-2.0-flash"

    def test_gemini_with_foreign_prefix_kept(self) -> None:
        result = _derive_dspy_model(protocol="gemini", llm_model_standard="openai/some-model")
        assert result == "openai/some-model"

    def test_model_with_slash_returned_unchanged(self) -> None:
        result = _derive_dspy_model(protocol="anthropic", llm_model_standard="anthropic/claude-3")
        assert result == "anthropic/claude-3"

    def test_no_slash_gets_protocol_prefix(self) -> None:
        result = _derive_dspy_model(protocol="anthropic", llm_model_standard="claude-3-sonnet")
        assert result == "anthropic/claude-3-sonnet"


class TestResolveDspyExpectedPrefix:
    def test_openai_codex_maps_to_openai(self) -> None:
        assert _resolve_dspy_expected_prefix(protocol="openai-codex") == "openai"

    def test_gemini_maps_to_gemini(self) -> None:
        assert _resolve_dspy_expected_prefix(protocol="gemini") == "gemini"

    def test_other_protocol_returned_as_is(self) -> None:
        assert _resolve_dspy_expected_prefix(protocol="anthropic") == "anthropic"
        assert _resolve_dspy_expected_prefix(protocol="openai") == "openai"
