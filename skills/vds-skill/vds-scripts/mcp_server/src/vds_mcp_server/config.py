"""Configuration management for MCP server.

Based on pydantic-settings v2.12.0+ API
Context7: /pydantic/pydantic-settings
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import DEFAULT_ENV_PATHS, load_shared_env


class MCPServerSettings(BaseSettings):
    """MCP server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_PATHS[0],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars not defined in this model
    )

    # VDS credentials (required for orchestrator operations)
    vds_username: str | None = None
    vds_password: str | None = None
    bitbucket_access_token: str | None = None
    internal_confluence_token: str | None = None
    external_confluence_token: str | None = None

    # MCP server settings
    server_name: str = "vds-orchestrator"
    server_version: str = "1.0.0"


def load_settings() -> MCPServerSettings:
    """Load MCP server settings from environment."""
    load_shared_env()
    return MCPServerSettings()
