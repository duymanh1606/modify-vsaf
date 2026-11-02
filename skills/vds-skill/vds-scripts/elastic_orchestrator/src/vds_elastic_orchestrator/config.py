"""Strongly-typed Elasticsearch settings using pydantic-settings.

Uses native pydantic-settings for environment variable and .env file loading.
Credentials are loaded through the shared VDS env path/config layer with os.environ overrides.

All Elasticsearch operations go through Kibana Console Proxy since direct
ES access (port 9200) is not available in the VDS environment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env
from vds_platform_core.config import (
    HTTPClientSettings,
    vds_settings_customise_sources,
)
from vds_platform_core.errors import SettingsError


class ElasticSettings(HTTPClientSettings, BaseSettings):
    """Strongly-typed Elasticsearch settings via Kibana Console Proxy.

    Loads configuration from:
    1. Shared VDS env file (primary credentials source)
    2. Project .env file (fallback)
    3. Environment variables (overrides everything)

    Inherits HTTP timeout/retry fields from HTTPClientSettings.
    Note: Sensitive fields (password) use SecretStr for security.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # Don't auto-load .env files; env vars only
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        env_prefix="VDS_ELASTIC_",
    )

    # Override HTTPClientSettings defaults with elastic-specific values
    connect_timeout: float = Field(default=10.0, ge=0)
    read_timeout: float = Field(default=30.0, ge=0)
    retry_backoff_initial: float = Field(default=1.0, ge=0)

    # Backward-compatibility: request_timeout aliased env var → read_timeout
    request_timeout: float = Field(
        default=30.0,
        alias="VDS_ELASTIC_REQUEST_TIMEOUT",
        description="Alias for read_timeout to support legacy request_timeout env var",
    )

    # Backward-compatibility: retry_backoff aliased env var → retry_backoff_initial
    retry_backoff: float = Field(
        default=1.0,
        alias="VDS_ELASTIC_RETRY_BACKOFF",
        description="Alias for retry_backoff_initial to support legacy retry_backoff env var",
    )

    # Kibana proxy settings (required)
    kibana_url: str = Field(
        alias="VDS_ELASTIC_KIBANA_URL",
        description="Kibana hostname for Host header (e.g., log.digital.vn)",
    )
    kibana_ip: str = Field(
        alias="VDS_ELASTIC_KIBANA_IP",
        description="Kibana internal IP for connection (e.g., 10.207.56.26)",
    )

    # Authentication (required)
    user: str = Field(
        alias="VDS_ELASTIC_USER",
        description="Username for basic auth",
    )
    password_secret: SecretStr = Field(
        alias="VDS_ELASTIC_PASSWORD",
        description="Password for basic auth",
    )

    # SSL settings
    verify_certs: bool = Field(
        default=False,
        alias="VDS_ELASTIC_VERIFY_CERTS",
        description="Verify SSL certificates (false for self-signed)",
    )

    # Search defaults
    default_index: str = Field(
        default="*",
        alias="VDS_ELASTIC_DEFAULT_INDEX",
        description="Default index pattern for search operations",
    )
    default_time_field: str = Field(
        default="@timestamp",
        alias="VDS_ELASTIC_DEFAULT_TIME_FIELD",
        description="Default time field for time-based queries",
    )
    default_size: int = Field(
        default=10,
        alias="VDS_ELASTIC_DEFAULT_SIZE",
        description="Default result size for search operations",
    )

    settings_customise_sources = vds_settings_customise_sources

    # Property wrapper for backward compatibility - expose SecretStr value as string
    @property
    def password(self) -> str:
        """Get password value (unwrapped from SecretStr)."""
        return self.password_secret.get_secret_value()

    def require_credentials(self) -> None:
        """Validate that credentials are available.

        Raises:
            ValueError: If user or password is missing.
        """
        if not self.user:
            raise ValueError("Missing VDS_ELASTIC_USER")
        if not self.password:
            raise ValueError("Missing VDS_ELASTIC_PASSWORD")

    @property
    def base_url(self) -> str:
        """Get the base URL for Kibana connection."""
        return f"https://{self.kibana_ip}"

    @property
    def proxy_endpoint(self) -> str:
        """Get the console proxy endpoint path."""
        return "/api/console/proxy"


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> ElasticSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source instead of DEFAULT_ENV_PATHS.
        overrides: Optional dict of values to override settings.
        strict: If True, require valid credentials (calls require_credentials).

    Returns:
        ElasticSettings instance with loaded configuration.

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

            class CustomElasticSettings(ElasticSettings):
                @classmethod
                def settings_customise_sources(
                    cls,
                    settings_cls: type[BaseSettings],
                    init_settings,
                    env_settings,
                    _dotenv_settings,
                    _file_secret_settings,
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

            settings = CustomElasticSettings(**kwargs)
        else:
            settings = ElasticSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        try:
            settings.require_credentials()
        except ValueError as exc:
            raise SettingsError(str(exc)) from exc

    return settings


__all__ = ["ElasticSettings", "SettingsError", "load_settings", "DEFAULT_ENV_PATHS"]
