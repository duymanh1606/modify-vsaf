"""Strongly-typed Jira ViettelMoney settings using pydantic-settings (SDK-only)."""

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
    HTTPClientSettings,
    VDS_BASE_SETTINGS_CONFIG,
    vds_settings_customise_sources,
)
from vds_platform_core.credentials import resolve_secret
from vds_platform_core.errors import SettingsError


class JiraViettelMoneySettings(HTTPClientSettings, BaseSettings):
    """Settings for jira.viettelmoney.vn.

    Credentials read from ~/.vds/.env via:
      JIRA_VIETTELMONEY_USERNAME, JIRA_VIETTELMONEY_PASSWORD, JIRA_VIETTELMONEY_BASE_URL
      JIRA_VIETTELMONEY_PROXY  (optional, e.g. http://10.254.148.131:8800)
    """

    model_config = SettingsConfigDict(
        **{**VDS_BASE_SETTINGS_CONFIG, "env_file": None}, env_prefix="JIRA_VIETTELMONEY_"
    )

    username: str | None = Field(default=None, alias="JIRA_VIETTELMONEY_USERNAME")
    base_url: str = Field(
        default="https://jira.viettelmoney.vn", alias="JIRA_VIETTELMONEY_BASE_URL"
    )
    # Proxy is passed per-request via requests.Session — not set system-wide
    proxy_url: str | None = Field(default="http://10.254.148.131:8800", alias="JIRA_VIETTELMONEY_PROXY")

    password_secret: SecretStr | None = Field(default=None, alias="JIRA_VIETTELMONEY_PASSWORD")
    token_secret: SecretStr | None = Field(default=None, alias="JIRA_VIETTELMONEY_TOKEN")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return vds_settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            env_paths=DEFAULT_ENV_PATHS,
        )

    @property
    def password(self) -> str | None:
        return resolve_secret(self.password_secret)

    @property
    def token(self) -> str | None:
        return resolve_secret(self.token_secret)

    def require_basic_or_token(self) -> None:
        if not ((self.username and self.password) or self.token):
            raise ValueError(
                "Missing credentials: set JIRA_VIETTELMONEY_USERNAME/JIRA_VIETTELMONEY_PASSWORD or JIRA_VIETTELMONEY_TOKEN"
            )

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
) -> JiraViettelMoneySettings:
    load_shared_env(path=env_path)
    try:
        kwargs: dict[str, Any] = {}
        if overrides:
            kwargs.update(overrides)

        if env_path is not None:
            from pydantic_settings.sources import DotEnvSettingsSource

            class CustomSettings(JiraViettelMoneySettings):
                @classmethod
                def settings_customise_sources(
                    cls,
                    settings_cls: type[BaseSettings],
                    init_settings: PydanticBaseSettingsSource,
                    env_settings: PydanticBaseSettingsSource,
                    dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
                    file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
                ) -> tuple[PydanticBaseSettingsSource, ...]:
                    sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
                    if env_path.exists():
                        sources.append(
                            DotEnvSettingsSource(
                                settings_cls,
                                env_file=env_path,
                                env_file_encoding="utf-8",
                            )
                        )
                    return tuple(sources)

            settings = CustomSettings(**kwargs)
        else:
            settings = JiraViettelMoneySettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        try:
            settings.require_basic_or_token()
        except ValueError as exc:
            raise SettingsError(str(exc)) from exc

    return settings


__all__ = ["JiraViettelMoneySettings", "SettingsError", "load_settings", "DEFAULT_ENV_PATHS"]
