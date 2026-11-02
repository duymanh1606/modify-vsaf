"""Strongly-typed VIDP settings using pydantic-settings.

Loads from the shared VDS env file (~/.vds/.env) with prefix `VDS_VIDP_`.
Accepts legacy `VIDP_*` env variables as aliases so existing VIDP MCP
deployments keep working without re-configuring credentials.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import load_shared_env
from vds_platform_core.credentials import resolve_secret
from vds_platform_core.errors import SettingsError


class VidpSettings(BaseSettings):
    """VIDP gateway settings."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=False,
    )

    base_url: str = Field(
        validation_alias=AliasChoices("VDS_VIDP_BASE_URL", "VIDP_BASE_URL"),
        description="VIDP base URL (e.g. https://idp.example.com/)",
    )
    username: str = Field(
        validation_alias=AliasChoices("VDS_VIDP_USERNAME", "VIDP_USERNAME"),
        description="Basic-auth username",
    )
    password_secret: SecretStr = Field(
        validation_alias=AliasChoices("VDS_VIDP_PASSWORD", "VIDP_PASSWORD"),
        description="Basic-auth password",
    )
    timeout_ms: int = Field(
        default=30_000,
        ge=1,
        validation_alias=AliasChoices("VDS_VIDP_TIMEOUT_MS", "VIDP_TIMEOUT_MS"),
        description="HTTP request timeout in milliseconds",
    )

    @property
    def password(self) -> str:
        return resolve_secret(self.password_secret) or ""

    @property
    def timeout_seconds(self) -> float:
        return self.timeout_ms / 1000.0

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/") + "/"

    @property
    def auth_header(self) -> dict[str, str]:
        token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {"Authorization": f"Basic {token}"}


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> VidpSettings:
    """Load VIDP settings from shared env + environment variables."""
    load_shared_env(path=env_path)
    try:
        return VidpSettings(**(overrides or {}))
    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc


__all__ = ["VidpSettings", "load_settings", "SettingsError"]
