"""Runtime profile activation — extracted core mechanics.

Loads YAML-based runtime profiles and applies env-var overrides for LLM,
retry, timeout, skill, backend, and agentic policies. The ``env_prefix``
parameter makes env-key mapping injectable so non-audit agents can reuse the
same profile engine with their own prefix.

The optional ``ConfigHooks`` and ``CodexCredentialResolver`` protocols allow
callers to inject config access and Codex credential resolution behavior
without importing audit-specific modules into ``vds_agent_core``.
"""

from __future__ import annotations

import contextlib
import contextvars
import copy
import fnmatch
import json
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

import structlog
import yaml
from vds_cli_common.env import load_shared_env
from vds_cli_common.paths import get_vds_config_root

logger = structlog.get_logger(__name__)

DEFAULT_RUNTIME_PROFILES_FILE = get_vds_config_root() / "audit.profiles.yaml"


# ---------------------------------------------------------------------------
# ConfigHooks Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ConfigHooks(Protocol):
    """Injectable config access for profile build operations.

    Implementations provide get/set/reset for the caller's config system,
    allowing build_llm_settings_for_profile to snapshot and restore config
    without importing a specific config module.
    """

    def get_config(self) -> Any: ...
    def set_config(self, cfg: Any) -> None: ...
    def reset_config(self) -> None: ...


# ---------------------------------------------------------------------------
# Env-map tables — parameterized by _make_env_key(prefix, suffix)
# ---------------------------------------------------------------------------


def _make_env_map(prefix: str, mapping: dict[str, str]) -> dict[str, str]:
    """Replace the default VDS_AUDIT_ prefix in env keys with the given prefix."""
    result: dict[str, str] = {}
    for key, env_key in mapping.items():
        result[key] = env_key.replace("VDS_AUDIT_", prefix) if prefix != "VDS_AUDIT_" else env_key
    return result


# Default env maps (VDS_AUDIT_ prefix) — used as templates
_DEFAULT_RETRY_POLICY_ENV_MAP: dict[str, str] = {
    "agent_retries": "VDS_AUDIT_LLM__AGENT_RETRIES",
    "output_retries": "VDS_AUDIT_LLM__OUTPUT_RETRIES",
}
_RETRY_POLICY_BOUNDS: dict[str, tuple[float, float, type[int] | type[float]]] = {
    "agent_retries": (0, 6, int),
    "output_retries": (0, 6, int),
}
_DEFAULT_TIMEOUT_POLICY_ENV_MAP: dict[str, str] = {
    "agent_timeout_seconds": "VDS_AUDIT_LLM__AGENT_TIMEOUT_SECONDS",
    "agent_timeout_max_seconds": "VDS_AUDIT_LLM__AGENT_TIMEOUT_MAX_SECONDS",
    "agent_timeout_extension_seconds": "VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_SECONDS",
    "agent_timeout_extension_attempts": "VDS_AUDIT_LLM__AGENT_TIMEOUT_EXTENSION_ATTEMPTS",
    "agent_timeout_heartbeat_seconds": "VDS_AUDIT_LLM__AGENT_TIMEOUT_HEARTBEAT_SECONDS",
    "agent_idle_timeout_seconds": "VDS_AUDIT_LLM__AGENT_IDLE_TIMEOUT_SECONDS",
    "row_timeout_ms": "VDS_AUDIT_ROW_TIMEOUT_MS",
    "batch_timeout_ms": "VDS_AUDIT_BATCH_TIMEOUT_MS",
    "row_progress_lease_seconds": "VDS_AUDIT_TIMEOUT_POLICY__ROW_PROGRESS_LEASE_SECONDS",
    "row_stall_detection_seconds": "VDS_AUDIT_TIMEOUT_POLICY__ROW_STALL_DETECTION_SECONDS",
    "row_absolute_timeout_ms": "VDS_AUDIT_TIMEOUT_POLICY__ROW_ABSOLUTE_TIMEOUT_MS",
    "row_timeout_progress_extension_enabled": "VDS_AUDIT_ROW_TIMEOUT_PROGRESS_EXTENSION_ENABLED",
    "row_timeout_progress_retry_attempts": "VDS_AUDIT_ROW_TIMEOUT_PROGRESS_RETRY_ATTEMPTS",
    "row_timeout_progress_extension_ms": "VDS_AUDIT_ROW_TIMEOUT_PROGRESS_EXTENSION_MS",
    "row_timeout_progress_max_ms": "VDS_AUDIT_ROW_TIMEOUT_PROGRESS_MAX_MS",
}
_TIMEOUT_POLICY_BOUNDS: dict[str, tuple[float, float, type[int] | type[float]]] = {
    "agent_timeout_seconds": (30.0, 3600.0, float),
    "agent_timeout_max_seconds": (60.0, 7200.0, float),
    "agent_timeout_extension_seconds": (0.0, 1800.0, float),
    "agent_timeout_extension_attempts": (0, 10, int),
    "agent_timeout_heartbeat_seconds": (5.0, 300.0, float),
    "agent_idle_timeout_seconds": (30.0, 1800.0, float),
    "row_timeout_ms": (1000, 600000, int),
    "batch_timeout_ms": (1000, 7200000, int),
    "row_progress_lease_seconds": (0, 1800, int),
    "row_stall_detection_seconds": (1, 900, int),
    "row_absolute_timeout_ms": (1000, 3600000, int),
    "row_timeout_progress_extension_enabled": (0, 1, int),
    "row_timeout_progress_retry_attempts": (0, 5, int),
    "row_timeout_progress_extension_ms": (1000, 300000, int),
    "row_timeout_progress_max_ms": (1000, 1800000, int),
}
_SKILL_TRUST_TIERS: tuple[str, ...] = ("internal", "external-verified", "external-unverified")
_DEFAULT_SKILL_POLICY_ENV_MAP: dict[str, str] = {
    "enabled": "VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED",
    "directories": "VDS_AUDIT_LLM__SKILLS_DIRECTORIES",
    "allow_script_execution": "VDS_AUDIT_LLM__SKILLS_ALLOW_SCRIPT_EXECUTION",
    "default_trust_tier": "VDS_AUDIT_LLM__SKILLS_DEFAULT_TRUST_TIER",
    "allowed_trust_tiers": "VDS_AUDIT_LLM__SKILLS_ALLOWED_TRUST_TIERS",
    "allowlist": "VDS_AUDIT_LLM__SKILLS_ALLOWLIST",
    "trust_tiers": "VDS_AUDIT_LLM__SKILLS_TRUST_TIERS",
    "strict_require_effective_skill": "VDS_AUDIT_AGENTIC_STRICT_REQUIRE_EFFECTIVE_SKILL",
}
_SKILL_POLICY_MAX_LIST_ITEMS = 200
_SKILL_POLICY_MAX_MAP_ITEMS = 200
_DEFAULT_ROW_BACKEND_POLICY_ENV_MAP: dict[str, str] = {
    "backend": "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND",
    "source": "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_SOURCE",
    "locked": "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_LOCKED",
    "allow_override": "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_ALLOW_OVERRIDE",
}
_DEFAULT_ROW_BACKEND_OVERRIDE_REQUEST_ENV = "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_OVERRIDE"
_ROW_EVALUATION_BACKENDS: tuple[str, ...] = ("prompt_evaluator", "dspy")
_DEFAULT_AGENT_RUNTIME_MODE_ENV = "VDS_AUDIT_LLM__AGENT_RUNTIME_MODE"
_AGENT_RUNTIME_MODES: tuple[str, ...] = ("pydanticai",)
_DEFAULT_AGENT_RUNTIME_POLICY_ENV_MAP: dict[str, str] = {
    "tool_allowlists": "VDS_AUDIT_AGENTIC_TOOL_ALLOWLISTS",
    "non_progress_policy": "VDS_AUDIT_AGENTIC_NON_PROGRESS_POLICY",
}
_DEFAULT_AGENTIC_POLICY_ENV_MAP: dict[str, str] = {
    "non_progress_preset": "VDS_AUDIT_AGENTIC_NON_PROGRESS_PRESET",
    "strict_no_fallback": "VDS_AUDIT_AGENTIC_STRICT_NO_FALLBACK",
}
_DEFAULT_AGENTIC_TOOL_FIRST_ENV_MAP: dict[str, str] = {
    "tool_first_max_steps": "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_STEPS",
    "tool_first_timeout_seconds": "VDS_AUDIT_AGENTIC_TOOL_FIRST_TIMEOUT_SECONDS",
    "tool_first_budget_units": "VDS_AUDIT_AGENTIC_TOOL_FIRST_BUDGET_UNITS",
    "tool_first_max_route_transitions": "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_ROUTE_TRANSITIONS",
    "tool_first_max_route_transitions_per_pair": "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_ROUTE_TRANSITIONS_PER_PAIR",
    "tool_calls_limit": "VDS_AUDIT_AGENTIC_TOOL_CALLS_LIMIT",
    "security_tool_calls_limit": "VDS_AUDIT_AGENTIC_SECURITY_TOOL_CALLS_LIMIT",
}
_AGENTIC_TOOL_FIRST_BOUNDS: dict[str, tuple[float, float, type[int] | type[float]]] = {
    "tool_first_max_steps": (1, 50, int),
    "tool_first_timeout_seconds": (1.0, 120.0, float),
    "tool_first_budget_units": (1, 100, int),
    "tool_first_max_route_transitions": (1, 12, int),
    "tool_first_max_route_transitions_per_pair": (1, 12, int),
    "tool_calls_limit": (1, 50, int),
    "security_tool_calls_limit": (1, 100, int),
}
_NON_PROGRESS_PRESETS: tuple[str, ...] = ("strict", "balanced", "permissive")
_DEFAULT_MODEL_POLICY_LLM_ENV_MAP: dict[str, str] = {
    "type": "VDS_AUDIT_LLM_PROTOCOL",
    "base_url": "VDS_AUDIT_LLM__BASE_URL",
    "api_key": "VDS_AUDIT_LLM__API_KEY",
    "stream": "VDS_AUDIT_LLM__STREAM",
    "agent_stream": "VDS_AUDIT_LLM__AGENT_STREAM",
    "row_failover_profiles": "VDS_AUDIT_LLM__ROW_FAILOVER_PROFILES",
    "row_failover_max_provider_hops": "VDS_AUDIT_LLM__ROW_FAILOVER_MAX_PROVIDER_HOPS",
    "reasoning_effort": "VDS_AUDIT_LLM__REASONING_EFFORT",
    "simple": "VDS_AUDIT_LLM__MODEL_SIMPLE",
    "standard": "VDS_AUDIT_LLM__MODEL_STANDARD",
    "complex": "VDS_AUDIT_LLM__MODEL_COMPLEX",
}
_DEFAULT_MODEL_POLICY_DSPY_ENV_MAP: dict[str, str] = {
    "type": "VDS_AUDIT_DSPY_PROTOCOL",
    "model": "VDS_AUDIT_DSPY_MODEL",
    "api_key": "VDS_AUDIT_DSPY_API_KEY",
    "max_tokens": "VDS_AUDIT_DSPY_MAX_TOKENS",
    "temperature": "VDS_AUDIT_DSPY_TEMPERATURE",
    "base_url": "VDS_AUDIT_DSPY_BASE_URL",
    "system_role_compat": "VDS_AUDIT_DSPY_SYSTEM_ROLE_COMPAT",
}
_DEFAULT_MODEL_POLICY_EMBEDDING_ENV_MAP: dict[str, str] = {
    "base_url": "VDS_AUDIT_EMBEDDING__BASE_URL",
    "model": "VDS_AUDIT_EMBEDDING__MODEL",
    "api_key": "VDS_AUDIT_EMBEDDING__API_KEY",
}
_SUPPORTED_PROFILE_PROTOCOLS: tuple[str, ...] = ("anthropic", "openai", "gemini", "openai-codex")
_LLM_REASONING_EFFORT_VALUES: tuple[str, ...] = ("none", "minimal", "low", "medium", "high", "xhigh")
_ENV_REF_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
_ENV_SCHEME_PATTERN = re.compile(r"^\$\{env:([A-Za-z_][A-Za-z0-9_]*)\}$")
_CODEX_REF_PATTERN = re.compile(r"^\$\{codex:([a-z_]+)\}$")

# NFR-225.12: Compile-time allowlist for ${env:VAR} credential references.
# Operators may extend via VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST (JSON array).
_DEFAULT_ENV_CREDENTIAL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "COHERE_API_KEY",
        "VOYAGE_API_KEY",
        "MISTRAL_API_KEY",
        "JINA_API_KEY",
        "HF_TOKEN",
        "INTERNAL_EMBED_API_KEY",
    }
)
_ENV_CREDENTIAL_ALLOWLIST_ENV = "VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST"

# NFR-226.1: One-shot dedup for `profile_embedding_resolved` log emission.
_EMBEDDING_PROFILE_RESOLUTION_SEEN: set[str] = set()
_EMBEDDING_PROFILE_RESOLUTION_LOCK = threading.Lock()
_CODEX_REF_FIELDS: tuple[str, ...] = ("access_token", "account_id", "refresh_token")
_CODEX_CHATGPT_PROFILE_NAME = "codex-chatgpt"
_RUNTIME_PROFILE_BUILD_LOCK = threading.Lock()
_CODEX_CHATGPT_BASELINE_ENV_DEFAULTS: dict[str, str] = {
    "VDS_AUDIT_LLM__SKILLS_TOOLSET_ENABLED": "false",
    "VDS_AUDIT_AGENTIC_ENABLE_SKILLS_TOOLSET": "false",
    "VDS_AUDIT_AGENTIC_SECURITY_ENABLE_SKILLS_TOOLSET": "false",
    "VDS_AUDIT_AGENTIC_STRICT_REQUIRE_EFFECTIVE_SKILL": "false",
    "VDS_AUDIT_AGENTIC_STRICT_NO_FALLBACK": "true",
    "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND": "prompt_evaluator",
    "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_SOURCE": "profile_codex_baseline",
    "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_LOCKED": "false",
    "VDS_AUDIT_LLM__ROW_EVALUATION_BACKEND_ALLOW_OVERRIDE": "false",
    "VDS_AUDIT_LLM__AGENT_RETRIES": "2",
    "VDS_AUDIT_LLM__OUTPUT_RETRIES": "4",
    "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_ROUTE_TRANSITIONS": "6",
    "VDS_AUDIT_AGENTIC_TOOL_FIRST_MAX_ROUTE_TRANSITIONS_PER_PAIR": "2",
    "VDS_AUDIT_LLM__CODE_REVIEW_MAX_TOTAL_CHARS": "200000",
}
_RUNTIME_LLM_POLICY_FIELDS: tuple[str, ...] = (
    "stream",
    "agent_stream",
    "reasoning_effort",
    "max_tokens_per_request",
    "agent_retries",
    "output_retries",
    "agent_timeout_seconds",
    "agent_timeout_max_seconds",
    "agent_timeout_extension_seconds",
    "agent_timeout_extension_attempts",
    "agent_timeout_heartbeat_seconds",
    "agent_rate_limit_retry_attempts",
    "agent_rate_limit_retry_backoff_seconds",
    "agent_idle_timeout_seconds",
    "row_failover_profiles",
    "row_failover_max_provider_hops",
    "row_progress_lease_seconds",
    "row_stall_detection_seconds",
    "row_absolute_timeout_ms",
    "agent_event_stream_enabled",
)
_PROFILE_PROTECTED_ENV_EXTRA_KEYS: tuple[str, ...] = (
    "VDS_AUDIT_LLM__MAX_TOKENS_PER_REQUEST",
    "VDS_AUDIT_AGENTIC_ENABLE_SKILLS_TOOLSET",
    "VDS_AUDIT_AGENTIC_SECURITY_ENABLE_SKILLS_TOOLSET",
)


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RuntimeProfileActivation:
    """Resolved runtime profile activation details."""

    profile_name: str | None
    source: Literal["cli", "default", "none"]
    profile_path: Path
    applied_env_keys: tuple[str, ...]


# ---------------------------------------------------------------------------
# Exceptions (Phase 225 W3 — FR-226.13, FR-226.15, NFR-225.12, NFR-225.13)
# ---------------------------------------------------------------------------


class ProfileValidationError(ValueError):
    """Raised when a profile YAML field fails structural validation (FR-226.13)."""


class CredentialResolutionError(ValueError):
    """Raised when a ``${env:VAR}`` reference targets a non-allowlisted env var (NFR-225.12)."""


class ProfileAuthorizationError(PermissionError):
    """Raised when an agent_id is not allowed to activate a profile (NFR-225.13)."""


# ---------------------------------------------------------------------------
# Env-map builder for custom prefix
# ---------------------------------------------------------------------------


class _EnvMaps:
    """Lazily-built env maps for a given prefix."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.retry = _make_env_map(prefix, _DEFAULT_RETRY_POLICY_ENV_MAP)
        self.timeout = _make_env_map(prefix, _DEFAULT_TIMEOUT_POLICY_ENV_MAP)
        self.skill = _make_env_map(prefix, _DEFAULT_SKILL_POLICY_ENV_MAP)
        self.row_backend = _make_env_map(prefix, _DEFAULT_ROW_BACKEND_POLICY_ENV_MAP)
        self.row_backend_override_env = (
            _DEFAULT_ROW_BACKEND_OVERRIDE_REQUEST_ENV.replace("VDS_AUDIT_", prefix)
            if prefix != "VDS_AUDIT_"
            else _DEFAULT_ROW_BACKEND_OVERRIDE_REQUEST_ENV
        )
        self.agent_runtime_mode_env = (
            _DEFAULT_AGENT_RUNTIME_MODE_ENV.replace("VDS_AUDIT_", prefix)
            if prefix != "VDS_AUDIT_"
            else _DEFAULT_AGENT_RUNTIME_MODE_ENV
        )
        self.agent_runtime = _make_env_map(prefix, _DEFAULT_AGENT_RUNTIME_POLICY_ENV_MAP)
        self.agentic = _make_env_map(prefix, _DEFAULT_AGENTIC_POLICY_ENV_MAP)
        self.agentic_tool_first = _make_env_map(prefix, _DEFAULT_AGENTIC_TOOL_FIRST_ENV_MAP)
        self.model_llm = _make_env_map(prefix, _DEFAULT_MODEL_POLICY_LLM_ENV_MAP)
        self.model_dspy = _make_env_map(prefix, _DEFAULT_MODEL_POLICY_DSPY_ENV_MAP)
        self.model_embedding = _make_env_map(prefix, _DEFAULT_MODEL_POLICY_EMBEDDING_ENV_MAP)
        self.active_profile_env = f"{prefix}ACTIVE_PROFILE"


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def resolve_runtime_profiles_path() -> Path:
    """Resolve profile config path with optional env override."""
    configured_path = os.getenv("VDS_AUDIT_RUNTIME_PROFILES_FILE", "").strip()
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_RUNTIME_PROFILES_FILE


def list_runtime_profile_names() -> list[str]:
    """Return configured runtime profile names in file order."""
    profile_path = resolve_runtime_profiles_path()
    raw: dict[str, Any] = {}
    if profile_path.exists():
        payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            raw = payload
    profiles = raw.get("profiles")
    profiles_map = profiles if isinstance(profiles, dict) else {}
    names: list[str] = []
    for name, payload in profiles_map.items():
        profile_name = str(name).strip()
        if not profile_name or not isinstance(payload, dict):
            continue
        names.append(profile_name)
    return names


def resolve_default_failover_profiles(
    active_profile: str | None,
    all_profiles: list[str] | None = None,
) -> list[str]:
    """Return the default failover profile list for a given active profile."""
    if all_profiles is None:
        all_profiles = list_runtime_profile_names()
    active_stripped = str(active_profile or "").strip()
    result: list[str] = []
    seen: set[str] = set()
    for name in all_profiles:
        name_stripped = str(name or "").strip()
        if not name_stripped or name_stripped == active_stripped or name_stripped in seen:
            continue
        seen.add(name_stripped)
        result.append(name_stripped)
    return result


def resolve_agentic_tool_first_scalar(
    key: str,
    *,
    default: int | float,
    env_prefix: str = "VDS_AUDIT_",
) -> int | float:
    """Resolve bounded agentic scalar env values using runtime-profile limits."""
    maps = _EnvMaps(env_prefix)
    env_key = maps.agentic_tool_first[key]
    min_value, max_value, value_type = _AGENTIC_TOOL_FIRST_BOUNDS[key]
    raw_value = os.getenv(env_key)
    if raw_value is None:
        return default
    try:
        coerced = value_type(raw_value)
    except (TypeError, ValueError):
        return default
    if value_type is int and coerced == 0:
        return 0
    bounded = max(min_value, min(max_value, coerced))
    return int(bounded) if value_type is int else float(bounded)


def profile_protected_env_keys(env_prefix: str = "VDS_AUDIT_") -> tuple[str, ...]:
    """Return env keys whose explicit operator overrides must out-rank profile defaults."""
    maps = _EnvMaps(env_prefix)
    ordered_keys: list[str] = []
    for mapping in (
        maps.model_llm,
        maps.model_dspy,
        maps.model_embedding,
        maps.retry,
        maps.timeout,
        maps.skill,
        maps.row_backend,
        maps.agent_runtime,
        maps.agentic,
        maps.agentic_tool_first,
    ):
        for env_key in mapping.values():
            normalized = str(env_key).strip()
            if normalized and normalized not in ordered_keys:
                ordered_keys.append(normalized)
    extra = _PROFILE_PROTECTED_ENV_EXTRA_KEYS
    if env_prefix != "VDS_AUDIT_":
        extra = tuple(k.replace("VDS_AUDIT_", env_prefix) for k in extra)
    for env_key in extra:
        normalized = str(env_key).strip()
        if normalized and normalized not in ordered_keys:
            ordered_keys.append(normalized)
    return tuple(ordered_keys)


@runtime_checkable
class CodexCredentialResolver(Protocol):
    """Injectable credential resolver for ${codex:...} profile references.

    Audit provides the concrete implementation using codex_oauth.
    Non-audit orchestrators that don't use Codex profiles don't need this.
    """

    def resolve(self, field: str) -> str: ...


# Backward-compatible alias for existing internal references/tests.
CredentialResolver = CodexCredentialResolver


# Context variable for credential resolver — set by apply_runtime_profile,
# read by _resolve_env_reference_if_needed (avoids threading through 18+ call sites)
_credential_resolver_ctx: contextvars.ContextVar[CodexCredentialResolver | None] = contextvars.ContextVar(
    "_credential_resolver_ctx",
    default=None,
)


def apply_runtime_profile(
    requested_profile: str | None,
    *,
    env_prefix: str = "VDS_AUDIT_",
    force_override: bool = False,
    _config_hooks: ConfigHooks | None = None,
    credential_resolver: CodexCredentialResolver | None = None,
    parse_embedding: bool = False,
    embedding_env_prefix: str = "VDS_AGENT_CORE_EMBED__",
) -> RuntimeProfileActivation:
    """Apply runtime profile env overrides before config loading.

    Args:
        requested_profile: Profile name to activate (None = use default from YAML).
        env_prefix: Prefix for env-key mapping (default "VDS_AUDIT_").
        force_override: If True, override already-set env vars.
        _config_hooks: Optional config access hooks for build operations (private param; prefix prevents accidental positional use).
        parse_embedding: If True (W3, FR-226.13), parse the optional
            ``model.embedding`` block and project its fields into env vars under
            ``embedding_env_prefix``. Default ``False`` preserves the FR-225.22
            back-compat lock for existing audit / progress_report consumers.
        embedding_env_prefix: Env prefix for embedding env vars when
            ``parse_embedding`` is true (default ``VDS_AGENT_CORE_EMBED__``,
            matches :class:`EmbeddingSettings` model_config).
    """
    load_shared_env(ensure_defaults=False)

    # Set credential resolver in context for nested call sites
    _credential_resolver_ctx.set(credential_resolver)

    maps = _EnvMaps(env_prefix)
    profile_path = resolve_runtime_profiles_path()
    raw: dict[str, Any] = {}
    if profile_path.exists():
        payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            raw = payload

    profiles = raw.get("profiles")
    profiles_map = profiles if isinstance(profiles, dict) else {}
    default_profile = raw.get("default_profile")
    default_profile_name = str(default_profile).strip() if isinstance(default_profile, str) else ""

    profile_name: str | None = None
    source: Literal["cli", "default", "none"] = "none"
    if requested_profile and requested_profile.strip():
        profile_name = requested_profile.strip()
        source = "cli"
    elif default_profile_name:
        profile_name = default_profile_name
        source = "default"

    if not profile_name:
        return RuntimeProfileActivation(
            profile_name=None,
            source=source,
            profile_path=profile_path,
            applied_env_keys=(),
        )

    profile_payload = profiles_map.get(profile_name)
    if not isinstance(profile_payload, dict):
        raise ValueError(
            f"Runtime profile '{profile_name}' was not found in {profile_path}. Define it under profiles.<name>."
        )

    applied_keys: list[str] = []

    model_payload = profile_payload.get("model")
    model_values = model_payload if isinstance(model_payload, dict) else {}
    _apply_profile_model_policy(
        profile_name=profile_name,
        model_policy_payload=model_values,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )

    env_payload = profile_payload.get("env")
    env_values = env_payload if isinstance(env_payload, dict) else {}
    for key, value in env_values.items():
        env_key = str(key).strip()
        if not env_key:
            continue
        resolved_value = _resolve_env_reference_if_needed(
            profile_name=profile_name,
            key=f"env.{env_key}",
            raw_value=value,
            credential_resolver=credential_resolver,
        )
        if _set_profile_env(env_key, resolved_value, force_override=force_override):
            applied_keys.append(env_key)

    retry_policy_payload = profile_payload.get("retry_policy")
    retry_policy = retry_policy_payload if isinstance(retry_policy_payload, dict) else {}
    _apply_profile_scalar_policy(
        profile_name=profile_name,
        policy_name="retry_policy",
        policy_payload=retry_policy,
        env_map=maps.retry,
        bounds_map=_RETRY_POLICY_BOUNDS,
        applied_keys=applied_keys,
        force_override=force_override,
    )

    timeout_policy_payload = profile_payload.get("timeout_policy")
    timeout_policy = timeout_policy_payload if isinstance(timeout_policy_payload, dict) else {}
    _apply_profile_scalar_policy(
        profile_name=profile_name,
        policy_name="timeout_policy",
        policy_payload=timeout_policy,
        env_map=maps.timeout,
        bounds_map=_TIMEOUT_POLICY_BOUNDS,
        applied_keys=applied_keys,
        force_override=force_override,
    )

    skill_policy_payload = profile_payload.get("skill_policy")
    skill_policy = skill_policy_payload if isinstance(skill_policy_payload, dict) else {}
    _apply_profile_skill_policy(
        profile_name=profile_name,
        skill_policy_payload=skill_policy,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )

    backend_policy_payload = profile_payload.get("backend_policy")
    backend_policy = backend_policy_payload if isinstance(backend_policy_payload, dict) else {}
    _apply_profile_backend_policy(
        profile_name=profile_name,
        backend_policy_payload=backend_policy,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )

    agent_runtime_policy_payload = profile_payload.get("agent_runtime_policy")
    agent_runtime_policy = agent_runtime_policy_payload if isinstance(agent_runtime_policy_payload, dict) else {}
    _apply_profile_agent_runtime_policy(
        profile_name=profile_name,
        agent_runtime_policy_payload=agent_runtime_policy,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )

    agentic_payload = profile_payload.get("agentic")
    agentic_policy = agentic_payload if isinstance(agentic_payload, dict) else {}
    _apply_profile_agentic_policy(
        profile_name=profile_name,
        agentic_payload=agentic_policy,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )

    _auto_derive_dspy_config(
        profile_name=profile_name,
        applied_keys=applied_keys,
        force_override=force_override,
        maps=maps,
    )
    _validate_dspy_coherence(profile_name=profile_name, maps=maps)
    _apply_codex_chatgpt_baseline_defaults(
        profile_name=profile_name,
        applied_keys=applied_keys,
        env_prefix=env_prefix,
    )

    # FR-226.13 (W3): opt-in embedding-block parser. Default OFF preserves
    # FR-225.22 back-compat lock for existing audit / progress_report callers.
    if parse_embedding:
        embedding_payload_raw = (
            model_values.get("embedding") if isinstance(model_values, dict) else None
        )
        embedding_payload = embedding_payload_raw if isinstance(embedding_payload_raw, dict) else {}
        if embedding_payload:
            _apply_profile_embedding_block(
                profile_name=profile_name,
                embedding_payload=embedding_payload,
                applied_keys=applied_keys,
                force_override=force_override,
                embedding_env_prefix=embedding_env_prefix,
                credential_resolver=credential_resolver,
            )
            _maybe_log_embedding_resolution(profile_name)

    # Propagate API key to provider-specific env vars for pydantic-ai.
    _resolved_api_key = os.environ.get(maps.model_llm["api_key"], "")
    _model_payload = profile_payload.get("model", {})
    _llm_type = (
        str((_model_payload.get("llm") or {}).get("type", "")).strip().lower()
        if isinstance(_model_payload, dict)
        else ""
    )
    if _resolved_api_key:
        if _llm_type == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = _resolved_api_key
        elif _llm_type in ("openai", "") and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = _resolved_api_key

    os.environ[maps.active_profile_env] = profile_name
    return RuntimeProfileActivation(
        profile_name=profile_name,
        source=source,
        profile_path=profile_path,
        applied_env_keys=tuple(applied_keys),
    )


def build_llm_settings_for_profile(
    profile_name: str,
    *,
    env_prefix: str = "VDS_AUDIT_",
    config_hooks: ConfigHooks | None = None,
    settings_factory: Any = None,
) -> Any:
    """Build isolated LLM settings for a runtime profile without persistent env mutation.

    Args:
        profile_name: The profile to build settings for.
        env_prefix: Env prefix for the profile engine.
        config_hooks: Config get/set/reset hooks. Required for config snapshot/restore.
        settings_factory: Callable that returns LLMSettings from current config.
            If None, returns None (caller must handle).
    """
    with _RUNTIME_PROFILE_BUILD_LOCK:
        previous_config = config_hooks.get_config() if config_hooks else None
        env_snapshot = {key: value for key, value in os.environ.items() if key.startswith(env_prefix)}
        try:
            apply_runtime_profile(profile_name, env_prefix=env_prefix, force_override=True)
            if config_hooks:
                config_hooks.reset_config()
            if settings_factory is not None:
                return settings_factory()
            return None
        finally:
            for key in [item for item in os.environ if item.startswith(env_prefix)]:
                if key not in env_snapshot:
                    os.environ.pop(key, None)
            for key, value in env_snapshot.items():
                os.environ[key] = value
            if config_hooks and previous_config is not None:
                config_hooks.set_config(previous_config)


def inherit_runtime_llm_policy(
    profile_name: str,
    *,
    source_llm: Any | None = None,
    env_prefix: str = "VDS_AUDIT_",
    config_hooks: ConfigHooks | None = None,
    settings_factory: Any = None,
) -> Any:
    """Build profile settings while preserving active runtime execution policy knobs."""
    settings = build_llm_settings_for_profile(
        profile_name,
        env_prefix=env_prefix,
        config_hooks=config_hooks,
        settings_factory=settings_factory,
    )
    if source_llm is None:
        return settings

    if hasattr(settings, "model_copy"):
        with contextlib.suppress(TypeError, ValueError, AttributeError):
            settings = settings.model_copy(deep=True)
    else:
        settings = copy.copy(settings)

    for field_name in _RUNTIME_LLM_POLICY_FIELDS:
        if not hasattr(source_llm, field_name):
            continue
        with contextlib.suppress(Exception):
            setattr(settings, field_name, copy.deepcopy(getattr(source_llm, field_name)))
    return settings


def build_embedding_settings_for_profile(
    profile_name: str,
    *,
    env_prefix: str = "VDS_AUDIT_",
    embedding_env_prefix: str = "VDS_AGENT_CORE_EMBED__",
    config_hooks: ConfigHooks | None = None,
    credential_resolver: CodexCredentialResolver | None = None,
) -> Any:
    """Build :class:`EmbeddingSettings` for a runtime profile (FR-226.13).

    Mirrors :func:`build_llm_settings_for_profile`: snapshots both the LLM-prefix
    env vars and the embedding-prefix env vars, applies the profile with
    ``parse_embedding=True``, constructs the EmbeddingSettings, then restores
    the env. Side-effect-free (FR-226.11) -- no Redis / disk-write calls.

    Args:
        profile_name: Runtime profile to activate.
        env_prefix: LLM-side env prefix (kept for symmetry with siblings).
        embedding_env_prefix: Embedding-side env prefix
            (matches ``EmbeddingSettings.model_config["env_prefix"]``).
        config_hooks: Optional config snapshot/restore hooks.
        credential_resolver: Optional resolver for ``${codex:...}`` references.

    Returns:
        Newly-constructed :class:`EmbeddingSettings` instance.
    """
    # Lazy import to break the profiles -> llm.embedding cycle.
    from vds_agent_core.llm.embedding import EmbeddingSettings

    with _RUNTIME_PROFILE_BUILD_LOCK:
        previous_config = config_hooks.get_config() if config_hooks else None
        env_snapshot: dict[str, str] = {
            key: value
            for key, value in os.environ.items()
            if key.startswith(env_prefix) or key.startswith(embedding_env_prefix)
        }
        try:
            apply_runtime_profile(
                profile_name,
                env_prefix=env_prefix,
                force_override=True,
                credential_resolver=credential_resolver,
                parse_embedding=True,
                embedding_env_prefix=embedding_env_prefix,
            )
            if config_hooks:
                config_hooks.reset_config()
            return EmbeddingSettings()
        finally:
            for key in [
                item
                for item in os.environ
                if item.startswith(env_prefix) or item.startswith(embedding_env_prefix)
            ]:
                if key not in env_snapshot:
                    os.environ.pop(key, None)
            for key, value in env_snapshot.items():
                os.environ[key] = value
            if config_hooks and previous_config is not None:
                config_hooks.set_config(previous_config)


def is_agent_allowed_for_profile(
    profile_name: str,
    agent_id: str,
    *,
    profiles: dict[str, Any] | None = None,
) -> bool:
    """Check whether ``agent_id`` is allowed to activate ``profile_name`` (NFR-225.13).

    The ``allowed_agents`` field on a profile entry is an optional list of
    fnmatch-style glob patterns. Absent field => any agent allowed
    (back-compat). When present, ``agent_id`` must match at least one pattern.

    Args:
        profile_name: Profile to check.
        agent_id: Agent identifier (matched verbatim against globs).
        profiles: Optional pre-loaded profiles map. Falls back to loading
            from :func:`resolve_runtime_profiles_path` when ``None``.

    Returns:
        True if allowed (or field absent); False otherwise.
    """
    profiles_map = profiles
    if profiles_map is None:
        profile_path = resolve_runtime_profiles_path()
        raw: dict[str, Any] = {}
        if profile_path.exists():
            payload = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
            if isinstance(payload, dict):
                raw = payload
        loaded = raw.get("profiles")
        profiles_map = loaded if isinstance(loaded, dict) else {}
    profile_payload = profiles_map.get(profile_name)
    if not isinstance(profile_payload, dict):
        # Unknown profile -> defer to caller; treat as "no constraint" so the
        # subsequent profile-resolution path raises a clearer error message.
        return True
    allowed_agents = profile_payload.get("allowed_agents")
    if allowed_agents is None:
        return True
    if not isinstance(allowed_agents, list):
        raise ProfileValidationError(
            f"Runtime profile '{profile_name}' has invalid allowed_agents: "
            f"{allowed_agents!r} (expected list of glob strings)."
        )
    for pattern in allowed_agents:
        if not isinstance(pattern, str):
            continue
        if fnmatch.fnmatch(agent_id, pattern):
            return True
    return False


def resolve_skill_directory_path(raw_path: str | Path) -> Path:
    """Resolve a skill-directory path with portable relative-path semantics."""
    path_obj = raw_path if isinstance(raw_path, Path) else Path(str(raw_path))
    expanded = path_obj.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    candidate_bases: list[Path] = []
    for env_name in ("VDS_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        raw_base = os.getenv(env_name)
        if raw_base and raw_base.strip():
            candidate_bases.append(Path(raw_base).expanduser())
    candidate_bases.append(Path.cwd())
    for base in candidate_bases:
        candidate = (base / expanded).resolve()
        if candidate.exists():
            return candidate
    return (candidate_bases[0] / expanded).resolve()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _set_profile_env(env_key: str, value: Any, *, force_override: bool = False) -> bool:
    """Set profile env var without overriding an already-defined process env."""
    existing = os.environ.get(env_key)
    if not force_override and isinstance(existing, str) and existing.strip():
        return False
    os.environ[env_key] = str(value)
    return True


def _get_env_credential_allowlist() -> frozenset[str]:
    """Return the active ``${env:VAR}`` allowlist (compile-time defaults + operator extensions).

    Operators may extend via ``VDS_AGENT_CORE__CREDENTIAL_ENV_ALLOWLIST`` (JSON array).
    Malformed JSON / non-list payloads silently fall back to the compile-time default
    (NFR-225.12 -- never narrow the allowlist via env-var typo).
    """
    extra = os.environ.get(_ENV_CREDENTIAL_ALLOWLIST_ENV, "").strip()
    if not extra:
        return _DEFAULT_ENV_CREDENTIAL_ALLOWLIST
    try:
        parsed = json.loads(extra)
    except json.JSONDecodeError:
        return _DEFAULT_ENV_CREDENTIAL_ALLOWLIST
    if not isinstance(parsed, list):
        return _DEFAULT_ENV_CREDENTIAL_ALLOWLIST
    extras = {str(item).strip() for item in parsed if isinstance(item, str) and str(item).strip()}
    return _DEFAULT_ENV_CREDENTIAL_ALLOWLIST | frozenset(extras)


def _resolve_env_scheme(
    *,
    profile_name: str,
    key: str,
    value: str,
) -> str | None:
    """Resolve ``${env:VAR}`` references against the credential allowlist (FR-226.15, NFR-225.12).

    Returns:
        The resolved env-var value if ``value`` matches the ``${env:VAR}`` scheme AND
        ``VAR`` is allowlisted. Returns ``None`` if the value does not match the scheme
        (caller should fall through to other resolvers).

    Raises:
        CredentialResolutionError: if the env var is not on the allowlist.
        ValueError: if the env var is allowlisted but unset/empty.
    """
    match = _ENV_SCHEME_PATTERN.match(value)
    if match is None:
        return None
    env_name = match.group(1)
    allowlist = _get_env_credential_allowlist()
    if env_name not in allowlist:
        raise CredentialResolutionError(
            f"Runtime profile '{profile_name}' references env var {env_name!r} via {value!r} for {key}, "
            f"but env var '{env_name}' is not in the credential allowlist. "
            f"Extend via {_ENV_CREDENTIAL_ALLOWLIST_ENV} (JSON array) or use ${{VAR}} for non-credential vars."
        )
    env_value = os.getenv(env_name, "").strip()
    if not env_value:
        raise ValueError(
            f"Runtime profile '{profile_name}' requires environment variable '{env_name}' for {key}, "
            "but it is not set or empty."
        )
    return env_value


def _resolve_env_reference_if_needed(
    *,
    profile_name: str,
    key: str,
    raw_value: Any,
    credential_resolver: CredentialResolver | None = None,
) -> Any:
    """Resolve ${env:VAR}, ${ENV_VAR}, and ${codex:<field>} placeholders in profile values."""
    if not isinstance(raw_value, str):
        return raw_value
    value = raw_value.strip()
    if not value:
        return value
    # FR-226.15 + NFR-225.12: ${env:VAR} scheme has highest priority among env-style
    # patterns; takes the credential allowlist gate.
    env_scheme_resolved = _resolve_env_scheme(profile_name=profile_name, key=key, value=value)
    if env_scheme_resolved is not None:
        return env_scheme_resolved
    match = _ENV_REF_PATTERN.match(value)
    if match is not None:
        env_name = match.group(1)
        env_value = os.getenv(env_name, "").strip()
        if not env_value:
            raise ValueError(
                f"Runtime profile '{profile_name}' requires environment variable '{env_name}' for {key}, "
                "but it is not set or empty."
            )
        return env_value
    codex_match = _CODEX_REF_PATTERN.match(value)
    if codex_match is None:
        if value.startswith("${codex:") and value.endswith("}"):
            raise ValueError(
                f"Runtime profile '{profile_name}' has malformed codex reference '{value}' for {key}. "
                "Expected format: ${codex:access_token} | ${codex:account_id} | ${codex:refresh_token}."
            )
        return value
    field_name = codex_match.group(1)
    if field_name not in _CODEX_REF_FIELDS:
        allowed = ", ".join(_CODEX_REF_FIELDS)
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid codex reference '{value}' for {key}. "
            f"Allowed fields: {allowed}."
        )
    resolver = credential_resolver or _credential_resolver_ctx.get(None)
    if resolver is None:
        raise ValueError(
            f"Runtime profile '{profile_name}' uses codex reference '{value}' for {key}, "
            "but no credential_resolver was provided. Inject a CredentialResolver "
            "via apply_runtime_profile(..., credential_resolver=...) to resolve ${codex:...} references."
        )
    try:
        return resolver.resolve(field_name)
    except Exception as exc:
        raise ValueError(f"Runtime profile '{profile_name}' failed resolving {key} from '{value}': {exc}") from exc


def _validate_required_string(*, profile_name: str, key: str, raw_value: Any) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected non-empty string)."
        )
    return _resolve_env_reference_if_needed(profile_name=profile_name, key=key, raw_value=raw_value.strip())


def _validate_boolean_policy_value(*, profile_name: str, key: str, raw_value: Any) -> str:
    if isinstance(raw_value, bool):
        return "true" if raw_value else "false"
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in {"true", "false"}:
            return normalized
    raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected boolean).")


def _validate_optional_boolean_policy_value(
    *,
    profile_name: str,
    key: str,
    raw_value: Any,
    default: bool,
) -> bool:
    if raw_value is None:
        return default
    normalized = _validate_boolean_policy_value(profile_name=profile_name, key=key, raw_value=raw_value)
    return normalized == "true"


def _validate_retry_policy_value(
    *,
    profile_name: str,
    key: str,
    raw_value: Any,
    min_value: float,
    max_value: float,
    value_type: type[int] | type[float],
    allow_zero_int: bool = False,
) -> int | float:
    """Validate scalar policy value from runtime profile and return normalized scalar."""
    try:
        coerced = value_type(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected {value_type.__name__})."
        ) from exc
    if allow_zero_int and value_type is int and coerced == 0:
        return 0
    if coerced < min_value or coerced > max_value:
        raise ValueError(
            f"Runtime profile '{profile_name}' has out-of-range {key}: {coerced} (allowed {min_value}..{max_value})."
        )
    return int(coerced) if value_type is int else float(coerced)


def _apply_profile_scalar_policy(
    *,
    profile_name: str,
    policy_name: str,
    policy_payload: dict[str, Any],
    env_map: dict[str, str],
    bounds_map: dict[str, tuple[float, float, type[int] | type[float]]],
    applied_keys: list[str],
    force_override: bool,
) -> None:
    """Validate and apply scalar policy entries from runtime profile."""
    for key, env_key in env_map.items():
        if key not in policy_payload:
            continue
        raw_value = policy_payload[key]
        min_value, max_value, value_type = bounds_map[key]
        validated = _validate_retry_policy_value(
            profile_name=profile_name,
            key=f"{policy_name}.{key}",
            raw_value=raw_value,
            min_value=min_value,
            max_value=max_value,
            value_type=value_type,
            allow_zero_int=policy_name == "agentic" and key == "tool_calls_limit",
        )
        if _set_profile_env(env_key, validated, force_override=force_override):
            applied_keys.append(env_key)


def _apply_profile_model_policy(
    *,
    profile_name: str,
    model_policy_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Validate and apply structured model policy from runtime profile."""
    if not model_policy_payload:
        return

    llm_payload_raw = model_policy_payload.get("llm")
    if llm_payload_raw is not None and not isinstance(llm_payload_raw, dict):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.llm: {llm_payload_raw!r} (expected object)."
        )
    llm_payload = llm_payload_raw if isinstance(llm_payload_raw, dict) else {}
    allowed_llm_keys = set(maps.model_llm) | {"model", "code_review_max_total_chars"}
    unknown_llm_keys = set(llm_payload).difference(allowed_llm_keys)
    if unknown_llm_keys:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.llm keys: {sorted(unknown_llm_keys)!r} "
            f"(allowed: {', '.join(sorted(allowed_llm_keys))})."
        )
    if "type" in llm_payload:
        protocol = _validate_required_string(
            profile_name=profile_name,
            key="model.llm.type",
            raw_value=llm_payload["type"],
        ).lower()
        if protocol not in _SUPPORTED_PROFILE_PROTOCOLS:
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid model.llm.type='{protocol}'. "
                f"Allowed protocols: {', '.join(_SUPPORTED_PROFILE_PROTOCOLS)}."
            )
        if _set_profile_env(maps.model_llm["type"], protocol, force_override=force_override):
            applied_keys.append(maps.model_llm["type"])
    if "base_url" in llm_payload:
        base_url = _validate_required_string(
            profile_name=profile_name,
            key="model.llm.base_url",
            raw_value=llm_payload["base_url"],
        )
        if _set_profile_env(maps.model_llm["base_url"], base_url, force_override=force_override):
            applied_keys.append(maps.model_llm["base_url"])
    if "api_key" in llm_payload:
        api_key = _validate_required_string(
            profile_name=profile_name,
            key="model.llm.api_key",
            raw_value=llm_payload["api_key"],
        )
        if _set_profile_env(maps.model_llm["api_key"], api_key, force_override=force_override):
            applied_keys.append(maps.model_llm["api_key"])
    if "stream" in llm_payload:
        stream = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="model.llm.stream",
            raw_value=llm_payload["stream"],
        )
        if _set_profile_env(maps.model_llm["stream"], stream, force_override=force_override):
            applied_keys.append(maps.model_llm["stream"])
    if "agent_stream" in llm_payload:
        agent_stream = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="model.llm.agent_stream",
            raw_value=llm_payload["agent_stream"],
        )
        if _set_profile_env(maps.model_llm["agent_stream"], agent_stream, force_override=force_override):
            applied_keys.append(maps.model_llm["agent_stream"])
    if "row_failover_profiles" in llm_payload:
        raw_profiles = llm_payload["row_failover_profiles"]
        if isinstance(raw_profiles, str):
            failover_profiles = [item.strip() for item in raw_profiles.split(",") if item.strip()]
        elif isinstance(raw_profiles, list):
            failover_profiles = []
            for index, item in enumerate(raw_profiles):
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(
                        f"Runtime profile '{profile_name}' has invalid model.llm.row_failover_profiles[{index}]: "
                        f"{item!r} (expected non-empty string)."
                    )
                failover_profiles.append(item.strip())
        else:
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid model.llm.row_failover_profiles: "
                f"{raw_profiles!r} (expected string or list)."
            )
        if _set_profile_env(
            maps.model_llm["row_failover_profiles"],
            json.dumps(failover_profiles),
            force_override=force_override,
        ):
            applied_keys.append(maps.model_llm["row_failover_profiles"])
    if "row_failover_max_provider_hops" in llm_payload:
        max_provider_hops = _validate_retry_policy_value(
            profile_name=profile_name,
            key="model.llm.row_failover_max_provider_hops",
            raw_value=llm_payload["row_failover_max_provider_hops"],
            min_value=0,
            max_value=5,
            value_type=int,
        )
        if _set_profile_env(
            maps.model_llm["row_failover_max_provider_hops"],
            max_provider_hops,
            force_override=force_override,
        ):
            applied_keys.append(maps.model_llm["row_failover_max_provider_hops"])
    if "reasoning_effort" in llm_payload:
        reasoning_effort = _validate_required_string(
            profile_name=profile_name,
            key="model.llm.reasoning_effort",
            raw_value=llm_payload["reasoning_effort"],
        ).lower()
        if reasoning_effort not in _LLM_REASONING_EFFORT_VALUES:
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid model.llm.reasoning_effort={reasoning_effort!r}. "
                f"Allowed values: {', '.join(_LLM_REASONING_EFFORT_VALUES)}."
            )
        if _set_profile_env(maps.model_llm["reasoning_effort"], reasoning_effort, force_override=force_override):
            applied_keys.append(maps.model_llm["reasoning_effort"])
    if "model" in llm_payload:
        model = _validate_required_string(
            profile_name=profile_name,
            key="model.llm.model",
            raw_value=llm_payload["model"],
        )
        if "simple" not in llm_payload and _set_profile_env(
            maps.model_llm["simple"], model, force_override=force_override
        ):
            applied_keys.append(maps.model_llm["simple"])
        if "standard" not in llm_payload and _set_profile_env(
            maps.model_llm["standard"], model, force_override=force_override
        ):
            applied_keys.append(maps.model_llm["standard"])
        if "complex" not in llm_payload and _set_profile_env(
            maps.model_llm["complex"], model, force_override=force_override
        ):
            applied_keys.append(maps.model_llm["complex"])
    for tier, env_key in maps.model_llm.items():
        if tier in {"type", "base_url", "stream", "agent_stream", "reasoning_effort"}:
            continue
        if tier not in llm_payload:
            continue
        model_value = _validate_required_string(
            profile_name=profile_name,
            key=f"model.llm.{tier}",
            raw_value=llm_payload[tier],
        )
        if _set_profile_env(env_key, model_value, force_override=force_override):
            applied_keys.append(env_key)
    if "code_review_max_total_chars" in llm_payload:
        cr_env_key = f"{maps.prefix}LLM__CODE_REVIEW_MAX_TOTAL_CHARS"
        value = _validate_retry_policy_value(
            profile_name=profile_name,
            key="model.llm.code_review_max_total_chars",
            raw_value=llm_payload["code_review_max_total_chars"],
            min_value=1000,
            max_value=500000,
            value_type=int,
        )
        if _set_profile_env(cr_env_key, value, force_override=force_override):
            applied_keys.append(cr_env_key)

    # DSPy model policy
    dspy_payload_raw = model_policy_payload.get("dspy")
    if dspy_payload_raw is not None and not isinstance(dspy_payload_raw, dict):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.dspy: {dspy_payload_raw!r} (expected object)."
        )
    dspy_payload = dspy_payload_raw if isinstance(dspy_payload_raw, dict) else {}
    unknown_dspy_keys = set(dspy_payload).difference(maps.model_dspy)
    if unknown_dspy_keys:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.dspy keys: {sorted(unknown_dspy_keys)!r} "
            f"(allowed: {', '.join(maps.model_dspy)})."
        )
    if "type" in dspy_payload:
        protocol = _validate_required_string(
            profile_name=profile_name,
            key="model.dspy.type",
            raw_value=dspy_payload["type"],
        ).lower()
        if protocol not in _SUPPORTED_PROFILE_PROTOCOLS:
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid model.dspy.type='{protocol}'. "
                f"Allowed protocols: {', '.join(_SUPPORTED_PROFILE_PROTOCOLS)}."
            )
        if _set_profile_env(maps.model_dspy["type"], protocol, force_override=force_override):
            applied_keys.append(maps.model_dspy["type"])
    if "model" in dspy_payload:
        str_value = _validate_required_string(
            profile_name=profile_name,
            key="model.dspy.model",
            raw_value=dspy_payload["model"],
        )
        if _set_profile_env(maps.model_dspy["model"], str_value, force_override=force_override):
            applied_keys.append(maps.model_dspy["model"])
    if "api_key" in dspy_payload:
        str_value = _validate_required_string(
            profile_name=profile_name,
            key="model.dspy.api_key",
            raw_value=dspy_payload["api_key"],
        )
        if _set_profile_env(maps.model_dspy["api_key"], str_value, force_override=force_override):
            applied_keys.append(maps.model_dspy["api_key"])
    if "max_tokens" in dspy_payload:
        value = _validate_retry_policy_value(
            profile_name=profile_name,
            key="model.dspy.max_tokens",
            raw_value=dspy_payload["max_tokens"],
            min_value=1,
            max_value=200000,
            value_type=int,
        )
        if _set_profile_env(maps.model_dspy["max_tokens"], value, force_override=force_override):
            applied_keys.append(maps.model_dspy["max_tokens"])
    if "temperature" in dspy_payload:
        value = _validate_retry_policy_value(
            profile_name=profile_name,
            key="model.dspy.temperature",
            raw_value=dspy_payload["temperature"],
            min_value=0.0,
            max_value=2.0,
            value_type=float,
        )
        if _set_profile_env(maps.model_dspy["temperature"], value, force_override=force_override):
            applied_keys.append(maps.model_dspy["temperature"])
    if "base_url" in dspy_payload:
        str_value = _validate_required_string(
            profile_name=profile_name,
            key="model.dspy.base_url",
            raw_value=dspy_payload["base_url"],
        )
        if _set_profile_env(maps.model_dspy["base_url"], str_value, force_override=force_override):
            applied_keys.append(maps.model_dspy["base_url"])
    if "system_role_compat" in dspy_payload:
        bool_str_value = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="model.dspy.system_role_compat",
            raw_value=dspy_payload["system_role_compat"],
        )
        encoded = "1" if bool_str_value == "true" else "0"
        if _set_profile_env(maps.model_dspy["system_role_compat"], encoded, force_override=force_override):
            applied_keys.append(maps.model_dspy["system_role_compat"])

    # Embedding model policy
    embedding_payload_raw = model_policy_payload.get("embedding")
    if embedding_payload_raw is not None and not isinstance(embedding_payload_raw, dict):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.embedding: {embedding_payload_raw!r} "
            "(expected object)."
        )
    embedding_payload = embedding_payload_raw if isinstance(embedding_payload_raw, dict) else {}
    # FR-226.13 (W3): ``type`` and ``dimension`` are accepted here as forward-compatible
    # keys for the new embedding-block parser. They are validated in
    # _apply_profile_embedding_block (under parse_embedding=True); this helper merely
    # tolerates their presence so legacy callers (parse_embedding=False) don't trip.
    _W3_TOLERATED_EMBEDDING_KEYS = {
        "type",
        "dimension",
        "model_simple",
        "model_standard",
        "model_complex",
        "fail_open",
        "cache_ttl_seconds",
        "timeout_seconds",
    }
    legacy_allowed = set(maps.model_embedding) | _W3_TOLERATED_EMBEDDING_KEYS
    unknown_embedding_keys = set(embedding_payload).difference(legacy_allowed)
    if unknown_embedding_keys:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid model.embedding keys: {sorted(unknown_embedding_keys)!r} "
            f"(allowed: {', '.join(sorted(legacy_allowed))})."
        )
    for emb_key in ("base_url", "model", "api_key"):
        if emb_key in embedding_payload:
            str_value = _validate_required_string(
                profile_name=profile_name,
                key=f"model.embedding.{emb_key}",
                raw_value=embedding_payload[emb_key],
            )
            if _set_profile_env(maps.model_embedding[emb_key], str_value, force_override=force_override):
                applied_keys.append(maps.model_embedding[emb_key])


def _apply_profile_embedding_block(
    *,
    profile_name: str,
    embedding_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    embedding_env_prefix: str,
    credential_resolver: CodexCredentialResolver | None = None,
) -> None:
    """Parse the ``model.embedding`` block into ``EmbeddingSettings``-shaped env vars.

    Activated only when ``apply_runtime_profile(..., parse_embedding=True)`` (FR-226.13).
    Validates ``type`` against the live ``EMBEDDING_PROVIDERS`` registry and
    projects the rest of the block into ``<embedding_env_prefix>*`` env keys.
    """
    # Lazy import: avoids a profiles -> llm.embedding cycle on module load.
    from vds_agent_core.llm.embedding import EMBEDDING_PROVIDERS

    if "type" in embedding_payload:
        raw_type = embedding_payload["type"]
        if not isinstance(raw_type, str) or not raw_type.strip():
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.type: "
                f"{raw_type!r} (expected non-empty string)."
            )
        type_value = raw_type.strip()
        if type_value not in EMBEDDING_PROVIDERS:
            raise ProfileValidationError(
                f"Unknown embedding type {type_value!r}; registered: {sorted(EMBEDDING_PROVIDERS)}"
            )
        env_key = f"{embedding_env_prefix}PROVIDER"
        if _set_profile_env(env_key, type_value, force_override=force_override):
            applied_keys.append(env_key)

    str_field_to_env = {
        "base_url": "BASE_URL",
        "api_key": "API_KEY",
        "model": "MODEL_STANDARD",
        "model_simple": "MODEL_SIMPLE",
        "model_standard": "MODEL_STANDARD",
        "model_complex": "MODEL_COMPLEX",
    }
    for field_name, env_suffix in str_field_to_env.items():
        if field_name not in embedding_payload:
            continue
        str_value = _validate_required_string(
            profile_name=profile_name,
            key=f"model.embedding.{field_name}",
            raw_value=embedding_payload[field_name],
        )
        # api_key may legitimately resolve to a sensitive string via ${env:VAR};
        # _validate_required_string already routed through credential_resolver.
        _ = credential_resolver  # Silence linters; resolver context is used inside helpers.
        env_key = f"{embedding_env_prefix}{env_suffix}"
        if _set_profile_env(env_key, str_value, force_override=force_override):
            applied_keys.append(env_key)

    if "dimension" in embedding_payload:
        raw_dim = embedding_payload["dimension"]
        try:
            dim_value = int(raw_dim)
        except (TypeError, ValueError) as exc:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.dimension: "
                f"{raw_dim!r} (expected positive integer)."
            ) from exc
        if dim_value <= 0:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.dimension: "
                f"{dim_value} (expected positive integer)."
            )
        env_key = f"{embedding_env_prefix}DIMENSION"
        if _set_profile_env(env_key, str(dim_value), force_override=force_override):
            applied_keys.append(env_key)

    if "fail_open" in embedding_payload:
        bool_str = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="model.embedding.fail_open",
            raw_value=embedding_payload["fail_open"],
        )
        env_key = f"{embedding_env_prefix}FAIL_OPEN"
        if _set_profile_env(env_key, bool_str, force_override=force_override):
            applied_keys.append(env_key)

    if "cache_ttl_seconds" in embedding_payload:
        raw_ttl = embedding_payload["cache_ttl_seconds"]
        try:
            ttl_value = int(raw_ttl)
        except (TypeError, ValueError) as exc:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.cache_ttl_seconds: "
                f"{raw_ttl!r} (expected non-negative integer)."
            ) from exc
        if ttl_value < 0:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.cache_ttl_seconds: "
                f"{ttl_value} (expected non-negative integer)."
            )
        env_key = f"{embedding_env_prefix}CACHE_TTL_SECONDS"
        if _set_profile_env(env_key, str(ttl_value), force_override=force_override):
            applied_keys.append(env_key)

    if "timeout_seconds" in embedding_payload:
        raw_timeout = embedding_payload["timeout_seconds"]
        try:
            timeout_value = float(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.timeout_seconds: "
                f"{raw_timeout!r} (expected positive float)."
            ) from exc
        if timeout_value <= 0:
            raise ProfileValidationError(
                f"Runtime profile '{profile_name}' has invalid model.embedding.timeout_seconds: "
                f"{timeout_value} (expected positive float)."
            )
        env_key = f"{embedding_env_prefix}TIMEOUT_SECONDS"
        if _set_profile_env(env_key, str(timeout_value), force_override=force_override):
            applied_keys.append(env_key)


def _maybe_log_embedding_resolution(profile_name: str) -> None:
    """Emit one-shot ``profile_embedding_resolved`` INFO log per profile (NFR-226.1).

    BLOCKER-1 (W6 v20.6.1 fix): the ``logger.info`` MUST sit inside the lock —
    otherwise two threads passing the ``add()`` can both emit the log before
    the first ``return``. Mirrors the lock-emit pattern in
    ``_cascade.py::_log_resolution_once``.
    """
    if os.environ.get("VDS_AGENT_CORE__LOG_RESOLUTION", "").lower() != "true":
        return
    with _EMBEDDING_PROFILE_RESOLUTION_LOCK:
        if profile_name in _EMBEDDING_PROFILE_RESOLUTION_SEEN:
            return
        _EMBEDDING_PROFILE_RESOLUTION_SEEN.add(profile_name)
        logger.info("profile_embedding_resolved", profile_name=profile_name)


def _reset_embedding_resolution_log() -> None:
    """Test helper: clear the one-shot embedding-resolution log set."""
    with _EMBEDDING_PROFILE_RESOLUTION_LOCK:
        _EMBEDDING_PROFILE_RESOLUTION_SEEN.clear()


def _apply_profile_skill_policy(
    *,
    profile_name: str,
    skill_policy_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Validate and apply skill_policy entries from runtime profile."""
    if "enabled" in skill_policy_payload:
        env_key = maps.skill["enabled"]
        value = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="skill_policy.enabled",
            raw_value=skill_policy_payload["enabled"],
        )
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)
    if "directories" in skill_policy_payload:
        env_key = maps.skill["directories"]
        directories = _validate_skill_directory_list(
            profile_name=profile_name,
            key="skill_policy.directories",
            raw_value=skill_policy_payload["directories"],
        )
        if _set_profile_env(env_key, json.dumps(directories), force_override=force_override):
            applied_keys.append(env_key)
    if "allow_script_execution" in skill_policy_payload:
        env_key = maps.skill["allow_script_execution"]
        value = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="skill_policy.allow_script_execution",
            raw_value=skill_policy_payload["allow_script_execution"],
        )
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)
    if "default_trust_tier" in skill_policy_payload:
        env_key = maps.skill["default_trust_tier"]
        value = _validate_skill_trust_tier(
            profile_name=profile_name,
            key="skill_policy.default_trust_tier",
            raw_value=skill_policy_payload["default_trust_tier"],
        )
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)
    if "allowed_trust_tiers" in skill_policy_payload:
        env_key = maps.skill["allowed_trust_tiers"]
        tiers = _validate_skill_trust_tier_list(
            profile_name=profile_name,
            key="skill_policy.allowed_trust_tiers",
            raw_value=skill_policy_payload["allowed_trust_tiers"],
        )
        if _set_profile_env(env_key, json.dumps(tiers), force_override=force_override):
            applied_keys.append(env_key)
    if "allowlist" in skill_policy_payload:
        env_key = maps.skill["allowlist"]
        allowlist = _validate_skill_name_list(
            profile_name=profile_name,
            key="skill_policy.allowlist",
            raw_value=skill_policy_payload["allowlist"],
        )
        if _set_profile_env(env_key, json.dumps(allowlist), force_override=force_override):
            applied_keys.append(env_key)
    if "trust_tiers" in skill_policy_payload:
        env_key = maps.skill["trust_tiers"]
        trust_tiers = _validate_skill_trust_tier_map(
            profile_name=profile_name,
            key="skill_policy.trust_tiers",
            raw_value=skill_policy_payload["trust_tiers"],
        )
        if _set_profile_env(env_key, json.dumps(trust_tiers), force_override=force_override):
            applied_keys.append(env_key)
    if "strict_require_effective_skill" in skill_policy_payload:
        env_key = maps.skill["strict_require_effective_skill"]
        value = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="skill_policy.strict_require_effective_skill",
            raw_value=skill_policy_payload["strict_require_effective_skill"],
        )
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)


def _validate_skill_trust_tier(*, profile_name: str, key: str, raw_value: Any) -> str:
    if not isinstance(raw_value, str):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected trust-tier string)."
        )
    value = raw_value.strip()
    if value not in _SKILL_TRUST_TIERS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} "
            f"(allowed: {', '.join(_SKILL_TRUST_TIERS)})."
        )
    return value


def _validate_skill_trust_tier_list(*, profile_name: str, key: str, raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected list).")
    if not raw_value:
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: list cannot be empty.")
    if len(raw_value) > _SKILL_POLICY_MAX_LIST_ITEMS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: too many entries "
            f"(max {_SKILL_POLICY_MAX_LIST_ITEMS})."
        )
    validated: list[str] = []
    for index, item in enumerate(raw_value):
        validated.append(_validate_skill_trust_tier(profile_name=profile_name, key=f"{key}[{index}]", raw_value=item))
    return list(dict.fromkeys(validated))


def _validate_skill_name_list(*, profile_name: str, key: str, raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected list).")
    if len(raw_value) > _SKILL_POLICY_MAX_LIST_ITEMS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: too many entries "
            f"(max {_SKILL_POLICY_MAX_LIST_ITEMS})."
        )
    validated: list[str] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid {key}[{index}]: {item!r} (expected non-empty string)."
            )
        validated.append(item.strip())
    return validated


def _validate_skill_directory_list(*, profile_name: str, key: str, raw_value: Any) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected list).")
    if not raw_value:
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: list cannot be empty.")
    if len(raw_value) > _SKILL_POLICY_MAX_LIST_ITEMS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: too many entries "
            f"(max {_SKILL_POLICY_MAX_LIST_ITEMS})."
        )
    validated: list[str] = []
    for index, item in enumerate(raw_value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid {key}[{index}]: {item!r} (expected non-empty string)."
            )
        resolved = resolve_skill_directory_path(item.strip())
        validated.append(str(resolved))
    return validated


def _validate_skill_trust_tier_map(*, profile_name: str, key: str, raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected object map).")
    if len(raw_value) > _SKILL_POLICY_MAX_MAP_ITEMS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: too many entries (max {_SKILL_POLICY_MAX_MAP_ITEMS})."
        )
    validated: dict[str, str] = {}
    for skill_name, tier in raw_value.items():
        if not isinstance(skill_name, str) or not skill_name.strip():
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid {key} key: {skill_name!r} (expected non-empty string)."
            )
        normalized_name = skill_name.strip()
        validated[normalized_name] = _validate_skill_trust_tier(
            profile_name=profile_name,
            key=f"{key}.{normalized_name}",
            raw_value=tier,
        )
    return validated


def _apply_profile_backend_policy(
    *,
    profile_name: str,
    backend_policy_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Validate and apply backend_policy entries from runtime profile."""
    if not backend_policy_payload:
        return
    backend = _validate_row_backend_value(
        profile_name=profile_name,
        key="backend_policy.backend",
        raw_value=backend_policy_payload.get("backend"),
    )
    locked = _validate_optional_boolean_policy_value(
        profile_name=profile_name,
        key="backend_policy.locked",
        raw_value=backend_policy_payload.get("locked"),
        default=False,
    )
    allow_override = _validate_optional_boolean_policy_value(
        profile_name=profile_name,
        key="backend_policy.allow_override",
        raw_value=backend_policy_payload.get("allow_override"),
        default=False,
    )
    if locked and allow_override:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid backend_policy: "
            "locked=true cannot be combined with allow_override=true."
        )
    override_request_raw = os.getenv(maps.row_backend_override_env, "")
    override_request = override_request_raw.strip() if isinstance(override_request_raw, str) else ""
    effective_backend = backend
    backend_source = "profile"
    if override_request:
        override_backend = _validate_row_backend_value(
            profile_name=profile_name,
            key=f"env.{maps.row_backend_override_env}",
            raw_value=override_request,
        )
        if locked:
            raise ValueError(
                f"Runtime profile '{profile_name}' rejected {maps.row_backend_override_env}: backend policy is locked."
            )
        if not allow_override:
            raise ValueError(
                f"Runtime profile '{profile_name}' rejected {maps.row_backend_override_env}: "
                "backend override is disabled by policy."
            )
        effective_backend = override_backend
        backend_source = "override_request"
    if _set_profile_env(maps.row_backend["backend"], effective_backend, force_override=force_override):
        applied_keys.append(maps.row_backend["backend"])
    if _set_profile_env(maps.row_backend["source"], backend_source, force_override=force_override):
        applied_keys.append(maps.row_backend["source"])
    if _set_profile_env(maps.row_backend["locked"], "true" if locked else "false", force_override=force_override):
        applied_keys.append(maps.row_backend["locked"])
    if _set_profile_env(
        maps.row_backend["allow_override"],
        "true" if allow_override else "false",
        force_override=force_override,
    ):
        applied_keys.append(maps.row_backend["allow_override"])


def _validate_row_backend_value(*, profile_name: str, key: str, raw_value: Any) -> str:
    if not isinstance(raw_value, str):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected backend string)."
        )
    backend = raw_value.strip()
    if backend not in _ROW_EVALUATION_BACKENDS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} "
            f"(allowed: {', '.join(_ROW_EVALUATION_BACKENDS)})."
        )
    return backend


def _apply_profile_agent_runtime_policy(
    *,
    profile_name: str,
    agent_runtime_policy_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Validate and apply agent runtime policy from runtime profile."""
    if not agent_runtime_policy_payload:
        return
    runtime_mode = _validate_agent_runtime_mode(
        profile_name=profile_name,
        key="agent_runtime_policy.mode",
        raw_value=agent_runtime_policy_payload.get("mode"),
    )
    if _set_profile_env(maps.agent_runtime_mode_env, runtime_mode, force_override=force_override):
        applied_keys.append(maps.agent_runtime_mode_env)
    if "tool_allowlists" in agent_runtime_policy_payload:
        tool_allowlists = _validate_agent_tool_allowlists(
            profile_name=profile_name,
            key="agent_runtime_policy.tool_allowlists",
            raw_value=agent_runtime_policy_payload["tool_allowlists"],
        )
        env_key = maps.agent_runtime["tool_allowlists"]
        if _set_profile_env(env_key, json.dumps(tool_allowlists), force_override=force_override):
            applied_keys.append(env_key)
    if "non_progress_policy" in agent_runtime_policy_payload:
        non_progress_policy = _validate_agent_non_progress_policy_payload(
            profile_name=profile_name,
            key="agent_runtime_policy.non_progress_policy",
            raw_value=agent_runtime_policy_payload["non_progress_policy"],
        )
        env_key = maps.agent_runtime["non_progress_policy"]
        if _set_profile_env(env_key, json.dumps(non_progress_policy), force_override=force_override):
            applied_keys.append(env_key)


def _validate_agent_runtime_mode(*, profile_name: str, key: str, raw_value: Any) -> str:
    if not isinstance(raw_value, str):
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected runtime mode string)."
        )
    mode = raw_value.strip()
    if mode not in _AGENT_RUNTIME_MODES:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} "
            f"(allowed: {', '.join(_AGENT_RUNTIME_MODES)})."
        )
    return mode


def _validate_agent_tool_allowlists(*, profile_name: str, key: str, raw_value: Any) -> dict[str, list[str]]:
    if not isinstance(raw_value, dict):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected object map).")
    validated: dict[str, list[str]] = {}
    for agent_name, tools in raw_value.items():
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid {key} key: {agent_name!r} (expected non-empty string)."
            )
        if not isinstance(tools, list):
            raise ValueError(
                f"Runtime profile '{profile_name}' has invalid {key}.{agent_name}: {tools!r} (expected list)."
            )
        normalized_tools: list[str] = []
        for index, tool_name in enumerate(tools):
            if not isinstance(tool_name, str) or not tool_name.strip():
                raise ValueError(
                    f"Runtime profile '{profile_name}' has invalid {key}.{agent_name}[{index}]: "
                    f"{tool_name!r} (expected non-empty string)."
                )
            normalized = tool_name.strip()
            if normalized not in normalized_tools:
                normalized_tools.append(normalized)
        validated[agent_name.strip().lower()] = normalized_tools
    return validated


def _validate_agent_non_progress_policy_payload(*, profile_name: str, key: str, raw_value: Any) -> dict[str, Any]:
    if not isinstance(raw_value, dict):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected object).")
    return raw_value


def _apply_profile_agentic_policy(
    *,
    profile_name: str,
    agentic_payload: dict[str, Any],
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Validate and apply profile-level agentic policy payload."""
    if not agentic_payload:
        return
    if "non_progress_preset" in agentic_payload:
        value = _validate_non_progress_preset(
            profile_name=profile_name,
            key="agentic.non_progress_preset",
            raw_value=agentic_payload["non_progress_preset"],
        )
        env_key = maps.agentic["non_progress_preset"]
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)
    if "strict_no_fallback" in agentic_payload:
        value = _validate_boolean_policy_value(
            profile_name=profile_name,
            key="agentic.strict_no_fallback",
            raw_value=agentic_payload["strict_no_fallback"],
        )
        env_key = maps.agentic["strict_no_fallback"]
        if _set_profile_env(env_key, value, force_override=force_override):
            applied_keys.append(env_key)
    _apply_profile_scalar_policy(
        profile_name=profile_name,
        policy_name="agentic",
        policy_payload=agentic_payload,
        env_map=maps.agentic_tool_first,
        bounds_map=_AGENTIC_TOOL_FIRST_BOUNDS,
        applied_keys=applied_keys,
        force_override=force_override,
    )


def _validate_non_progress_preset(*, profile_name: str, key: str, raw_value: Any) -> str:
    if not isinstance(raw_value, str):
        raise ValueError(f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} (expected preset string).")
    preset = raw_value.strip().lower()
    if preset not in _NON_PROGRESS_PRESETS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has invalid {key}: {raw_value!r} "
            f"(allowed: {', '.join(_NON_PROGRESS_PRESETS)})."
        )
    return preset


def _auto_derive_dspy_config(
    *,
    profile_name: str,
    applied_keys: list[str],
    force_override: bool,
    maps: _EnvMaps,
) -> None:
    """Auto-derive DSPy runtime config from active protocol/model when not explicit."""
    llm_protocol = (os.getenv(maps.model_llm["type"]) or "").strip().lower()
    if llm_protocol and llm_protocol not in _SUPPORTED_PROFILE_PROTOCOLS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has unsupported {maps.model_llm['type']}='{llm_protocol}'. "
            f"Allowed protocols: {', '.join(_SUPPORTED_PROFILE_PROTOCOLS)}."
        )
    dspy_protocol = (os.getenv(maps.model_dspy["type"]) or "").strip().lower()
    if dspy_protocol and dspy_protocol not in _SUPPORTED_PROFILE_PROTOCOLS:
        raise ValueError(
            f"Runtime profile '{profile_name}' has unsupported {maps.model_dspy['type']}='{dspy_protocol}'. "
            f"Allowed protocols: {', '.join(_SUPPORTED_PROFILE_PROTOCOLS)}."
        )
    protocol = dspy_protocol or llm_protocol
    split_protocol_active = bool(dspy_protocol and llm_protocol and dspy_protocol != llm_protocol)

    dspy_model = (os.getenv(maps.model_dspy["model"]) or "").strip()
    llm_standard = (os.getenv(maps.model_llm["standard"]) or "").strip()
    if not split_protocol_active and not dspy_model and protocol and llm_standard:
        derived_model = _derive_dspy_model(protocol=protocol, llm_model_standard=llm_standard)
        if _set_profile_env(maps.model_dspy["model"], derived_model, force_override=force_override):
            applied_keys.append(maps.model_dspy["model"])
    dspy_base = (os.getenv(maps.model_dspy["base_url"]) or "").strip()
    llm_base = (os.getenv(maps.model_llm["base_url"]) or "").strip()
    if not split_protocol_active and not dspy_base and llm_base and _set_profile_env(maps.model_dspy["base_url"], llm_base, force_override=force_override):
            applied_keys.append(maps.model_dspy["base_url"])


def _derive_dspy_model(*, protocol: str, llm_model_standard: str) -> str:
    model = llm_model_standard.strip()
    if not model:
        return ""
    expected_prefix = _resolve_dspy_expected_prefix(protocol=protocol)
    if expected_prefix == "gemini":
        if model.startswith("google/"):
            return f"gemini/{model.split('/', 1)[1]}"
        if model.startswith("gemini/"):
            return model
        if "/" not in model:
            return f"gemini/{model}"
        return model
    if "/" in model:
        return model
    return f"{expected_prefix}/{model}"


def _resolve_dspy_expected_prefix(*, protocol: str) -> str:
    if protocol == "openai-codex":
        return "openai"
    if protocol == "gemini":
        return "gemini"
    return protocol


def _validate_dspy_coherence(*, profile_name: str, maps: _EnvMaps) -> None:
    """Fail fast when DSPy protocol/model pairing is incoherent."""
    protocol = (
        (os.getenv(maps.model_dspy["type"]) or "").strip() or (os.getenv(maps.model_llm["type"]) or "").strip()
    ).lower()
    dspy_model = (os.getenv(maps.model_dspy["model"]) or "").strip()
    if not protocol or not dspy_model:
        return
    if protocol not in _SUPPORTED_PROFILE_PROTOCOLS:
        return
    model_prefix = dspy_model.split("/", 1)[0].lower() if "/" in dspy_model else ""
    normalized_prefix = "gemini" if model_prefix == "google" else model_prefix
    expected_prefix = _resolve_dspy_expected_prefix(protocol=protocol)
    if model_prefix and protocol != "openai" and normalized_prefix != expected_prefix:
        raise ValueError(
            f"Runtime profile '{profile_name}' has incoherent DSPy model/protocol pairing: "
            f"protocol='{protocol}' but {maps.model_dspy['model']}='{dspy_model}'. "
            f"Expected model prefix '{expected_prefix}/...' or no prefix."
        )
    lowered_model = dspy_model.lower()
    if not model_prefix and protocol != "anthropic" and lowered_model.startswith("claude-"):
        raise ValueError(
            f"Runtime profile '{profile_name}' has incoherent DSPy model/protocol pairing: "
            f"protocol='{protocol}' cannot use Anthropic-only model '{dspy_model}'."
        )
    if not model_prefix and protocol != "gemini" and lowered_model.startswith("gemini"):
        raise ValueError(
            f"Runtime profile '{profile_name}' has incoherent DSPy model/protocol pairing: "
            f"protocol='{protocol}' cannot use Google Gemini model '{dspy_model}'."
        )


def _apply_codex_chatgpt_baseline_defaults(
    *,
    profile_name: str,
    applied_keys: list[str],
    env_prefix: str,
) -> None:
    """Apply deterministic codex baseline defaults for subscription provider runs."""
    if profile_name != _CODEX_CHATGPT_PROFILE_NAME:
        return
    protocol_env = f"{env_prefix}LLM_PROTOCOL"
    protocol = str(os.getenv(protocol_env) or "").strip().lower()
    if protocol != "openai-codex":
        return
    defaults = _CODEX_CHATGPT_BASELINE_ENV_DEFAULTS
    if env_prefix != "VDS_AUDIT_":
        defaults = {k.replace("VDS_AUDIT_", env_prefix): v for k, v in defaults.items()}
    for env_key, value in defaults.items():
        if _set_profile_env(env_key, value, force_override=False):
            applied_keys.append(env_key)
