"""Strongly-typed Confluence settings using pydantic-settings (consistent with VDS orchestrators)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, AnyHttpUrl, Field, SecretStr, ValidationError
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


class ConfluenceSettings(HTTPClientSettings, BaseSettings):
    """Strongly-typed view of the orchestrator settings."""

    model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="CONFLUENCE_")

    # Override HTTPClientSettings retry_backoff_initial default (1.0s vs
    # platform_core's 0.5s) and read_timeout (legacy CONFLUENCE_HTTP_TIMEOUT
    # alias). Aliases preserve the existing env var contracts.
    retry_backoff_initial: float = Field(default=1.0, alias="CONFLUENCE_RETRY_BACKOFF", ge=0)
    read_timeout: float = Field(default=30.0, alias="CONFLUENCE_HTTP_TIMEOUT", ge=0)

    # Backward-compat aliases for code consumers
    @property
    def retry_backoff_factor(self) -> float:
        """Legacy alias for retry_backoff_initial."""
        return self.retry_backoff_initial

    @property
    def http_timeout(self) -> float:
        """Legacy alias for read_timeout."""
        return self.read_timeout

    # Credential fields (cross-prefix: VDS_, INTERNAL_, EXTERNAL_)
    username: str | None = Field(default=None, alias="VDS_USERNAME")
    password: SecretStr | None = Field(default=None, alias="VDS_PASSWORD")
    internal_token: SecretStr | None = Field(default=None, alias="INTERNAL_CONFLUENCE_TOKEN")
    external_token: SecretStr | None = Field(default=None, alias="EXTERNAL_CONFLUENCE_TOKEN")

    # Canonical URLs
    internal_url: AnyHttpUrl = Field(
        default="http://confluence.digital.vn",
        alias="CONFLUENCE_INTERNAL_URL",
    )
    external_url: AnyHttpUrl = Field(
        default="http://10.254.136.35:8090",
        alias="CONFLUENCE_EXTERNAL_URL",
    )

    # Alternate URLs accept canonical name first, legacy fallback-era names
    # as secondary aliases (replaces the old _normalize_legacy_endpoint_aliases
    # procedural map with a pydantic-native AliasChoices lookup).
    external_alternate_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CONFLUENCE_EXTERNAL_ALTERNATE_URL",
            "CONFLUENCE_SECONDARY_EXTERNAL_URL",
        ),
    )
    internal_alternate_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CONFLUENCE_INTERNAL_ALTERNATE_URL",
            "CONFLUENCE_INTERNAL_FALLBACK_URL",
        ),
    )

    default_server: str = Field(default="internal", alias="CONFLUENCE_DEFAULT_SERVER")

    # Note: max_retries is inherited from HTTPClientSettings with env_prefix
    # CONFLUENCE_ → binds to CONFLUENCE_MAX_RETRIES. retry_backoff_initial and
    # read_timeout are declared above with explicit legacy aliases.

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

    def token_for(self, server: str) -> str | None:
        server_lower = server.lower()
        if server_lower in {"internal", "int", "main"}:
            return resolve_secret(self.internal_token)
        if server_lower in {"external", "ext", "outsource"}:
            return resolve_secret(self.external_token)
        raise ValueError(f"Unknown server '{server}'")

    def url_for(self, server: str) -> AnyHttpUrl:
        server_lower = server.lower()
        if server_lower in {"internal", "int", "main"}:
            return self.internal_url
        if server_lower in {"external", "ext", "outsource"}:
            return self.external_url
        raise ValueError(f"Unknown server '{server}'")

    def external_urls(self) -> list[AnyHttpUrl]:
        """Return all configured external server URLs (primary first, alternate if set)."""
        urls: list[AnyHttpUrl] = [self.external_url]
        if self.external_alternate_url is not None:
            urls.append(self.external_alternate_url)
        return urls

    @property
    def default_token(self) -> str | None:
        return self.token_for(self.default_server)

    @property
    def default_url(self) -> AnyHttpUrl:
        return self.url_for(self.default_server)


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: Mapping[str, Any] | None = None,
    strict: bool = False,
) -> ConfluenceSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source that places the
                 env_path file BEFORE runtime env vars (preserves legacy
                 load_shared_env(override=True) semantics).
        overrides: Optional mapping of values to override settings.
        strict: If True, require valid credentials (basic auth or token).

    Returns:
        ConfluenceSettings instance with loaded configuration.

    Raises:
        SettingsError: If validation fails or strict mode requirements not met.
    """
    load_shared_env(path=env_path)
    try:
        kwargs: dict[str, Any] = dict(overrides) if overrides else {}

        if env_path is not None:
            from pydantic_settings.sources import DotEnvSettingsSource

            class CustomConfluenceSettings(ConfluenceSettings):
                @classmethod
                def settings_customise_sources(
                    cls,
                    settings_cls: type[BaseSettings],
                    init_settings: PydanticBaseSettingsSource,
                    env_settings: PydanticBaseSettingsSource,
                    dotenv_settings: PydanticBaseSettingsSource,
                    file_secret_settings: PydanticBaseSettingsSource,
                ) -> tuple[PydanticBaseSettingsSource, ...]:
                    """Custom source chain: init → custom env_path → env vars.

                    env_path precedes env_settings so explicit test/override
                    files beat ambient runtime env (preserves legacy
                    load_shared_env(override=True) semantics).
                    """
                    sources: list[PydanticBaseSettingsSource] = [init_settings]
                    if env_path.exists():
                        sources.append(
                            DotEnvSettingsSource(
                                settings_cls,
                                env_file=env_path,
                                env_file_encoding="utf-8",
                            )
                        )
                    sources.append(env_settings)
                    return tuple(sources)

            settings = CustomConfluenceSettings(**kwargs)
        else:
            settings = ConfluenceSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        has_token = bool(settings.internal_token or settings.external_token)
        has_basic_auth = bool(settings.username and settings.password)
        if not (has_token or has_basic_auth):
            raise SettingsError(
                "Missing Confluence credentials. Provide VDS_USERNAME+VDS_PASSWORD as the primary auth mechanism, "
                "or INTERNAL_CONFLUENCE_TOKEN/EXTERNAL_CONFLUENCE_TOKEN as fallback in the shared VDS env file "
                "(or run './scripts/worktree_uv.sh run --project vds_cli vds-cli env load')."
            )

    return settings


__all__ = ["DEFAULT_ENV_PATHS", "ConfluenceSettings", "SettingsError", "load_settings"]
