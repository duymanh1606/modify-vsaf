"""Configuration management for Excel orchestrator using pydantic-settings."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env


class ExcelSettings(BaseSettings):
    """Settings for Excel orchestrator."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=True,
        populate_by_name=True,
    )

    # Excel file defaults
    default_sheet_name: str = "Sheet1"
    max_file_size_mb: int = 100
    max_sheets: int = 1000

    # Performance settings
    read_only: bool = False
    data_only: bool = False
    keep_vba: bool = False

    # Output settings
    json_output: bool = False
    pretty_print: bool = True


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, str] | None = None,
    strict: bool = False,
) -> ExcelSettings:
    """Load orchestrator settings from environment and optional .env file.

    Args:
        env_path: Optional path to .env file
        overrides: Optional dictionary of setting overrides
        strict: If True, raise errors for missing required settings

    Returns:
        ExcelSettings instance

    Raises:
        ValueError: If strict=True and required settings are missing
    """
    load_shared_env(path=env_path, override=env_path is not None)
    env_vars: dict[str, str] = dict(os.environ)

    # Apply overrides
    if overrides:
        env_vars.update(overrides)

    try:
        settings = ExcelSettings.model_validate(env_vars)
    except Exception as exc:
        if strict:
            raise ValueError(f"Failed to load settings: {exc}") from exc
        # Return defaults on non-strict mode
        return ExcelSettings()

    return settings


__all__ = ["ExcelSettings", "load_settings", "DEFAULT_ENV_PATHS"]
