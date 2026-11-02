"""Shared 3-layer settings cascade for ``for_agent()`` factories (Phase 225 W2).

Both :class:`vds_agent_core.llm.provider.LLMSettings` and
:class:`vds_agent_core.llm.embedding.EmbeddingSettings` use this helper to
implement the per-agent resolution cascade described in FR-226.1, FR-226.2,
and FR-226.7.

Resolution precedence (highest -> lowest):
    1. Path C  -- ``overrides`` kwargs (programmatic, e.g. tests/replays)
    2. Path B  -- ``api_settings.<api_attr>`` (Agent model from Redis/API)
    3. Path A  -- ``VDS_AGENT_<SANITIZED_ID>_<ENV_PREFIX>__*`` env vars
    4. Layer 1+2 defaults: ``cls()`` (BaseSettings + orchestrator subclass)

When Path A and Path B disagree on a field, Path B wins and a structured WARN
log records the staleness (FR-226.7). The construction itself is
side-effect-free (no I/O, FR-226.11) -- network probes belong in startup
health-checks, not here.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import TYPE_CHECKING, Any

import structlog

from vds_agent_core.runtime.agent_id import sanitize_agent_id

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings

logger = structlog.get_logger(__name__)


# One-shot resolution log set (NFR-226.1) keyed by (agent_id, kind).
_RESOLUTION_LOG_SEEN: set[tuple[str, str]] = set()
_RESOLUTION_LOG_LOCK = Lock()


def _log_resolution_once(agent_id: str, kind: str, resolved: dict[str, Any]) -> None:
    """Emit a single INFO log per (agent_id, kind) pair (NFR-226.1)."""
    key = (agent_id, kind)
    with _RESOLUTION_LOG_LOCK:
        if key in _RESOLUTION_LOG_SEEN:
            return
        _RESOLUTION_LOG_SEEN.add(key)
    logger.info(
        "for_agent_resolved",
        agent_id=agent_id,
        kind=kind,
        provider=resolved.get("provider"),
        model_standard=resolved.get("model_standard"),
        base_url=resolved.get("base_url"),
    )


def _reset_resolution_log() -> None:
    """Test helper: clear the one-shot log set."""
    with _RESOLUTION_LOG_LOCK:
        _RESOLUTION_LOG_SEEN.clear()


def resolve_for_agent(
    cls: type[BaseSettings],
    agent_id: str,
    *,
    kind: str,
    env_prefix_template: str,
    api_attr: str,
    profile: str | None = None,
    api_settings: Any = None,
    overrides: dict[str, Any] | None = None,
) -> Any:
    """Build a settings instance for ``agent_id`` via the 3-layer cascade.

    Args:
        cls: The settings class to construct (e.g. ``LLMSettings``).
        agent_id: Agent identifier; sanitized internally.
        kind: ``"llm"`` or ``"embedding"`` (used in log/env-prefix).
        env_prefix_template: Format string with ``{sanitized}`` placeholder
            for the env-var prefix (e.g. ``"VDS_AGENT_{sanitized}_LLM__"``).
        api_attr: Attribute name on ``api_settings`` to read for Path B
            (e.g. ``"llm_settings"`` or ``"embedding_settings"``).
        profile: Reserved for W3 profile YAML resolution; accepted but the
            full enforcement (NFR-225.13 ``allowed_agents``) lands in W3.
        api_settings: Optional Agent model loaded from Redis/API (Path B).
        overrides: Programmatic kwargs (Path C).

    Returns:
        Newly constructed settings instance.
    """
    sanitized = sanitize_agent_id(agent_id)

    # Layer 1+2 -- defaults from BaseSettings (env file + cls env_prefix).
    base = cls()  # FR-226.12: no-args path must continue to work.
    field_names = set(cls.model_fields.keys())

    # Path A -- env vars VDS_AGENT_<SANITIZED>_<KIND>__<FIELD>.
    path_a: dict[str, Any] = {}
    prefix = env_prefix_template.format(sanitized=sanitized)
    for key, val in os.environ.items():
        if key.startswith(prefix):
            field_name = key[len(prefix) :].lower()
            if field_name in field_names:
                path_a[field_name] = val

    # Path B -- api_settings.<api_attr> (Agent model dict).
    path_b: dict[str, Any] = {}
    if api_settings is not None and hasattr(api_settings, api_attr):
        attr_data = getattr(api_settings, api_attr) or {}
        if isinstance(attr_data, dict):
            path_b = {k: v for k, v in attr_data.items() if k in field_names}

    # Path C -- programmatic overrides.
    path_c: dict[str, Any] = {k: v for k, v in (overrides or {}).items() if k in field_names}

    # Compose resolution: base < A < B < C.
    resolved: dict[str, Any] = base.model_dump()
    resolved.update(path_a)

    # FR-226.7 -- WARN when Path B differs from Path A (Path B wins).
    for field, b_value in path_b.items():
        a_value = path_a.get(field)
        if a_value is not None and a_value != b_value:
            logger.warning(
                "for_agent_path_conflict",
                agent_id=agent_id,
                kind=kind,
                field=field,
                path_a_value=a_value,
                path_b_value=b_value,
                winner="path_b",
            )
    resolved.update(path_b)
    resolved.update(path_c)

    # NFR-226.1 -- one-shot resolution log.
    if os.environ.get("VDS_AGENT_CORE__LOG_RESOLUTION", "").lower() == "true":
        _log_resolution_once(agent_id, kind, resolved)

    # FR-226.11 -- side-effect-free settings construction.
    return cls(**resolved)
