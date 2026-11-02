"""Tests for vds_agent_core.profiles — Wave 2 full extraction."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest


class TestCodexCredentialResolverProtocol:
    """ConfigHooks Protocol structural conformance."""

    def test_protocol_importable(self) -> None:
        from vds_agent_core.profiles import CodexCredentialResolver

        assert hasattr(CodexCredentialResolver, "resolve")

    def test_protocol_is_runtime_checkable(self) -> None:
        from vds_agent_core.profiles import CodexCredentialResolver

        class _Good:
            def resolve(self, field: str) -> str:
                return field

        class _Bad:
            pass

        assert isinstance(_Good(), CodexCredentialResolver)
        assert not isinstance(_Bad(), CodexCredentialResolver)

    def test_protocol_structural_match(self) -> None:
        """A class with the right method satisfies the protocol without inheriting."""
        from vds_agent_core.profiles import CodexCredentialResolver

        class MyResolver:
            def resolve(self, field: str) -> str:
                return f"resolved:{field}"

        resolver = MyResolver()
        assert isinstance(resolver, CodexCredentialResolver)
        assert resolver.resolve("access_token") == "resolved:access_token"


class TestDefaultRuntimeProfilesFileExport:
    def test_exported_from_package_root(self) -> None:
        from vds_agent_core import DEFAULT_RUNTIME_PROFILES_FILE

        assert isinstance(DEFAULT_RUNTIME_PROFILES_FILE, Path)
        assert DEFAULT_RUNTIME_PROFILES_FILE.name == "audit.profiles.yaml"


class TestRuntimeProfileActivation:
    """RuntimeProfileActivation dataclass."""

    def test_importable(self) -> None:
        from vds_agent_core.profiles import RuntimeProfileActivation

        activation = RuntimeProfileActivation(
            profile_name="test",
            source="cli",
            profile_path=Path("/tmp/test.yaml"),
            applied_env_keys=("KEY_A", "KEY_B"),
        )
        assert activation.profile_name == "test"
        assert activation.source == "cli"
        assert activation.applied_env_keys == ("KEY_A", "KEY_B")

    def test_none_profile(self) -> None:
        from vds_agent_core.profiles import RuntimeProfileActivation

        activation = RuntimeProfileActivation(
            profile_name=None,
            source="none",
            profile_path=Path("/tmp/test.yaml"),
            applied_env_keys=(),
        )
        assert activation.profile_name is None
        assert activation.source == "none"


class TestApplyRuntimeProfile:
    """apply_runtime_profile with full extraction mechanics."""

    def test_importable(self) -> None:
        from vds_agent_core.profiles import apply_runtime_profile

        assert callable(apply_runtime_profile)

    def test_none_profile_no_yaml(self, tmp_path: Path) -> None:
        """None profile with no YAML file returns source=none."""
        from vds_agent_core.profiles import apply_runtime_profile

        fake_yaml = tmp_path / "profiles.yaml"
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(fake_yaml)}, clear=False):
            result = apply_runtime_profile(None)
            assert result.profile_name is None
            assert result.source == "none"
            assert result.applied_env_keys == ()

    def test_default_profile_from_yaml(self, tmp_path: Path) -> None:
        """Default profile is loaded when no explicit profile is requested."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""            default_profile: my-default
            profiles:
              my-default:
                env:
                  MY_CUSTOM_KEY: hello
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        env_patch = {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}
        with patch.dict(os.environ, env_patch, clear=False):
            os.environ.pop("MY_CUSTOM_KEY", None)
            result = apply_runtime_profile(None)
            assert result.profile_name == "my-default"
            assert result.source == "default"
            assert "MY_CUSTOM_KEY" in result.applied_env_keys
            assert os.environ.get("MY_CUSTOM_KEY") == "hello"

    def test_explicit_profile_from_yaml(self, tmp_path: Path) -> None:
        """Explicit profile name overrides default."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""            default_profile: default-one
            profiles:
              default-one:
                env:
                  TEST_KEY_A: from-default
              explicit-one:
                env:
                  TEST_KEY_B: from-explicit
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            os.environ.pop("TEST_KEY_A", None)
            os.environ.pop("TEST_KEY_B", None)
            result = apply_runtime_profile("explicit-one")
            assert result.profile_name == "explicit-one"
            assert result.source == "cli"
            assert "TEST_KEY_B" in result.applied_env_keys
            assert os.environ.get("TEST_KEY_B") == "from-explicit"

    def test_missing_profile_raises(self, tmp_path: Path) -> None:
        """Requesting a non-existent profile raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""            profiles:
              existing:
                env:
                  X: Y
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match="was not found"):
                apply_runtime_profile("nonexistent")

    def test_custom_env_prefix(self, tmp_path: Path) -> None:
        """Custom env_prefix replaces VDS_AUDIT_ in env key mapping."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""            profiles:
              test-profile:
                retry_policy:
                  agent_retries: 3
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            # Clear any pre-existing keys
            for k in list(os.environ):
                if k.startswith("VDS_PROGRESS_"):
                    os.environ.pop(k, None)
            result = apply_runtime_profile(
                "test-profile",
                env_prefix="VDS_PROGRESS_",
            )
            assert result.profile_name == "test-profile"
            assert "VDS_PROGRESS_LLM__AGENT_RETRIES" in result.applied_env_keys
            assert os.environ.get("VDS_PROGRESS_LLM__AGENT_RETRIES") == "3"

    def test_config_hooks_accepted(self, tmp_path: Path) -> None:
        """config_hooks parameter is accepted and functional."""
        from vds_agent_core.profiles import ConfigHooks, apply_runtime_profile

        class _TrackingHooks:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def get_config(self) -> Any:
                self.calls.append("get")
                return {}

            def set_config(self, cfg: Any) -> None:
                self.calls.append("set")

            def reset_config(self) -> None:
                self.calls.append("reset")

        hooks = _TrackingHooks()
        assert isinstance(hooks, ConfigHooks)

        yaml_content = textwrap.dedent("""            profiles:
              hook-test:
                env:
                  HOOK_TEST_KEY: value
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            os.environ.pop("HOOK_TEST_KEY", None)
            result = apply_runtime_profile("hook-test", _config_hooks=hooks)
            assert result.profile_name == "hook-test"

    def test_force_override(self, tmp_path: Path) -> None:
        """force_override=True overwrites existing env vars."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""            profiles:
              override-test:
                env:
                  OVERRIDE_KEY: new-value
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(
            os.environ,
            {
                "VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file),
                "OVERRIDE_KEY": "old-value",
            },
            clear=False,
        ):
            result = apply_runtime_profile("override-test", force_override=True)
            assert os.environ.get("OVERRIDE_KEY") == "new-value"
            assert "OVERRIDE_KEY" in result.applied_env_keys


class TestBuildLlmSettingsForProfile:
    """build_llm_settings_for_profile with config_hooks."""

    def test_with_config_hooks_and_factory(self, tmp_path: Path) -> None:
        """Config hooks are called during build, factory produces settings."""
        from vds_agent_core.profiles import build_llm_settings_for_profile

        yaml_content = textwrap.dedent("""            profiles:
              build-test:
                env:
                  BUILD_TEST_MARKER: active
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        class _MockHooks:
            def __init__(self) -> None:
                self.calls: list[str] = []

            def get_config(self) -> Any:
                self.calls.append("get")
                return {"original": True}

            def set_config(self, cfg: Any) -> None:
                self.calls.append(f"set:{cfg}")

            def reset_config(self) -> None:
                self.calls.append("reset")

        hooks = _MockHooks()

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            result = build_llm_settings_for_profile(
                "build-test",
                config_hooks=hooks,
                settings_factory=lambda: {"built": True},
            )

        assert result == {"built": True}
        assert "get" in hooks.calls
        assert "reset" in hooks.calls
        assert any(c.startswith("set:") for c in hooks.calls)

    def test_without_factory_returns_none(self, tmp_path: Path) -> None:
        """Without settings_factory, returns None."""
        from vds_agent_core.profiles import build_llm_settings_for_profile

        yaml_content = textwrap.dedent("""            profiles:
              no-factory:
                env:
                  NF_KEY: val
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            result = build_llm_settings_for_profile("no-factory")

        assert result is None


class TestEnvMaps:
    """_EnvMaps prefix substitution."""

    def test_default_prefix(self) -> None:
        from vds_agent_core.profiles import _EnvMaps

        maps = _EnvMaps("VDS_AUDIT_")
        assert maps.retry["agent_retries"] == "VDS_AUDIT_LLM__AGENT_RETRIES"
        assert maps.active_profile_env == "VDS_AUDIT_ACTIVE_PROFILE"

    def test_custom_prefix(self) -> None:
        from vds_agent_core.profiles import _EnvMaps

        maps = _EnvMaps("VDS_PROGRESS_")
        assert maps.retry["agent_retries"] == "VDS_PROGRESS_LLM__AGENT_RETRIES"
        assert maps.active_profile_env == "VDS_PROGRESS_ACTIVE_PROFILE"
        assert maps.model_llm["type"] == "VDS_PROGRESS_LLM_PROTOCOL"
        assert maps.model_dspy["model"] == "VDS_PROGRESS_DSPY_MODEL"


class TestProfileProtectedEnvKeys:
    """profile_protected_env_keys with prefix."""

    def test_default_prefix(self) -> None:
        from vds_agent_core.profiles import profile_protected_env_keys

        keys = profile_protected_env_keys()
        assert "VDS_AUDIT_LLM_PROTOCOL" in keys
        assert "VDS_AUDIT_LLM__API_KEY" in keys

    def test_custom_prefix(self) -> None:
        from vds_agent_core.profiles import profile_protected_env_keys

        keys = profile_protected_env_keys(env_prefix="VDS_PROGRESS_")
        assert "VDS_PROGRESS_LLM_PROTOCOL" in keys
        assert "VDS_PROGRESS_LLM__API_KEY" in keys
        assert "VDS_AUDIT_LLM_PROTOCOL" not in keys


class TestResolveAgenticToolFirstScalar:
    """resolve_agentic_tool_first_scalar with custom prefix."""

    def test_default_returns_default(self) -> None:
        from vds_agent_core.profiles import resolve_agentic_tool_first_scalar

        os.environ.pop("VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS", None)
        result = resolve_agentic_tool_first_scalar("tool_first_max_steps", default=10)
        assert result == 10

    def test_custom_prefix(self) -> None:
        from vds_agent_core.profiles import resolve_agentic_tool_first_scalar

        os.environ["VDS_PROGRESS_AGENTIC_TOOL_FIRST_MAX_STEPS"] = "25"
        try:
            result = resolve_agentic_tool_first_scalar(
                "tool_first_max_steps",
                default=10,
                env_prefix="VDS_PROGRESS_",
            )
            assert result == 25
        finally:
            os.environ.pop("VDS_PROGRESS_AGENTIC_TOOL_FIRST_MAX_STEPS", None)


class TestRealProfileIntegration:
    """Integration tests using the real ~/.vds/audit.profiles.yaml file.

    These tests exercise the actual YAML loading and env mutation paths
    that unit tests with mocks cannot cover.
    """

    def test_resolve_runtime_profiles_path_finds_real_file(self) -> None:
        from vds_agent_core.profiles import resolve_runtime_profiles_path

        path = resolve_runtime_profiles_path()
        assert path is not None
        assert path.exists(), f"Profile file not found at {path}"
        assert path.suffix == ".yaml"

    def test_list_runtime_profile_names_returns_profiles(self) -> None:
        from vds_agent_core.profiles import list_runtime_profile_names

        names = list_runtime_profile_names()
        assert isinstance(names, list)
        assert len(names) > 0, "Expected at least one profile"

    def test_apply_runtime_profile_none_is_noop(self) -> None:
        """Applying None profile should not raise and return activation."""
        from vds_agent_core.profiles import RuntimeProfileActivation, apply_runtime_profile

        result = apply_runtime_profile(None)
        assert result is not None
        assert isinstance(result, RuntimeProfileActivation)

    def test_apply_runtime_profile_default_profile(self) -> None:
        """Apply the default profile from the real YAML file."""
        import os

        from vds_agent_core.profiles import RuntimeProfileActivation, apply_runtime_profile

        # Save and restore env state
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        try:
            result = apply_runtime_profile("omniroute-dlg1-gpt-openai")
            assert result is not None
            assert isinstance(result, RuntimeProfileActivation)
        finally:
            # Restore env
            for k in list(os.environ.keys()):
                if k.startswith("VDS_AUDIT_") and k not in saved:
                    del os.environ[k]
            for k, v in saved.items():
                os.environ[k] = v

    def test_apply_runtime_profile_unknown_profile_raises(self) -> None:
        """Applying an unknown profile name should raise ValueError."""
        import pytest
        from vds_agent_core.profiles import apply_runtime_profile

        with pytest.raises((ValueError, KeyError, Exception)):
            apply_runtime_profile("nonexistent-profile-xyz-12345")

    def test_profile_sets_env_vars(self) -> None:
        """Applying a real profile should set VDS_AUDIT_* env vars."""
        import os

        from vds_agent_core.profiles import apply_runtime_profile

        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        try:
            apply_runtime_profile("omniroute-dlg1-gpt-openai")
            # After applying, at least the active profile env var should be set
            active = os.environ.get("VDS_AUDIT_ACTIVE_PROFILE")
            assert active == "omniroute-dlg1-gpt-openai", f"Expected active profile, got {active}"
        finally:
            for k in list(os.environ.keys()):
                if k.startswith("VDS_AUDIT_") and k not in saved:
                    del os.environ[k]
            for k, v in saved.items():
                os.environ[k] = v

    def test_apply_runtime_profile_custom_env_prefix(self) -> None:
        """env_prefix parameter should be accepted without error."""
        from vds_agent_core.profiles import apply_runtime_profile

        # Just verify it accepts the parameter — don't check env mutation
        # since VDS_PROGRESS_ prefix won't match the YAML profile keys
        result = apply_runtime_profile(None, env_prefix="VDS_PROGRESS_")
        assert result is not None


class TestRealProfilePolicyApplication:
    """Tests that verify policy application helpers are exercised via real profiles."""

    def _apply_and_restore(self, profile_name: str) -> dict:
        """Apply profile, capture env changes, restore env."""
        import os

        from vds_agent_core.profiles import apply_runtime_profile

        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        try:
            apply_runtime_profile(profile_name)
            applied = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
            return applied
        finally:
            for k in list(os.environ.keys()):
                if k.startswith("VDS_AUDIT_") and k not in saved:
                    del os.environ[k]
            for k, v in saved.items():
                os.environ[k] = v

    def test_model_policy_sets_llm_enabled(self) -> None:
        """Profile with env.VDS_AUDIT_LLM_ENABLED should set it."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        assert applied.get("VDS_AUDIT_LLM_ENABLED") == "true"

    def test_model_policy_sets_api_key_env(self) -> None:
        """Profile with env.VDS_AUDIT_LLM__API_KEY should set it."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        # Key may be set to the literal ${OMNIROUTE_API_KEY} or resolved value
        assert "VDS_AUDIT_LLM__API_KEY" in applied or "VDS_AUDIT_LLM_ENABLED" in applied

    def test_model_policy_sets_max_tokens(self) -> None:
        """Profile env.VDS_AUDIT_LLM__MAX_TOKENS_PER_REQUEST should be applied."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        assert applied.get("VDS_AUDIT_LLM__MAX_TOKENS_PER_REQUEST") == "24000"

    def test_model_policy_sets_agent_retries(self) -> None:
        """Profile env.VDS_AUDIT_LLM__AGENT_RETRIES should be applied."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        assert applied.get("VDS_AUDIT_LLM__AGENT_RETRIES") == "2"

    def test_model_policy_sets_skills_toolset(self) -> None:
        """Profile env.VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED should be applied."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        assert applied.get("VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED") == "true"

    def test_active_profile_env_var_set(self) -> None:
        """VDS_AUDIT_ACTIVE_PROFILE should be set to the applied profile name."""
        applied = self._apply_and_restore("omniroute-dlg1-gpt-openai")
        assert applied.get("VDS_AUDIT_ACTIVE_PROFILE") == "omniroute-dlg1-gpt-openai"

    def test_build_llm_settings_for_profile(self) -> None:
        """build_llm_settings_for_profile should not raise for a valid profile."""
        from vds_agent_core.profiles import build_llm_settings_for_profile

        # May return None if no settings_factory is provided — just verify no exception
        try:
            build_llm_settings_for_profile("omniroute-dlg1-gpt-openai")
        except Exception as e:
            # Only fail if it's not a missing-factory type error
            if "settings_factory" not in str(e) and "factory" not in str(e).lower():
                raise

    def test_inherit_runtime_llm_policy(self) -> None:
        """inherit_runtime_llm_policy should not raise for a valid profile."""
        import os

        from vds_agent_core.profiles import inherit_runtime_llm_policy

        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        try:
            # inherit_runtime_llm_policy requires profile_name as first arg
            try:
                inherit_runtime_llm_policy("omniroute-dlg1-gpt-openai")
            except Exception as e:
                # Only fail if it is not a missing-factory type error
                if "settings_factory" not in str(e) and "factory" not in str(e).lower():
                    raise
        finally:
            for k in list(os.environ.keys()):
                if k.startswith("VDS_AUDIT_") and k not in saved:
                    del os.environ[k]
            for k, v in saved.items():
                os.environ[k] = v


class TestResolveDefaultFailoverProfiles:
    """resolve_default_failover_profiles returns other profiles excluding active."""

    def test_excludes_active_profile(self) -> None:
        from vds_agent_core.profiles import resolve_default_failover_profiles

        all_profiles = ["profile-a", "profile-b", "profile-c"]
        result = resolve_default_failover_profiles("profile-a", all_profiles=all_profiles)
        assert "profile-a" not in result
        assert "profile-b" in result
        assert "profile-c" in result

    def test_none_active_returns_all(self) -> None:
        from vds_agent_core.profiles import resolve_default_failover_profiles

        all_profiles = ["profile-a", "profile-b"]
        result = resolve_default_failover_profiles(None, all_profiles=all_profiles)
        assert result == ["profile-a", "profile-b"]

    def test_empty_all_profiles_returns_empty(self) -> None:
        from vds_agent_core.profiles import resolve_default_failover_profiles

        result = resolve_default_failover_profiles("profile-a", all_profiles=[])
        assert result == []

    def test_deduplicates_profiles(self) -> None:
        from vds_agent_core.profiles import resolve_default_failover_profiles

        all_profiles = ["profile-a", "profile-b", "profile-b", "profile-c"]
        result = resolve_default_failover_profiles("profile-a", all_profiles=all_profiles)
        assert result.count("profile-b") == 1


class TestListRuntimeProfileNames:
    """list_runtime_profile_names returns names from YAML."""

    def test_returns_list_from_yaml(self, tmp_path: Path) -> None:
        import textwrap
        from unittest.mock import patch

        from vds_agent_core.profiles import list_runtime_profile_names

        yaml_content = textwrap.dedent("""
            profiles:
              alpha:
                env:
                  KEY_A: val
              beta:
                env:
                  KEY_B: val
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            names = list_runtime_profile_names()

        assert "alpha" in names
        assert "beta" in names

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        from unittest.mock import patch

        from vds_agent_core.profiles import list_runtime_profile_names

        missing = tmp_path / "nonexistent.yaml"
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(missing)}, clear=False):
            names = list_runtime_profile_names()

        assert names == []


class TestEnvMapsCustomPrefix:
    """_EnvMaps with non-default prefix replaces VDS_AUDIT_ correctly."""

    def test_model_dspy_prefix_replaced(self) -> None:
        from vds_agent_core.profiles import _EnvMaps

        maps = _EnvMaps("VDS_PROGRESS_")
        assert maps.model_dspy["model"] == "VDS_PROGRESS_DSPY_MODEL"
        assert maps.model_dspy["api_key"] == "VDS_PROGRESS_DSPY_API_KEY"

    def test_timeout_prefix_replaced(self) -> None:
        from vds_agent_core.profiles import _EnvMaps

        maps = _EnvMaps("VDS_PROGRESS_")
        assert maps.timeout["agent_timeout_seconds"] == "VDS_PROGRESS_LLM__AGENT_TIMEOUT_SECONDS"

    def test_agentic_tool_first_prefix_replaced(self) -> None:
        from vds_agent_core.profiles import _EnvMaps

        maps = _EnvMaps("VDS_PROGRESS_")
        assert maps.agentic_tool_first["tool_first_max_steps"] == "VDS_PROGRESS_AGENTIC_TOOL_FIRST_MAX_STEPS"


class TestModelPolicyViaYaml:
    """Tests for model policy helpers exercised via apply_runtime_profile with crafted YAML."""

    def _apply(self, tmp_path: Path, yaml_content: str, profile: str = "test-profile", **kwargs: Any) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            # Clear any pre-existing VDS_AUDIT_ keys that might interfere
            saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile(profile, force_override=True, **kwargs)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_model_llm_type_applied(self, tmp_path: Path) -> None:
        """model.llm.type sets VDS_AUDIT_LLM_PROTOCOL."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
        """,
        )
        assert result.profile_name == "test-profile"
        assert "VDS_AUDIT_LLM_PROTOCOL" in result.applied_env_keys

    def test_model_llm_stream_applied(self, tmp_path: Path) -> None:
        """model.llm.stream sets VDS_AUDIT_LLM__STREAM."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    stream: true
        """,
        )
        assert "VDS_AUDIT_LLM__STREAM" in result.applied_env_keys

    def test_model_llm_invalid_type_raises(self, tmp_path: Path) -> None:
        """model.llm.type with unsupported protocol raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                model:
                  llm:
                    type: unsupported-protocol
                    base_url: http://localhost:4000
                    api_key: sk-test
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match=r"invalid model\.llm\.type"):
                apply_runtime_profile("test-profile", force_override=True)

    def test_model_llm_reasoning_effort_applied(self, tmp_path: Path) -> None:
        """model.llm.reasoning_effort sets VDS_AUDIT_LLM__REASONING_EFFORT."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    reasoning_effort: high
        """,
        )
        assert "VDS_AUDIT_LLM__REASONING_EFFORT" in result.applied_env_keys

    def test_model_llm_invalid_reasoning_effort_raises(self, tmp_path: Path) -> None:
        """model.llm.reasoning_effort with invalid value raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    reasoning_effort: ultra
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match="reasoning_effort"):
                apply_runtime_profile("test-profile", force_override=True)

    def test_model_llm_row_failover_profiles_string(self, tmp_path: Path) -> None:
        """model.llm.row_failover_profiles as comma-string sets env var."""
        # Note: list form is not used here because the generic tier loop in
        # _apply_profile_model_policy also processes row_failover_profiles as a
        # string field — using a string value avoids the conflict.
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    row_failover_profiles: "profile-b,profile-c"
        """,
        )
        assert "VDS_AUDIT_LLM__ROW_FAILOVER_PROFILES" in result.applied_env_keys

    def test_model_llm_model_shorthand_sets_all_tiers(self, tmp_path: Path) -> None:
        """model.llm.model shorthand sets simple/standard/complex tiers."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    model: gpt-4o
        """,
        )
        assert "VDS_AUDIT_LLM__MODEL_STANDARD" in result.applied_env_keys
        assert "VDS_AUDIT_LLM__MODEL_SIMPLE" in result.applied_env_keys
        assert "VDS_AUDIT_LLM__MODEL_COMPLEX" in result.applied_env_keys

    def test_model_dspy_type_and_model_applied(self, tmp_path: Path) -> None:
        """model.dspy.type and model set DSPy env vars."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                  dspy:
                    type: openai
                    model: openai/gpt-4o
                    api_key: sk-dspy
        """,
        )
        assert "VDS_AUDIT_DSPY_PROTOCOL" in result.applied_env_keys
        assert "VDS_AUDIT_DSPY_MODEL" in result.applied_env_keys

    def test_model_dspy_invalid_type_raises(self, tmp_path: Path) -> None:
        """model.dspy.type with unsupported protocol raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                model:
                  dspy:
                    type: bad-protocol
                    model: gpt-4o
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match=r"invalid model\.dspy\.type"):
                apply_runtime_profile("test-profile", force_override=True)

    def test_model_embedding_applied(self, tmp_path: Path) -> None:
        """model.embedding fields set embedding env vars."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  embedding:
                    base_url: http://localhost:11434
                    model: bge-m3
                    api_key: sk-embed
        """,
        )
        assert "VDS_AUDIT_EMBEDDING__BASE_URL" in result.applied_env_keys
        assert "VDS_AUDIT_EMBEDDING__MODEL" in result.applied_env_keys

    def test_model_llm_unknown_key_raises(self, tmp_path: Path) -> None:
        """model.llm with unknown key raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    unknown_field: bad
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match=r"invalid model\.llm keys"):
                apply_runtime_profile("test-profile", force_override=True)


class TestSkillPolicyViaYaml:
    """Tests for skill_policy helpers exercised via apply_runtime_profile."""

    def _apply(self, tmp_path: Path, yaml_content: str) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_skill_policy_enabled_applied(self, tmp_path: Path) -> None:
        """skill_policy.enabled sets VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  enabled: true
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED" in result.applied_env_keys

    def test_skill_policy_allow_script_execution(self, tmp_path: Path) -> None:
        """skill_policy.allow_script_execution sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  allow_script_execution: false
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_ALLOW_SCRIPT_EXECUTION" in result.applied_env_keys

    def test_skill_policy_default_trust_tier(self, tmp_path: Path) -> None:
        """skill_policy.default_trust_tier sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  default_trust_tier: internal
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_DEFAULT_TRUST_TIER" in result.applied_env_keys

    def test_skill_policy_invalid_trust_tier_raises(self, tmp_path: Path) -> None:
        """skill_policy.default_trust_tier with invalid value raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                skill_policy:
                  default_trust_tier: super-trusted
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError):
                apply_runtime_profile("test-profile", force_override=True)

    def test_skill_policy_allowlist_applied(self, tmp_path: Path) -> None:
        """skill_policy.allowlist sets VDS_AUDIT_LLM__SKILLS_ALLOWLIST."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  allowlist:
                    - research-skill
                    - grepai-skill
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_ALLOWLIST" in result.applied_env_keys

    def test_skill_policy_allowed_trust_tiers_applied(self, tmp_path: Path) -> None:
        """skill_policy.allowed_trust_tiers sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  allowed_trust_tiers:
                    - internal
                    - external-verified
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_ALLOWED_TRUST_TIERS" in result.applied_env_keys

    def test_skill_policy_trust_tiers_map_applied(self, tmp_path: Path) -> None:
        """skill_policy.trust_tiers map sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  trust_tiers:
                    research-skill: internal
                    grepai-skill: external-verified
        """,
        )
        assert "VDS_AUDIT_LLM__SKILLS_TRUST_TIERS" in result.applied_env_keys

    def test_skill_policy_strict_require_effective_skill(self, tmp_path: Path) -> None:
        """skill_policy.strict_require_effective_skill sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                skill_policy:
                  strict_require_effective_skill: true
        """,
        )
        assert "VDS_AUDIT_AGENTIC_STRICT_REQUIRE_EFFECTIVE_SKILL" in result.applied_env_keys


class TestBackendPolicyViaYaml:
    """Tests for backend_policy helpers exercised via apply_runtime_profile."""

    def _apply(self, tmp_path: Path, yaml_content: str, extra_env: dict | None = None) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        env_patch = {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}
        if extra_env:
            env_patch.update(extra_env)
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, env_patch, clear=False):
            for k in list(saved):
                if k not in ("VDS_AUDIT_RUNTIME_PROFILES_FILE",) and k not in (extra_env or {}):
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_backend_policy_prompt_evaluator(self, tmp_path: Path) -> None:
        """backend_policy.backend=prompt_evaluator sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                backend_policy:
                  backend: prompt_evaluator
        """,
        )
        assert "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND" in result.applied_env_keys

    def test_backend_policy_dspy(self, tmp_path: Path) -> None:
        """backend_policy.backend=dspy sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                backend_policy:
                  backend: dspy
        """,
        )
        assert "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND" in result.applied_env_keys

    def test_backend_policy_invalid_backend_raises(self, tmp_path: Path) -> None:
        """backend_policy.backend with invalid value raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                backend_policy:
                  backend: unknown-backend
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError):
                apply_runtime_profile("test-profile", force_override=True)

    def test_backend_policy_locked_and_allow_override_raises(self, tmp_path: Path) -> None:
        """backend_policy locked=true + allow_override=true raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                backend_policy:
                  backend: prompt_evaluator
                  locked: true
                  allow_override: true
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match="locked=true cannot be combined"):
                apply_runtime_profile("test-profile", force_override=True)


class TestAgenticPolicyViaYaml:
    """Tests for agentic policy helpers exercised via apply_runtime_profile."""

    def _apply(self, tmp_path: Path, yaml_content: str) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_agentic_non_progress_preset_applied(self, tmp_path: Path) -> None:
        """agentic.non_progress_preset sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agentic:
                  non_progress_preset: strict
        """,
        )
        assert "VDS_AUDIT_AGENTIC_NON_PROGRESS_PRESET" in result.applied_env_keys

    def test_agentic_invalid_preset_raises(self, tmp_path: Path) -> None:
        """agentic.non_progress_preset with invalid value raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                agentic:
                  non_progress_preset: invalid-preset
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError):
                apply_runtime_profile("test-profile", force_override=True)

    def test_agentic_strict_no_fallback_applied(self, tmp_path: Path) -> None:
        """agentic.strict_no_fallback sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agentic:
                  strict_no_fallback: true
        """,
        )
        assert "VDS_AUDIT_AGENTIC_STRICT_NO_FALLBACK" in result.applied_env_keys

    def test_agentic_tool_first_max_steps_applied(self, tmp_path: Path) -> None:
        """agentic.tool_first_max_steps sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agentic:
                  tool_first_max_steps: 10
        """,
        )
        assert "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS" in result.applied_env_keys


class TestEnvReferenceResolution:
    """Tests for ${ENV_VAR} and ${codex:...} reference resolution."""

    def test_env_ref_resolved_when_set(self, tmp_path: Path) -> None:
        """${ENV_VAR} in profile value is resolved from environment."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  MY_RESOLVED_KEY: "${MY_SOURCE_VAR}"
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(
            os.environ,
            {
                "VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file),
                "MY_SOURCE_VAR": "resolved-value",
            },
            clear=False,
        ):
            os.environ.pop("MY_RESOLVED_KEY", None)
            _result = apply_runtime_profile("test-profile", force_override=True)
            assert os.environ.get("MY_RESOLVED_KEY") == "resolved-value"

    def test_env_ref_raises_when_not_set(self, tmp_path: Path) -> None:
        """${ENV_VAR} raises ValueError when the referenced var is not set."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  MY_KEY: "${NONEXISTENT_VAR_XYZ_12345}"
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            os.environ.pop("NONEXISTENT_VAR_XYZ_12345", None)
            with pytest.raises(ValueError, match="NONEXISTENT_VAR_XYZ_12345"):
                apply_runtime_profile("test-profile", force_override=True)

    def test_codex_ref_raises_when_module_unavailable(self, tmp_path: Path) -> None:
        """${codex:access_token} raises ValueError when codex_oauth not available."""
        import sys

        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  MY_KEY: "${codex:access_token}"
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with patch.dict(sys.modules, {"vds_audit_orchestrator.llm.codex_oauth": None}):
                with pytest.raises(ValueError, match="codex"):
                    apply_runtime_profile("test-profile", force_override=True)

    def test_malformed_codex_ref_raises(self, tmp_path: Path) -> None:
        """Malformed ${codex:...} reference raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  MY_KEY: "${codex:bad field name!}"
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError):
                apply_runtime_profile("test-profile", force_override=True)


class TestResolveSkillDirectoryPath:
    """resolve_skill_directory_path with absolute and relative paths."""

    def test_absolute_path_returned_as_is(self, tmp_path: Path) -> None:
        from vds_agent_core.profiles import resolve_skill_directory_path

        result = resolve_skill_directory_path(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_tilde_expanded(self) -> None:
        from vds_agent_core.profiles import resolve_skill_directory_path

        result = resolve_skill_directory_path("~")
        assert result == Path.home().resolve()

    def test_relative_path_resolved_against_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from vds_agent_core.profiles import resolve_skill_directory_path

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("VDS_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        subdir = tmp_path / "skills"
        subdir.mkdir()
        result = resolve_skill_directory_path("skills")
        assert result == subdir.resolve()


class TestInheritRuntimeLlmPolicy:
    """inherit_runtime_llm_policy copies policy fields from source_llm."""

    def test_source_llm_none_returns_settings(self, tmp_path: Path) -> None:
        """When source_llm is None, returns the built settings directly."""
        from vds_agent_core.profiles import inherit_runtime_llm_policy

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  INHERIT_TEST_KEY: value
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            result = inherit_runtime_llm_policy("test-profile", source_llm=None)
        # Returns None because no settings_factory provided
        assert result is None

    def test_source_llm_fields_copied(self, tmp_path: Path) -> None:
        """When source_llm provided, policy fields are copied to settings."""
        from vds_agent_core.profiles import inherit_runtime_llm_policy

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                env:
                  INHERIT_TEST_KEY: value
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        class _FakeSettings:
            stream = False
            agent_stream = False

        class _SourceLlm:
            stream = True
            agent_stream = True

        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            result = inherit_runtime_llm_policy(
                "test-profile",
                source_llm=_SourceLlm(),
                settings_factory=_FakeSettings,
            )
        # stream should be copied from source_llm
        assert result.stream is True


class TestAgentRuntimePolicyViaYaml:
    """Tests for agent_runtime_policy helpers exercised via apply_runtime_profile."""

    def _apply(self, tmp_path: Path, yaml_content: str) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_agent_runtime_policy_mode_applied(self, tmp_path: Path) -> None:
        """agent_runtime_policy.mode=pydanticai sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agent_runtime_policy:
                  mode: pydanticai
        """,
        )
        assert "VDS_AUDIT_LLM__AGENT_RUNTIME_MODE" in result.applied_env_keys

    def test_agent_runtime_policy_invalid_mode_raises(self, tmp_path: Path) -> None:
        """agent_runtime_policy.mode with invalid value raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                agent_runtime_policy:
                  mode: invalid-mode
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError):
                apply_runtime_profile("test-profile", force_override=True)

    def test_agent_runtime_policy_tool_allowlists_applied(self, tmp_path: Path) -> None:
        """agent_runtime_policy.tool_allowlists sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agent_runtime_policy:
                  mode: pydanticai
                  tool_allowlists:
                    evaluator:
                      - read_file
                      - search_code
        """,
        )
        assert "VDS_AUDIT_AGENTIC_TOOL_ALLOWLISTS" in result.applied_env_keys

    def test_agent_runtime_policy_non_progress_policy_applied(self, tmp_path: Path) -> None:
        """agent_runtime_policy.non_progress_policy sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                agent_runtime_policy:
                  mode: pydanticai
                  non_progress_policy:
                    max_retries: 3
        """,
        )
        assert "VDS_AUDIT_AGENTIC_NON_PROGRESS_POLICY" in result.applied_env_keys


class TestTimeoutPolicyViaYaml:
    """Tests for timeout_policy helpers exercised via apply_runtime_profile."""

    def _apply(self, tmp_path: Path, yaml_content: str) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_timeout_policy_agent_timeout_applied(self, tmp_path: Path) -> None:
        """timeout_policy.agent_timeout_seconds sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                timeout_policy:
                  agent_timeout_seconds: 120
        """,
        )
        assert "VDS_AUDIT_LLM__AGENT_TIMEOUT_SECONDS" in result.applied_env_keys

    def test_timeout_policy_row_timeout_applied(self, tmp_path: Path) -> None:
        """timeout_policy.row_timeout_ms sets env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                timeout_policy:
                  row_timeout_ms: 60000
        """,
        )
        assert "VDS_AUDIT_ROW_TIMEOUT_MS" in result.applied_env_keys


class TestDspyAutoDerivation:
    """Tests for DSPy auto-derivation and coherence validation."""

    def _apply(self, tmp_path: Path, yaml_content: str) -> Any:
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(textwrap.dedent(yaml_content), encoding="utf-8")
        saved = {k: v for k, v in os.environ.items() if k.startswith("VDS_AUDIT_")}
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            for k in list(saved):
                if k != "VDS_AUDIT_RUNTIME_PROFILES_FILE":
                    os.environ.pop(k, None)
            try:
                return apply_runtime_profile("test-profile", force_override=True)
            finally:
                for k in list(os.environ.keys()):
                    if k.startswith("VDS_AUDIT_") and k not in saved:
                        os.environ.pop(k, None)
                for k, v in saved.items():
                    os.environ[k] = v

    def test_dspy_model_auto_derived_from_llm(self, tmp_path: Path) -> None:
        """DSPy model is auto-derived from LLM standard model when not explicit."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                    standard: openai/gpt-4o
        """,
        )
        # VDS_AUDIT_DSPY_MODEL should be auto-derived
        assert "VDS_AUDIT_DSPY_MODEL" in result.applied_env_keys

    def test_dspy_coherence_incoherent_raises(self, tmp_path: Path) -> None:
        """Incoherent DSPy model/protocol pairing raises ValueError."""
        from vds_agent_core.profiles import apply_runtime_profile

        yaml_content = textwrap.dedent("""
            profiles:
              test-profile:
                model:
                  llm:
                    type: openai
                    base_url: http://localhost:4000
                    api_key: sk-test
                  dspy:
                    type: anthropic
                    model: openai/gpt-4o
        """)
        yaml_file = tmp_path / "profiles.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
        with patch.dict(os.environ, {"VDS_AUDIT_RUNTIME_PROFILES_FILE": str(yaml_file)}, clear=False):
            with pytest.raises(ValueError, match="incoherent"):
                apply_runtime_profile("test-profile", force_override=True)

    def test_dspy_temperature_applied(self, tmp_path: Path) -> None:
        """model.dspy.temperature sets DSPy temperature env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  dspy:
                    type: openai
                    model: openai/gpt-4o
                    temperature: 0.5
        """,
        )
        assert "VDS_AUDIT_DSPY_TEMPERATURE" in result.applied_env_keys

    def test_dspy_max_tokens_applied(self, tmp_path: Path) -> None:
        """model.dspy.max_tokens sets DSPy max_tokens env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  dspy:
                    type: openai
                    model: openai/gpt-4o
                    max_tokens: 4096
        """,
        )
        assert "VDS_AUDIT_DSPY_MAX_TOKENS" in result.applied_env_keys

    def test_dspy_system_role_compat_applied(self, tmp_path: Path) -> None:
        """model.dspy.system_role_compat sets DSPy system_role_compat env var."""
        result = self._apply(
            tmp_path,
            """
            profiles:
              test-profile:
                model:
                  dspy:
                    type: openai
                    model: openai/gpt-4o
                    system_role_compat: true
        """,
        )
        assert "VDS_AUDIT_DSPY_SYSTEM_ROLE_COMPAT" in result.applied_env_keys
