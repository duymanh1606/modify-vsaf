"""Environment management using pydantic-settings.

Based on pydantic-settings v2.12.0+ API.
Loads VDS settings through the shared cross-platform path/config layer.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from vds_cli_common.env import load_shared_env


class VDSSettings(BaseSettings):
    """VDS environment settings loaded through the shared VDS env file."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    vds_username: str | None = None
    vds_password: str | None = None
    bitbucket_access_token: str | None = None
    bitbucket_token: str | None = None
    internal_confluence_token: str | None = None
    external_confluence_token: str | None = None
    # Git orchestrator settings (loaded from the shared VDS env file)
    vds_git_auto_regenerate_manifest: str | None = None
    vds_git_concurrency_default: str | None = None
    # Bitbucket URL configuration (FR-21.1.1)
    # Primary: VDS_BITBUCKET_URL (recommended)
    # Legacy aliases: VDS_BITBUCKET_HTTP_BASE, BITBUCKET_BASE_URL
    vds_bitbucket_url: str | None = None  # Primary env var
    vds_bitbucket_http_base: str | None = None  # Legacy alias
    bitbucket_base_url: str | None = None  # Legacy alias
    # Git network settings (timeouts, buffers, retries)
    vds_git_http_timeout: str | None = None  # seconds (default: 300)
    vds_git_http_post_buffer: str | None = None  # bytes (default: 524288000 = 500MB)
    vds_git_http_low_speed_limit: str | None = None  # bytes/sec (default: 1000 = 1KB/s)
    vds_git_http_low_speed_time: str | None = None  # seconds (default: 300)
    vds_git_retries: str | None = None  # number of retries (default: 2)
    vds_git_backoff: str | None = None  # backoff multiplier (default: 1.5)
    # Git projects configuration (comma-separated list, e.g., "lep,insurance,saving,ekyc")
    vds_git_projects: str | None = None


def parse_git_projects(projects_str: str | None) -> set[str]:
    """Parse comma-separated project list from environment variable.

    Args:
        projects_str: Comma-separated list of project IDs (e.g., "lep,insurance,saving,ekyc")

    Returns:
        Set of project IDs with whitespace trimmed

    Example:
        >>> parse_git_projects("lep,insurance,saving,ekyc")
        {'lep', 'insurance', 'saving', 'ekyc'}
        >>> parse_git_projects("lep, insurance , saving")
        {'lep', 'insurance', 'saving'}
    """
    if not projects_str:
        return set()
    return {project.strip() for project in projects_str.split(",") if project.strip()}


def get_bitbucket_url(settings: VDSSettings | None = None) -> str:
    """Get Bitbucket URL with proper priority resolution (FR-21.1.1).

    Priority order:
    1. VDS_BITBUCKET_URL (primary - recommended)
    2. VDS_BITBUCKET_HTTP_BASE (legacy alias)
    3. BITBUCKET_BASE_URL (legacy alias)
    4. Default: http://bitbucket.digital.vn/

    Args:
        settings: Optional VDSSettings instance. If None, loads from environment.

    Returns:
        Resolved Bitbucket URL (without trailing slash)

    Example:
        >>> url = get_bitbucket_url()
        >>> print(url)
        'http://bitbucket.digital.vn'
    """
    if settings is None:
        settings = load_environment()

    url = (
        settings.vds_bitbucket_url
        or settings.vds_bitbucket_http_base
        or settings.bitbucket_base_url
        or "http://bitbucket.digital.vn/"
    )
    return url.rstrip("/")


def load_environment() -> VDSSettings:
    """Load environment variables from the shared VDS env file.

    Returns:
        VDSSettings: Loaded settings instance

    Example:
        >>> settings = load_environment()
        >>> if settings.vds_username:
        ...     print("Credentials loaded")
    """
    load_shared_env()
    return VDSSettings()
