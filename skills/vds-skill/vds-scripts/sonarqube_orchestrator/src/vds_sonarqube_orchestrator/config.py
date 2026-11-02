"""Strongly-typed SonarQube settings using pydantic-settings.

Uses native pydantic-settings for environment variable and .env file loading.
Credentials are loaded through the shared VDS env path/config layer with os.environ overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env
from vds_platform_core.config import (
    VDS_BASE_SETTINGS_CONFIG,
    HTTPClientSettings,
    vds_settings_customise_sources,
)
from vds_platform_core.credentials import resolve_secret
from vds_platform_core.errors import SettingsError


class SonarqubeSettings(HTTPClientSettings, BaseSettings):
    """Strongly-typed SonarQube settings for code quality scanning.

    Loads configuration from:
    1. Shared VDS env file (primary credentials source)
    2. Project .env file (fallback)
    3. Environment variables (overrides everything)

    Note: Sensitive fields (token, password) use SecretStr for security.
    """

    model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="VDS_SONAR_")

    # Override HTTPClientSettings defaults with sonarqube-specific values
    connect_timeout: float = Field(default=10.0, ge=0)
    read_timeout: float = Field(default=30.0, ge=0)
    retry_backoff_initial: float = Field(default=1.5, ge=0)

    # Backward-compatibility alias (HTTPClientSettings uses read_timeout)
    @property
    def request_timeout(self) -> float:
        return self.read_timeout

    # SonarQube server URL (required)
    host_url: str = Field(
        alias="VDS_SONAR_HOST_URL",
        description="SonarQube server URL (e.g., http://sonar-10.digital.vn)",
    )

    # Authentication (optional - token preferred, username/password fallback)
    token_secret: SecretStr | None = Field(
        default=None,
        alias="VDS_SONAR_TOKEN",
        description="SonarQube authentication token (preferred)",
    )
    user: str | None = Field(
        default=None,
        alias="VDS_SONAR_USER",
        description="SonarQube username (fallback)",
    )
    password_secret: SecretStr | None = Field(
        default=None,
        alias="VDS_SONAR_PASSWORD",
        description="SonarQube password (fallback with user)",
    )

    # Default project configuration (optional - can be specified per-request)
    project_key: str | None = Field(
        default=None,
        alias="VDS_SONAR_PROJECT_KEY",
        description="Default project key",
    )
    branch_name: str | None = Field(
        default=None,
        alias="VDS_SONAR_BRANCH_NAME",
        description="Default branch name",
    )

    # SSL settings
    verify_certs: bool = Field(
        default=False,
        alias="VDS_SONAR_VERIFY_CERTS",
        description="Verify SSL certificates (false for self-signed)",
    )

    # SCA (Software Composition Analysis) settings
    sca_timeout: int = Field(
        default=300,
        alias="VDS_SONAR_SCA_TIMEOUT",
        description="SCA tool timeout in seconds (default: 300)",
    )
    sca_tool: str = Field(
        default="auto",
        alias="VDS_SONAR_SCA_TOOL",
        description="Preferred SCA tool (auto, snyk, trivy, grype, syft)",
    )
    sca_severity: str = Field(
        default="HIGH",
        alias="VDS_SONAR_SCA_SEVERITY",
        description="Minimum severity for quality gate (CRITICAL, HIGH, MEDIUM, LOW)",
    )
    snyk_token: SecretStr | None = Field(
        default=None,
        alias="VDS_SONAR_SNYK_TOKEN",
        description="Snyk authentication token (optional)",
    )
    trivy_path: str | None = Field(
        default=None,
        alias="VDS_SONAR_TRIVY_PATH",
        description="Custom path to trivy binary",
    )
    syft_path: str | None = Field(
        default=None,
        alias="VDS_SONAR_SYFT_PATH",
        description="Custom path to syft binary",
    )

    # Backward-compatibility alias (HTTPClientSettings uses retry_backoff_initial)
    @property
    def retry_backoff(self) -> float:
        return self.retry_backoff_initial

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Wrapper that uses local DEFAULT_ENV_PATHS for test compatibility."""
        return vds_settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            env_paths=DEFAULT_ENV_PATHS,
        )

    @field_validator("sca_severity", mode="before")
    @classmethod
    def _validate_sca_severity(cls, v: str) -> str:
        valid = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid sca_severity: {v}. Must be one of {valid}")
        return v.upper()

    # Property wrappers for backward compatibility - expose SecretStr values
    @property
    def token(self) -> str | None:
        """Get token value (unwrapped via platform_core.resolve_secret)."""
        return resolve_secret(self.token_secret)

    @property
    def password(self) -> str | None:
        """Get password value (unwrapped via platform_core.resolve_secret)."""
        return resolve_secret(self.password_secret)

    @property
    def base_url(self) -> str:
        """Get the normalized base URL (without trailing slash)."""
        return self.host_url.rstrip("/")

    def require_credentials(self) -> None:
        """Validate that credentials are available.

        Raises:
            ValueError: If neither token nor username/password are set.
        """
        if not self.token and not (self.user and self.password):
            raise ValueError(
                "Missing SonarQube credentials: set VDS_SONAR_TOKEN or "
                "VDS_SONAR_USER and VDS_SONAR_PASSWORD"
            )


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> SonarqubeSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source instead of DEFAULT_ENV_PATHS.
        overrides: Optional dict of values to override settings.
        strict: If True, require valid credentials (calls require_credentials).

    Returns:
        SonarqubeSettings instance with loaded configuration.

    Raises:
        SettingsError: If validation fails or strict mode requirements not met.
    """
    load_shared_env(path=env_path)
    try:
        # Build kwargs for settings instantiation
        kwargs: dict[str, Any] = {}
        if overrides:
            kwargs.update(overrides)

        # If custom env_path provided, create a custom settings class that uses it
        if env_path is not None:
            from pydantic_settings.sources import DotEnvSettingsSource

            # Create settings with custom source chain for the provided env_path
            class CustomSonarqubeSettings(SonarqubeSettings):
                @classmethod
                def settings_customise_sources(
                    cls,
                    settings_cls: type[BaseSettings],
                    init_settings: PydanticBaseSettingsSource,
                    env_settings: PydanticBaseSettingsSource,
                    dotenv_settings: PydanticBaseSettingsSource,
                    file_secret_settings: PydanticBaseSettingsSource,
                ) -> tuple[PydanticBaseSettingsSource, ...]:
                    """Custom source chain: init → env vars → custom env_path."""
                    sources: list[PydanticBaseSettingsSource] = [
                        init_settings,
                        env_settings,
                    ]
                    if env_path.exists():
                        sources.append(
                            DotEnvSettingsSource(
                                settings_cls,
                                env_file=env_path,
                                env_file_encoding="utf-8",
                            )
                        )
                    return tuple(sources)

            settings = CustomSonarqubeSettings(**kwargs)
        else:
            # Use standard settings with default source chain
            settings = SonarqubeSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        try:
            settings.require_credentials()
        except ValueError as exc:
            raise SettingsError(str(exc)) from exc

    return settings


__all__ = ["SonarqubeSettings", "SettingsError", "load_settings", "DEFAULT_ENV_PATHS"]
