"""Unit tests for vds_agent_core.config — Wave 1 enums + Wave 2 LLMRuntimeConfig."""

from __future__ import annotations

from vds_agent_core.config import (
    VDS_BASE_SETTINGS_CONFIG,
    AgenticConfig,
    AgentRuntimeMode,
    LangGraphConfig,
    LLMProtocolType,
    LLMRuntimeConfig,
    NonProgressPolicyConfig,
    NonProgressPreset,
)


class TestLLMProtocolType:
    def test_has_expected_members(self) -> None:
        assert LLMProtocolType.ANTHROPIC == "anthropic"
        assert LLMProtocolType.OPENAI == "openai"
        assert LLMProtocolType.GEMINI == "gemini"
        assert LLMProtocolType.OPENAI_CODEX == "openai-codex"

    def test_is_str_enum(self) -> None:
        assert isinstance(LLMProtocolType.OPENAI, str)


class TestAgentRuntimeMode:
    def test_has_pydanticai(self) -> None:
        assert AgentRuntimeMode.PYDANTICAI == "pydanticai"

    def test_is_str_enum(self) -> None:
        assert isinstance(AgentRuntimeMode.PYDANTICAI, str)


class TestNonProgressPreset:
    def test_has_expected_members(self) -> None:
        assert NonProgressPreset.STRICT == "strict"
        assert NonProgressPreset.BALANCED == "balanced"
        assert NonProgressPreset.PERMISSIVE == "permissive"


class TestNonProgressPolicyConfig:
    def test_default_instantiation(self) -> None:
        config = NonProgressPolicyConfig()
        assert config.high_repeat_min_tool_calls == 10
        assert config.high_repeat_max_repeat == 4

    def test_custom_values(self) -> None:
        config = NonProgressPolicyConfig(high_repeat_min_tool_calls=20)
        assert config.high_repeat_min_tool_calls == 20

    def test_field_constraints(self) -> None:
        import pytest

        with pytest.raises(Exception):
            NonProgressPolicyConfig(high_repeat_min_tool_calls=0)  # ge=1


class TestLangGraphConfig:
    def test_default_instantiation(self) -> None:
        config = LangGraphConfig()
        assert config.checkpointer_type == "memory"
        assert config.postgres_dsn is None
        assert config.thread_id_prefix == "audit"

    def test_custom_values(self) -> None:
        config = LangGraphConfig(
            checkpointer_type="postgres",
            postgres_dsn="postgresql://user:pass@host:5432/db",
            thread_id_prefix="progress",
        )
        assert config.checkpointer_type == "postgres"
        assert config.postgres_dsn is not None


class TestVDSBaseSettingsConfig:
    def test_has_required_keys(self) -> None:
        assert "env_file" in VDS_BASE_SETTINGS_CONFIG
        assert "dotenv_filtering" in VDS_BASE_SETTINGS_CONFIG
        assert "env_nested_delimiter" in VDS_BASE_SETTINGS_CONFIG
        assert VDS_BASE_SETTINGS_CONFIG["dotenv_filtering"] == "match_prefix"
        assert VDS_BASE_SETTINGS_CONFIG["env_nested_delimiter"] == "__"


class TestLLMRuntimeConfig:
    def test_default_instantiation(self) -> None:
        cfg = LLMRuntimeConfig()
        assert cfg.enabled is False
        assert cfg.protocol == LLMProtocolType.OPENAI
        assert cfg.agent_runtime_mode == AgentRuntimeMode.PYDANTICAI
        assert cfg.model_standard == "gpt-4o-mini"
        assert cfg.model_complex == "gpt-4o"
        assert cfg.cache_enabled is True

    def test_env_prefix(self) -> None:
        assert LLMRuntimeConfig.model_config.get("env_prefix") == "VDS_AGENT_CORE__"

    def test_dotenv_filtering(self) -> None:
        assert LLMRuntimeConfig.model_config.get("dotenv_filtering") == "match_prefix"

    def test_env_nested_delimiter(self) -> None:
        assert LLMRuntimeConfig.model_config.get("env_nested_delimiter") == "__"

    def test_custom_values(self) -> None:
        cfg = LLMRuntimeConfig(
            enabled=True,
            api_key="test-key",
            base_url="http://localhost:4000",
            model_standard="openai/gpt-4o",
        )
        assert cfg.enabled is True
        assert cfg.api_key == "test-key"
        assert cfg.base_url == "http://localhost:4000"
        assert cfg.model_standard == "openai/gpt-4o"

    def test_is_base_settings(self) -> None:
        from pydantic_settings import BaseSettings

        assert issubclass(LLMRuntimeConfig, BaseSettings)

    def test_timeout_constraints(self) -> None:
        import pytest

        with pytest.raises(Exception):
            LLMRuntimeConfig(agent_timeout_seconds=5.0)  # ge=10.0


class TestAgenticConfig:
    def test_default_instantiation(self) -> None:
        cfg = AgenticConfig()
        assert cfg.enabled is False
        assert cfg.max_turns == 20
        assert cfg.max_tool_calls == 100
        assert cfg.tool_timeout_sec == 30.0
        assert cfg.max_read_bytes == 1_000_000
        assert cfg.max_read_lines == 2000

    def test_custom_max_turns(self) -> None:
        cfg = AgenticConfig(max_turns=50)
        assert cfg.max_turns == 50

    def test_non_progress_preset(self) -> None:
        cfg = AgenticConfig(non_progress_preset=NonProgressPreset.STRICT)
        assert cfg.non_progress_preset == NonProgressPreset.STRICT
        cfg2 = AgenticConfig()
        assert cfg2.non_progress_preset == NonProgressPreset.BALANCED

    def test_tool_allowlists_empty_by_default(self) -> None:
        cfg = AgenticConfig()
        assert cfg.tool_allowlists == {}

    def test_tool_allowlists_custom(self) -> None:
        cfg = AgenticConfig(tool_allowlists={"code": ["read_file", "grep_search"]})
        assert cfg.tool_allowlists["code"] == ["read_file", "grep_search"]
