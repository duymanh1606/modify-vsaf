"""Shared settings helpers for VDS orchestrators."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import DotEnvSettingsSource, PydanticBaseSettingsSource

from vds_platform_core.env import DEFAULT_ENV_PATHS

if TYPE_CHECKING:
    from vds_platform_core.protocols import RetryPolicy

VDS_BASE_SETTINGS_CONFIG = {
    "env_file": "~/.vds/.env",
    "env_file_encoding": "utf-8",
    "extra": "ignore",
    "dotenv_filtering": "match_prefix",
    "env_nested_delimiter": "__",
    "case_sensitive": False,
    "populate_by_name": True,
}


def vds_settings_customise_sources(
    settings_cls: type[BaseSettings],
    init_settings: PydanticBaseSettingsSource,
    env_settings: PydanticBaseSettingsSource,
    dotenv_settings: PydanticBaseSettingsSource,
    file_secret_settings: PydanticBaseSettingsSource,
    *,
    env_paths: Iterable[Path] | None = None,
) -> tuple[PydanticBaseSettingsSource, ...]:
    """Return a common settings source chain for VDS packages."""
    sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
    candidates = tuple(env_paths) if env_paths is not None else DEFAULT_ENV_PATHS

    for env_path in candidates:
        resolved = env_path.expanduser()
        if resolved.exists():
            sources.append(
                DotEnvSettingsSource(
                    settings_cls,
                    env_file=resolved,
                    env_file_encoding="utf-8",
                )
            )

    return tuple(sources)


class HTTPClientSettings(BaseSettings):
    """Pydantic-settings mixin providing HTTP timeout + retry fields.

    Compose with a concrete settings class:
        class MySettings(HTTPClientSettings, BaseSettings):
            model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="MY_")
    """

    model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG)

    connect_timeout: float = Field(5.0, ge=0)
    read_timeout: float = Field(30.0, ge=0)
    write_timeout: float = Field(30.0, ge=0)
    pool_timeout: float = Field(5.0, ge=0)
    max_retries: int = Field(3, ge=0, le=20)
    retry_backoff_initial: float = Field(0.5, ge=0)
    retry_backoff_multiplier: float = Field(2.0, ge=1)
    retry_max_wait: float = Field(60.0, ge=0)
    rate_limit_aware: bool = True

    def to_retry_policy(self) -> RetryPolicy:
        """Return an exponential_backoff RetryPolicy configured from these fields."""
        from vds_platform_core.http.retry import exponential_backoff

        return exponential_backoff(  # type: ignore[return-value]
            max_attempts=self.max_retries,
            initial_wait=self.retry_backoff_initial,
            multiplier=self.retry_backoff_multiplier,
            max_wait=self.retry_max_wait,
        )


__all__ = ["VDS_BASE_SETTINGS_CONFIG", "HTTPClientSettings", "vds_settings_customise_sources"]
