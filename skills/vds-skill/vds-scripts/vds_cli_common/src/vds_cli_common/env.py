"""Shared environment loader for VDS scripts."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

# DEFAULT_ENV_PATHS lifted to platform_core.env (TSK-7.12b layering fix).
# Re-exported here for backward compatibility.
from vds_cli_common.paths import get_default_env_paths, get_shared_env_path

DEFAULT_ENV_PATHS = get_default_env_paths()

DEFAULT_AUDIT_ENV_DEFAULTS: tuple[tuple[str, str], ...] = (
    ("VDS_AUDIT_STATE_DSN", "postgresql://localhost:5432/vds_audit"),
    ("VDS_AUDIT_LLM__AGENT_RUNTIME_MODE", "pydanticai"),
    ("VDS_AUDIT_LLM__DSPY_RUNTIME_RETRY_ATTEMPTS", "3"),
    ("VDS_AUDIT_LLM__DSPY_RUNTIME_RETRY_BACKOFF_SECONDS", "0"),
)


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _render_default_env_content(defaults: tuple[tuple[str, str], ...]) -> str:
    lines = [
        "# Auto-generated default environment for VDS scripts.",
        "# Safe defaults only; replace values for your environment as needed.",
        "",
    ]
    for key, value in defaults:
        lines.append(f"{key}={value}")
    lines.append("")
    lines.append("# Optional credentials")
    lines.append("# ANTHROPIC_API_KEY=")
    lines.append("# OPENAI_API_KEY=")
    lines.append("# VDS_USERNAME=")
    lines.append("# VDS_PASSWORD=")
    lines.append("# VDS_AUDIT_LANGGRAPH__POSTGRES_DSN=postgresql://user:password@host:5432/database")
    lines.append("")
    return "\n".join(lines)


def ensure_shared_env(
    path: Path | None = None,
    *,
    defaults: tuple[tuple[str, str], ...] = DEFAULT_AUDIT_ENV_DEFAULTS,
) -> Path:
    """Ensure shared env file exists and contains required default keys.

    Existing values are never overwritten.
    """
    env_path = path or get_shared_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    if not env_path.exists():
        env_path.write_text(_render_default_env_content(defaults), encoding="utf-8")
        return env_path

    existing = _parse_env_file(env_path)
    missing = [(key, value) for key, value in defaults if key not in existing]
    if not missing:
        return env_path

    with env_path.open("a", encoding="utf-8") as handle:
        handle.write("\n# Added missing VDS defaults\n")
        for key, value in missing:
            handle.write(f"{key}={value}\n")
    return env_path


def _collect_shared_env_values(
    path: Path | None = None,
    *,
    ensure_defaults: bool = True,
    extra_paths: tuple[Path, ...] | None = None,
) -> dict[str, str]:
    primary_path = path or get_shared_env_path()
    if ensure_defaults:
        ensure_shared_env(primary_path)

    env_paths = (primary_path,)
    if extra_paths:
        env_paths = tuple(env_paths) + tuple(extra_paths)
    merged: dict[str, str] = {}
    for env_path in env_paths:
        for key, value in _parse_env_file(env_path).items():
            merged.setdefault(key, value)
    return merged


def render_shared_env_exports(
    path: Path | None = None,
    *,
    override: bool = False,
    ensure_defaults: bool = True,
    extra_paths: tuple[Path, ...] | None = None,
) -> str:
    """Return shell export lines for shared env keys.

    Existing process env wins by default so wrapper scripts can safely hydrate
    missing runtime values from `~/.vds/.env` without clobbering explicit
    session overrides.
    """

    merged = _collect_shared_env_values(
        path,
        ensure_defaults=ensure_defaults,
        extra_paths=extra_paths,
    )
    exports: list[str] = []
    for key, value in merged.items():
        if override or key not in os.environ:
            exports.append(f"export {key}={shlex.quote(value)}")
    return "\n".join(exports)


def load_shared_env(
    path: Path | None = None,
    override: bool = False,
    *,
    ensure_defaults: bool = True,
    extra_paths: tuple[Path, ...] | None = None,
) -> dict[str, str]:
    """Load VDS env files into os.environ."""
    merged = _collect_shared_env_values(
        path,
        ensure_defaults=ensure_defaults,
        extra_paths=extra_paths,
    )
    for key, value in merged.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return merged


__all__ = [
    "DEFAULT_AUDIT_ENV_DEFAULTS",
    "DEFAULT_ENV_PATHS",
    "ensure_shared_env",
    "load_shared_env",
    "render_shared_env_exports",
]
