"""Path and configuration helpers for VDS scripts."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "vds"
APP_AUTHOR = "VDS"
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _PROJECT_ROOT.parent


def _default_vds_home() -> Path:
    return Path.home() / ".vds"


def _optional_override(env_key: str) -> Path | None:
    raw = (os.getenv(env_key) or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def get_vds_config_root() -> Path:
    override = _optional_override("VDS_CONFIG_DIR")
    if override is not None:
        return override
    return _default_vds_home()


def get_vds_cache_root() -> Path:
    override = _optional_override("VDS_CACHE_DIR")
    if override is not None:
        return override
    return get_vds_config_root() / "cache"


def get_vds_data_root() -> Path:
    override = _optional_override("VDS_DATA_DIR")
    if override is not None:
        return override
    return get_vds_config_root() / "data"


def get_vds_log_root() -> Path:
    override = _optional_override("VDS_LOG_DIR")
    if override is not None:
        return override
    return get_vds_config_root() / "logs"


def get_shared_env_path() -> Path:
    override = _optional_override("VDS_ENV_FILE")
    if override is not None:
        return override
    return get_vds_config_root() / ".env"


def get_scripts_dir() -> Path:
    return _SCRIPTS_DIR


def get_default_env_paths() -> tuple[Path, ...]:
    return (get_shared_env_path(),)


__all__ = [
    "APP_AUTHOR",
    "APP_NAME",
    "get_default_env_paths",
    "get_scripts_dir",
    "get_shared_env_path",
    "get_vds_cache_root",
    "get_vds_config_root",
    "get_vds_data_root",
    "get_vds_log_root",
]
