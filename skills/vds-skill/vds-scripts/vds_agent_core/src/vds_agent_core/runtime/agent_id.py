"""Agent ID sanitization + registry for per-agent settings (FR-226.4, NFR-226.4).

The sanitizer maps a free-form agent_id to an env-var- and log-friendly form.
Hyphens, dots, slashes -> underscores; result is uppercased. Collisions are
detected via an in-memory registry so two distinct agent IDs cannot silently
share the same env-var prefix.
"""

from __future__ import annotations

import re
from threading import Lock

# In-memory collision detection: sanitized -> original (first-writer-wins).
_AGENT_ID_REGISTRY: dict[str, str] = {}
_AGENT_ID_LOCK = Lock()

# Allowed characters in raw agent_id input.
_VALID_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_.\-/]+$")
_REPLACE_RE = re.compile(r"[-./]")


class AgentIdCollisionError(ValueError):
    """Two agent IDs sanitize to the same key (e.g. 'agent-1' and 'agent.1')."""


def sanitize_agent_id(agent_id: str) -> str:
    """Map an agent_id to a safe env-var/log-friendly form.

    Hyphens, dots, slashes -> underscores. Uppercased.

    Collision detection: if a different original maps to the same sanitized
    form, raise :class:`AgentIdCollisionError`. Idempotent for the same
    agent_id.

    Raises:
        ValueError: agent_id is empty/non-str or contains invalid characters.
        AgentIdCollisionError: sanitized form already used by a different ID.
    """
    if not agent_id or not isinstance(agent_id, str):
        raise ValueError(f"agent_id must be a non-empty string; got {agent_id!r}")
    if not _VALID_AGENT_ID_RE.match(agent_id):
        raise ValueError(f"agent_id contains invalid characters: {agent_id!r}")
    sanitized = _REPLACE_RE.sub("_", agent_id).upper()
    with _AGENT_ID_LOCK:
        existing = _AGENT_ID_REGISTRY.get(sanitized)
        if existing is None:
            _AGENT_ID_REGISTRY[sanitized] = agent_id
        elif existing != agent_id:
            raise AgentIdCollisionError(
                f"agent_id {agent_id!r} sanitizes to {sanitized!r}, "
                f"already used by {existing!r}"
            )
    return sanitized


def reset_agent_id_registry() -> None:
    """Test helper: clear the in-memory registry (do not call in production)."""
    with _AGENT_ID_LOCK:
        _AGENT_ID_REGISTRY.clear()
