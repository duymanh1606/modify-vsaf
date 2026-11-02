"""Strongly-typed Bitbucket settings using pydantic-settings (consistent with VDS orchestrators)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, ValidationError
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
from vds_platform_core.errors import SettingsError


class BitbucketSettings(HTTPClientSettings, BaseSettings):
    model_config = SettingsConfigDict(**VDS_BASE_SETTINGS_CONFIG, env_prefix="BITBUCKET_")

    # Override HTTPClientSettings retry default to match bitbucket's legacy
    # behavior (1.0s initial backoff vs platform_core's 0.5s default); alias
    # preserves the BITBUCKET_RETRY_BACKOFF env var contract.
    retry_backoff_initial: float = Field(default=1.0, alias="BITBUCKET_RETRY_BACKOFF", ge=0)

    # Backward-compat alias for code consumers (client.py uses retry_backoff_factor)
    @property
    def retry_backoff_factor(self) -> float:
        """Legacy alias for retry_backoff_initial."""
        return self.retry_backoff_initial

    username: str | None = Field(default=None, alias="VDS_USERNAME")
    password: str | None = Field(default=None, alias="VDS_PASSWORD")

    # Bitbucket Server/DC URL (for on-premise installations)
    # Primary: VDS_BITBUCKET_URL (FR-21.1.1)
    # Backward-compatible aliases: BITBUCKET_BASE_URL, VDS_BITBUCKET_HTTP_BASE
    # Priority: VDS_BITBUCKET_URL > BITBUCKET_BASE_URL > VDS_BITBUCKET_HTTP_BASE
    base_url: str = Field(
        default="http://bitbucket.digital.vn",
        validation_alias=AliasChoices(
            "VDS_BITBUCKET_URL",  # Primary (highest priority)
            "BITBUCKET_BASE_URL",  # Legacy alias
            "VDS_BITBUCKET_HTTP_BASE",  # git_orchestrator alias
        ),
    )

    # Bitbucket Cloud workspace (for cloud.bitbucket.com)
    cloud_workspace: str | None = Field(default=None, alias="BITBUCKET_CLOUD_WORKSPACE")

    # Optional: Personal Access Token for Bitbucket Cloud or Server
    token: str | None = Field(default=None, alias="BITBUCKET_TOKEN")

    # Default mode: 'cloud' or 'server'
    mode: str = Field(default="server", alias="BITBUCKET_MODE")

    # Note: max_retries is inherited from HTTPClientSettings with env_prefix
    # BITBUCKET_ → binds to BITBUCKET_MAX_RETRIES. retry_backoff_initial is
    # declared above with explicit BITBUCKET_RETRY_BACKOFF alias override.

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

    def require_basic_or_token(self) -> None:
        if not ((self.username and self.password) or self.token):
            raise ValueError("Missing credentials: set VDS_USERNAME/VDS_PASSWORD or BITBUCKET_TOKEN")

    @property
    def is_cloud_mode(self) -> bool:
        return self.mode.lower() == "cloud"

    @property
    def is_server_mode(self) -> bool:
        return self.mode.lower() == "server"

    def get_url(self) -> str:
        """Get appropriate URL based on mode."""
        if self.is_cloud_mode:
            if not self.cloud_workspace:
                raise ValueError("BITBUCKET_CLOUD_WORKSPACE is required for cloud mode")
            return f"https://api.bitbucket.org/workspace/{self.cloud_workspace}"
        return str(self.base_url)

    def auth_attempts(self) -> list[dict[str, str]]:
        """Every way to authenticate, in the order they must be tried.

        The order is load-bearing and depends on which Bitbucket this is. The list length
        is a safety limit. Do not "simplify" either one without reading this whole
        docstring.

        Two ways exist to present a Personal Access Token:

        * ``token=`` — ``atlassian-python-api`` turns it into an ``Authorization: Bearer``
          header. The documented shape, and what Bitbucket **Cloud** accepts.
        * ``username`` plus the token as ``password`` — HTTP basic auth. What our
          Bitbucket **Server** instance accepts.

        Measured against the Server instance: the Bearer client answered
        ``401 Authentication failed`` while the basic one listed all 13 repos of the
        project. Sending the token by hand with curl works all three ways, so the
        credential is fine and it is the client construction that differs.

        Which is why the order follows the mode instead of being fixed. **Every rejected
        attempt counts as a failed login against the user's account, and this server locks
        an account after very few of them — one was enough, twice, on a real account.** So
        the shape known to work for this mode has to come first and the other one is only
        the fallback for a misconfigured mode. Ordering Bearer first for everyone cost one
        failed login per command, which is how the lock kept coming back even after the
        fallback existed.

        Exactly two entries, and no loop wrapped around them anywhere. A retry loop here
        does not make the tool more robust, it takes the user's account away.

        A password configured alongside a token is deliberately not a third attempt: it is
        used only when there is no token at all, which keeps the worst case at two logins
        per command.
        """
        if self.token:
            bearer = {"token": self.token}
            basic = {"username": self.username, "password": self.token} if self.username else None
            # Server first tries what Server accepts. Without a username there is no basic
            # form to try, so Bearer is all there is either way.
            if self.is_server_mode and basic:
                return [basic, bearer]
            return [bearer] if basic is None else [bearer, basic]
        if self.username and self.password:
            return [{"username": self.username, "password": self.password}]
        raise ValueError("No valid authentication credentials available")

    def get_auth_kwargs(self) -> dict[str, str]:
        """Get authentication kwargs for atlassian-python-api.

        The first attempt only. Callers that can survive a rejected login should walk
        ``auth_attempts()`` instead, because on Bitbucket Server this first one is the
        attempt that answers 401.
        """
        return self.auth_attempts()[0]


def load_settings(
    *,
    env_path: Path | None = None,
    overrides: Mapping[str, Any] | None = None,
    strict: bool = False,
) -> BitbucketSettings:
    """Load orchestrator settings using native pydantic-settings.

    Args:
        env_path: Optional path to a specific .env file (for testing).
                 When provided, uses custom settings source instead of DEFAULT_ENV_PATHS.
        overrides: Optional mapping of values to override settings.
        strict: If True, require valid credentials (basic auth or token).

    Returns:
        BitbucketSettings instance with loaded configuration.

    Raises:
        SettingsError: If validation fails or strict mode requirements not met.
    """
    load_shared_env(path=env_path)
    try:
        kwargs: dict[str, Any] = dict(overrides) if overrides else {}

        if env_path is not None:
            from pydantic_settings.sources import DotEnvSettingsSource

            class CustomBitbucketSettings(BitbucketSettings):
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

            settings = CustomBitbucketSettings(**kwargs)
        else:
            settings = BitbucketSettings(**kwargs)

    except ValidationError as exc:
        raise SettingsError(str(exc)) from exc

    if strict:
        # Let ValueError propagate unwrapped (matches legacy contract; tests
        # use pytest.raises(ValueError, match="Missing credentials"))
        settings.require_basic_or_token()

    return settings


__all__ = ["DEFAULT_ENV_PATHS", "BitbucketSettings", "SettingsError", "load_settings"]
