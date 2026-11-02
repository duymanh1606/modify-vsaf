"""Configuration settings for Google Sheets orchestrator."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env
from vds_cli_common.paths import get_vds_config_root

DEFAULT_ENV_PATH = DEFAULT_ENV_PATHS[0]


class GoogleSheetsSettings(BaseSettings):
    """Settings loaded from the shared VDS env/config layer using the VDS_GOOGLE_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="VDS_GOOGLE_",
        env_file=str(DEFAULT_ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    credentials_path: Path = get_vds_config_root() / "google_credentials.json"
    oauth_credentials_path: Path = get_vds_config_root() / "gspread_oauth.json"
    api_key_path: Path = get_vds_config_root() / "google_api_key.txt"
    api_key: str | None = None
    default_auth_method: str = "service_account"


def load_settings(
    *,
    env_file: Path | None = None,
    overrides: Mapping[str, str] | None = None,
) -> GoogleSheetsSettings:
    """Load settings with optional env file override and explicit overrides."""

    load_shared_env(path=env_file)
    kwargs = dict(overrides or {})
    if env_file is not None:
        return GoogleSheetsSettings(_env_file=env_file, **kwargs)
    return GoogleSheetsSettings(**kwargs)


__all__ = ["DEFAULT_ENV_PATH", "GoogleSheetsSettings", "load_settings"]
