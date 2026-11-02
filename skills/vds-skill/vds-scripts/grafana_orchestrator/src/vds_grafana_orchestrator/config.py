"""Strongly-typed Grafana settings using pydantic-settings.

Uses native pydantic-settings for environment variable and .env file loading.
Credentials are loaded through the shared VDS env path/config layer with
os.environ overrides.

All Quickwit operations go through Grafana Datasource Proxy.

Inherits HTTP timeout/retry fields from HTTPClientSettings.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env
from vds_platform_core.config import (
    HTTPClientSettings,
)
from vds_platform_core.credentials import resolve_secret
from vds_platform_core.errors import SettingsError


class GrafanaSettings(HTTPClientSettings, BaseSettings):
    """Strongly-typed Grafana settings for datasource proxy access.

    Loads configuration from:
    1. Shared VDS env file (primary credentials source)
    2. Project .env file (fallback)
    3. Environment variables (overrides everything)

    Inherits HTTP timeout/retry fields from HTTPClientSettings.
    Note: Sensitive fields (password, token) use SecretStr for security.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # Don't auto-load .env files; env vars only
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        env_prefix="VDS_GRAFANA_",
    )

    # Override HTTPClientSettings defaults with grafana-specific values
    connect_timeout: float = Field(default=10.0, ge=0)
    read_timeout: float = Field(default=30.0, ge=0)
    retry_backoff_initial: float = Field(default=1.0, ge=0)

    # Backward-compatibility alias (HTTPClientSettings uses read_timeout)
    @property
    def request_timeout(self) -> float:
        return self.read_timeout

    # Backward-compatibility alias (HTTPClientSettings uses retry_backoff_initial)
    @property
    def retry_backoff(self) -> float:
        return self.retry_backoff_initial

    # Grafana URL (required)
    grafana_url: str = Field(
        alias="VDS_GRAFANA_URL",
        description="Grafana base URL (e.g., http://10.207.58.64:8485/)",
    )

    # Authentication (optional - either basic auth or token)
    user: str | None = Field(
        default=None,
        alias="VDS_GRAFANA_USER",
        description="Grafana basic auth username",
    )
    password_secret: SecretStr | None = Field(
        default=None,
        alias="VDS_GRAFANA_PASSWORD",
        description="Grafana basic auth password",
    )
    token_secret: SecretStr | None = Field(
        default=None,
        alias="VDS_GRAFANA_TOKEN",
        description="Grafana service account token (alternative to basic auth)",
    )

    # Datasource configuration (optional - can be specified per-request)
    datasource_uid: str | None = Field(
        default=None,
        alias="VDS_GRAFANA_DATASOURCE_UID",
        description="Default datasource UID (preferred)",
    )
    datasource_id: int | None = Field(
        default=None,
        alias="VDS_GRAFANA_DATASOURCE_ID",
        description="Default datasource ID (legacy)",
    )
    datasource_name: str | None = Field(
        default=None,
        alias="VDS_GRAFANA_DATASOURCE_NAME",
        description="Default datasource name",
    )

    # Quickwit defaults
    default_index: str | None = Field(
        default=None,
        alias="VDS_QUICKWIT_INDEX",
        description="Default Quickwit index pattern",
    )

    # SSL settings
    verify_certs: bool = Field(
        default=False,
        alias="VDS_GRAFANA_VERIFY_CERTS",
        description="Verify SSL certificates (false for self-signed)",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """No dotenv loading - env vars only via os.environ/env file."""
        return (init_settings, env_settings)

    # Property wrappers for backward compatibility - expose SecretStr values
    @property
    def password(self) -> str | None:
        """Get password value (unwrapped via platform_core.resolve_secret)."""
        return resolve_secret(self.password_secret)

    @property
    def token(self) -> str | None:
        """Get token value (unwrapped via platform_core.resolve_secret)."""
        return resolve_secret(self.token_secret)

    @property
    def auth_header(self) -> dict[str, str]:
        """Get the appropriate authorization header.

        Returns Bearer token auth if token is set, otherwise Basic auth.
        Returns empty dict if no credentials are configured.
        """
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        if self.user and self.password:
            credentials = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            return {"Authorization": f"Basic {credentials}"}
        return {}

    @property
    def base_url(self) -> str:
        """Get the normalized base URL (without trailing slash)."""
        return self.grafana_url.rstrip("/")

    def require_credentials(self) -> None:
        """Validate that credentials are available.

        Raises:
            ValueError: If neither token nor basic auth credentials are set.
        """
        if not self.token and not (self.user and self.password):
            raise ValueError(
                "Missing Grafana credentials: set VDS_GRAFANA_TOKEN or "
                "VDS_GRAFANA_USER and VDS_GRAFANA_PASSWORD"
            )

    def has_datasource_config(self) -> bool:
        """Check if any datasource configuration is set."""
        return bool(self.datasource_uid or self.datasource_id or self.datasource_name)


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> GrafanaSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source instead of DEFAULT_ENV_PATHS.
        overrides: Optional dict of values to override settings.
        strict: If True, require valid credentials (calls require_credentials).

    Returns:
        GrafanaSettings instance with loaded configuration.

    Raises:
        SettingsError: If validation fails or strict mode requirements not met.
    """
    load_shared_env(path=env_path)
    try:
        kwargs: dict[str, Any] = {}
        if overrides:
            kwargs.update(overrides)

        if env_path is not None:
            from pydantic_settings.sources import DotEnvSettingsSource

            class CustomGrafanaSettings(GrafanaSettings):
                @classmethod
                def settings_customise_sources(
                    cls,
                    settings_cls: type[BaseSettings],
                    init_settings,
                    env_settings,
                    dotenv_settings,
                    file_secret_settings,
                ) -> tuple:
                    sources = [init_settings, env_settings]
                    if env_path.exists():
                        sources.append(
                            DotEnvSettingsSource(
                                settings_cls,
                                env_file=env_path,
                                env_file_encoding="utf-8",
                            )
                        )
                    return tuple(sources)

            settings = CustomGrafanaSettings(**kwargs)
        else:
            settings = GrafanaSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        try:
            settings.require_credentials()
        except ValueError as exc:
            raise SettingsError(str(exc)) from exc

    return settings


__all__ = ["GrafanaSettings", "SettingsError", "load_settings", "DEFAULT_ENV_PATHS"]
