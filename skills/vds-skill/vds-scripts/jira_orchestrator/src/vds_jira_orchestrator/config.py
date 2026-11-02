"""Strongly-typed Jira settings using pydantic-settings (SDK-only).

Uses native pydantic-settings for environment variable and .env file loading.
Credentials are loaded through the shared VDS env path/config layer with os.environ overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, field_validator
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


class JiraSettings(HTTPClientSettings, BaseSettings):
    """Strongly-typed Jira settings.

    Loads configuration from:
    1. Shared VDS env file (primary credentials source)
    2. Project .env file (fallback)
    3. Environment variables (overrides everything)

    Note: Sensitive fields (password, token) use SecretStr for security.
    Access via properties that unwrap the values for backward compatibility.
    Inherits HTTPClientSettings for connect_timeout/read_timeout/max_retries/
    retry_backoff_* fields with platform_core defaults.
    """

    model_config = SettingsConfigDict(**{**VDS_BASE_SETTINGS_CONFIG, "env_file": None}, env_prefix="JIRA_")

    # Non-sensitive fields
    username: str | None = Field(default=None, alias="VDS_USERNAME")
    base_url: str = Field(default="http://jira.digital.vn", alias="JIRA_BASE_URL")

    # Sensitive credentials - stored as SecretStr for security
    password_secret: SecretStr | None = Field(default=None, alias="VDS_PASSWORD")
    token_secret: SecretStr | None = Field(default=None, alias="JIRA_TOKEN")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Delegate to platform_core helper with local DEFAULT_ENV_PATHS."""
        return vds_settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            env_paths=DEFAULT_ENV_PATHS,
        )

    # Property wrappers for backward compatibility - expose SecretStr values as strings
    @property
    def password(self) -> str | None:
        """Get password value (unwrapped from SecretStr)."""
        return resolve_secret(self.password_secret)

    @property
    def token(self) -> str | None:
        """Get token value (unwrapped from SecretStr)."""
        return resolve_secret(self.token_secret)

    def require_basic_or_token(self) -> None:
        """Validate that either basic auth or token is available."""
        if not ((self.username and self.password) or self.token):
            raise ValueError("Missing credentials: set VDS_USERNAME/VDS_PASSWORD or JIRA_TOKEN")

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        AnyHttpUrl(value)
        return value.rstrip("/")


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
    strict: bool = False,
) -> JiraSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source instead of DEFAULT_ENV_PATHS.
        overrides: Optional dict of values to override settings.
        strict: If True, require valid credentials (basic auth or token).

    Returns:
        JiraSettings instance with loaded configuration.

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
            class CustomJiraSettings(JiraSettings):
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

            settings = CustomJiraSettings(**kwargs)
        else:
            # Use standard settings with default source chain
            settings = JiraSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        try:
            settings.require_basic_or_token()
        except ValueError as exc:
            raise SettingsError(str(exc)) from exc

    return settings


__all__ = ["DEFAULT_ENV_PATHS", "JiraSettings", "SettingsError", "load_settings"]
