"""Workflow alias registry — map friendly names to VIDP workflow UUIDs.

Two layers, merged at lookup time:

1. **Package-shipped defaults** at ``<pkg>/workflows.json`` — curated by the
   maintainer, distributed with the npm package, read-only at runtime.
2. **User overrides** at ``~/.vds/vidp-workflows.json`` (or
   ``$VDS_VIDP_WORKFLOWS_FILE``) — optional, user-editable, takes precedence
   over package defaults. CLI ``add``/``remove`` only touch this file.

``resolve_workflow_id()`` accepts a UUID or an alias and returns the canonical
UUID. Alias lookup is case-insensitive.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def package_workflows_file() -> Path:
    """Path to the package-shipped alias registry (read-only)."""
    return Path(__file__).resolve().parent / "workflows.json"


def user_workflows_file() -> Path:
    """Path to the user-override alias registry (mutable; CLI writes here)."""
    override = os.environ.get("VDS_VIDP_WORKFLOWS_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".vds" / "vidp-workflows.json"


# Backwards-compatible name used by the CLI before the split.
def workflows_file() -> Path:
    """Deprecated alias for :func:`user_workflows_file`."""
    return user_workflows_file()


def _read_json(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).strip(): str(v).strip() for k, v in data.items() if isinstance(v, str)}


def load_package_aliases() -> dict[str, str]:
    """Aliases shipped with the package."""
    return _read_json(package_workflows_file())


def load_user_aliases() -> dict[str, str]:
    """Aliases set by the user (override layer)."""
    return _read_json(user_workflows_file())


def load_aliases() -> dict[str, str]:
    """Merged view: package defaults overlaid with user overrides."""
    merged = load_package_aliases()
    merged.update(load_user_aliases())
    return merged


def save_user_aliases(aliases: dict[str, str]) -> Path:
    """Write the user-override registry, creating parent dir if needed."""
    path = user_workflows_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(aliases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# Backwards-compatible name used by older callers.
def save_aliases(aliases: dict[str, str]) -> Path:
    """Deprecated alias for :func:`save_user_aliases`."""
    return save_user_aliases(aliases)


def is_uuid(value: str) -> bool:
    return bool(UUID_RE.match(value.strip()))


def resolve_workflow_id(name_or_id: str) -> tuple[str, str | None]:
    """Return ``(workflow_id, alias_used)``.

    - UUID input → returned as-is with ``alias_used=None``.
    - Otherwise look up case-insensitively in the merged registry.
    - Raises ``KeyError`` with a helpful message if no match.
    """
    value = name_or_id.strip()
    if is_uuid(value):
        return value, None

    aliases = load_aliases()
    if value in aliases:
        return aliases[value], value
    lower_map = {k.lower(): (k, v) for k, v in aliases.items()}
    if value.lower() in lower_map:
        canonical, wf_id = lower_map[value.lower()]
        return wf_id, canonical

    raise KeyError(
        f"No workflow id found for alias '{value}'. "
        f"Maintainer can add it to {package_workflows_file()} "
        f"(shipped with package); user can add a private alias via "
        f"'vds-cli vidp workflows add {value} <uuid>' "
        f"(writes to {user_workflows_file()})."
    )


__all__ = [
    "package_workflows_file",
    "user_workflows_file",
    "workflows_file",  # backwards-compat
    "load_package_aliases",
    "load_user_aliases",
    "load_aliases",
    "save_user_aliases",
    "save_aliases",  # backwards-compat
    "is_uuid",
    "resolve_workflow_id",
]
