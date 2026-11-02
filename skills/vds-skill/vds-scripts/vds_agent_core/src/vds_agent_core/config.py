"""Shared config primitives for VDS agent infrastructure.

Wave 1: Enums and simple config models extracted from audit_orchestrator.
Wave 2: LLMRuntimeConfig(BaseSettings) added here.
Wave 3: AgenticConfig added here.

These are the generic, audit-independent config types. Audit-specific
config (AuditConfig, row-failover, Confluence/dispatch fields) stays
in audit_orchestrator/config.py.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Protocol / runtime enums
# ---------------------------------------------------------------------------


class LLMProtocolType(StrEnum):
    """Supported LLM protocols."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENAI_CODEX = "openai-codex"


class AgentRuntimeMode(StrEnum):
    """Supported agent runtime implementations."""

    PYDANTICAI = "pydanticai"


# ---------------------------------------------------------------------------
# LangGraph workflow config
# ---------------------------------------------------------------------------


class LangGraphConfig(BaseModel):
    """LangGraph workflow and checkpointing configuration.

    Supports MemorySaver (in-memory) and PostgresSaver (PostgreSQL) checkpointers
    for durable workflow execution with state persistence and human-in-the-loop.
    """

    checkpointer_type: str = Field(
        default="memory",
        description="Type of checkpointer: 'memory' for local-only debugging, 'postgres' for durable execution",
    )
    postgres_dsn: str | None = Field(
        default=None,
        description="PostgreSQL connection string for PostgresSaver checkpointer",
    )
    thread_id_prefix: str = Field(
        default="audit",
        description="Prefix for auto-generated thread IDs",
    )


# ---------------------------------------------------------------------------
# Non-progress detection policy
# ---------------------------------------------------------------------------


class NonProgressPolicyConfig(BaseModel):
    """Thresholds for repetitive non-progress detection in agentic runs."""

    high_repeat_min_tool_calls: int = Field(default=10, ge=1, le=500)
    high_repeat_max_repeat: int = Field(default=4, ge=1, le=100)
    signature_churn_min_tool_calls: int = Field(default=8, ge=1, le=500)
    signature_churn_min_repeated_signatures: int = Field(default=3, ge=1, le=100)
    signature_churn_max_unique_tools: int = Field(default=3, ge=1, le=100)
    early_directory_churn_min_tool_calls: int = Field(default=5, ge=1, le=500)
    early_directory_churn_min_list_directory_calls: int = Field(default=3, ge=1, le=100)
    early_directory_churn_max_grep_calls: int = Field(default=1, ge=0, le=100)
    directory_dominance_min_tool_calls: int = Field(default=12, ge=1, le=500)
    directory_dominance_min_list_directory_calls: int = Field(default=6, ge=1, le=200)
    directory_dominance_ratio: float = Field(default=0.4, ge=0.0, le=1.0)
    low_signal_loop_min_tool_calls: int = Field(default=8, ge=1, le=500)
    low_signal_loop_max_unique_tools: int = Field(default=4, ge=1, le=100)
    low_signal_loop_min_dominant_tool_calls: int = Field(default=4, ge=1, le=100)
    dominant_repetition_min_tool_calls: int = Field(default=10, ge=1, le=500)
    dominant_repetition_max_unique_tools: int = Field(default=4, ge=1, le=100)
    dominant_repetition_min_dominant_tool_calls: int = Field(default=5, ge=1, le=200)
    dominant_repetition_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    high_volume_repetition_min_tool_calls: int = Field(default=20, ge=1, le=1000)
    high_volume_repetition_max_unique_tools: int = Field(default=8, ge=1, le=200)
    high_volume_repetition_min_dominant_tool_calls: int = Field(default=8, ge=1, le=200)
    high_volume_repetition_ratio: float = Field(default=0.3, ge=0.0, le=1.0)
    skill_churn_min_tool_calls: int = Field(default=8, ge=1, le=500)
    skill_churn_min_list_skills_calls: int = Field(default=3, ge=1, le=100)
    fallback_single_tool_min_tool_calls: int = Field(default=6, ge=1, le=500)
    fallback_single_tool_max_unique_tools: int = Field(default=1, ge=1, le=100)


class NonProgressPreset(StrEnum):
    """Named non-progress sensitivity presets (FR-84)."""

    STRICT = "strict"
    BALANCED = "balanced"
    PERMISSIVE = "permissive"


# ---------------------------------------------------------------------------
# Shared base settings config — used by LLMRuntimeConfig and subclasses.
# Exported so audit_orchestrator.config.LLMConfig can reference it in Wave 3.
# ---------------------------------------------------------------------------

# pydantic-settings 2.13 accepts ``dotenv_filtering`` at runtime, but the
# ``SettingsConfigDict`` TypedDict has not declared it yet — silence the
# spurious ``typeddict-unknown-key`` while keeping the runtime contract.
VDS_BASE_SETTINGS_CONFIG: SettingsConfigDict = SettingsConfigDict(  # type: ignore[typeddict-unknown-key]
    env_file="~/.vds/.env",
    env_file_encoding="utf-8",
    extra="ignore",
    dotenv_filtering="match_prefix",
    env_nested_delimiter="__",
)


# ---------------------------------------------------------------------------
# LLM Runtime Config (Wave 2)
# ---------------------------------------------------------------------------


class LLMRuntimeConfig(BaseSettings):
    """Shared LLM runtime configuration for all VDS orchestrators.

    Uses pydantic-settings BaseSettings for automatic env var loading.
    env_prefix="VDS_AGENT_CORE__" — override in subclasses for package-specific
    namespaces (e.g., audit uses "VDS_AUDIT__").

    Config precedence (highest → lowest):
    1. CLI flags (via model_validate({...}) at call site)
    2. Environment variables (VDS_AGENT_CORE__*)
    3. Shared env file (~/.vds/.env)
    4. Defaults below
    """

    model_config = SettingsConfigDict(
        env_prefix="VDS_AGENT_CORE__",
        **VDS_BASE_SETTINGS_CONFIG,
    )

    # --- Provider ---
    enabled: bool = Field(default=False, description="Master switch for LLM features")
    protocol: LLMProtocolType = Field(default=LLMProtocolType.OPENAI)
    agent_runtime_mode: AgentRuntimeMode = Field(default=AgentRuntimeMode.PYDANTICAI)
    api_key: str | None = Field(default=None, description="LLM provider API key")
    base_url: str | None = Field(default=None, description="LLM provider base URL")

    # --- Streaming ---
    stream: bool = Field(default=True, description="Enable streaming for LLM calls")
    agent_stream: bool = Field(default=True, description="Enable streaming for agent LLM calls")
    reasoning_effort: str | None = Field(
        default=None,
        description="Reasoning effort override: none|minimal|low|medium|high|xhigh",
    )

    # --- Model tiers ---
    model_simple: str = Field(default="gpt-4o-mini", description="Model for simple/fast tasks")
    model_standard: str = Field(default="gpt-4o-mini", description="Model for standard tasks")
    model_complex: str = Field(default="gpt-4o", description="Model for complex reasoning tasks")

    # --- Cost / tokens ---
    max_cost_per_run: float = Field(default=2.00, description="Maximum cost per run in USD")
    max_tokens_per_request: int = Field(default=12000, description="Maximum tokens per LLM request")

    # --- Cache ---
    cache_enabled: bool = Field(default=True, description="Enable LLM response caching")
    cache_ttl_hours: int = Field(default=24, description="Cache TTL in hours")

    # --- Retries / timeouts ---
    agent_retries: int = Field(default=2, ge=0, description="Model retries for agent calls")
    output_retries: int = Field(default=1, ge=0, description="Output validation retries")
    agent_timeout_seconds: float = Field(
        default=1200.0,
        ge=10.0,
        description="Base timeout for agent LLM calls in seconds",
    )
    agent_timeout_max_seconds: float = Field(
        default=3600.0,
        ge=60.0,
        description="Maximum timeout for agent LLM calls in seconds",
    )
    agent_rate_limit_retry_attempts: int = Field(
        default=5,
        ge=0,
        description="Retries for transient provider rate-limit responses",
    )
    agent_rate_limit_retry_backoff_seconds: float = Field(
        default=1.5,
        ge=0.1,
        description="Base exponential backoff for rate-limit retries",
    )
    agent_idle_timeout_seconds: float = Field(
        default=360.0,
        ge=10.0,
        description="Abort when no event progress occurs",
    )

    # --- Event tracing ---
    agent_event_stream_enabled: bool = Field(default=True, description="Enable agent event streaming")
    agent_trace_payload_enabled: bool = Field(default=False, description="Log full trace payloads")

    # --- Skills / toolsets ---
    mcp_toolsets_enabled: bool = Field(default=False, description="Enable MCP toolsets for agents")
    skills_toolset_enabled: bool = Field(default=False, description="Enable AgentSkills toolset")
    skills_directories: list[str] = Field(default_factory=list, description="Skill directories")
    skills_allowlist: list[str] = Field(default_factory=list, description="Allowed skill names")


# ---------------------------------------------------------------------------
# Agentic execution config (Wave 3)
# ---------------------------------------------------------------------------


class AgenticConfig(BaseModel):
    """Agentic execution configuration for bounded tool-enabled runs.

    Default tool_allowlists are empty — host app provides presets.
    audit_orchestrator.config.AgenticConfig inherits from this and adds
    audit-specific defaults.
    """

    enabled: bool = Field(default=False, description="Enable agentic tool-enabled mode")
    max_turns: int = Field(default=20, ge=1, description="Maximum agent turns")
    max_tool_calls: int = Field(default=100, ge=1, description="Maximum tool calls per run")
    tool_timeout_sec: float = Field(default=30.0, ge=1.0, description="Per-tool call timeout")
    safe_extensions: list[str] = Field(
        default_factory=lambda: [".py", ".java", ".ts", ".js", ".md", ".yaml", ".toml", ".json"],
        description="File extensions safe to read",
    )
    max_read_bytes: int = Field(default=1_000_000, ge=1024, description="Max bytes per file read")
    max_read_lines: int = Field(default=2000, ge=10, description="Max lines per file read")
    non_progress_preset: NonProgressPreset = Field(
        default=NonProgressPreset.BALANCED,
        description="Non-progress detection sensitivity preset",
    )
    non_progress_policy: NonProgressPolicyConfig = Field(
        default_factory=NonProgressPolicyConfig,
        description="Fine-grained non-progress detection thresholds",
    )
    tool_allowlists: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Per-agent tool allowlists. Empty = no restriction. Host app provides presets.",
    )
