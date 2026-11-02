"""VDS Jira Orchestrator - Jira integration using atlassian-python-api SDK."""

from __future__ import annotations

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

from .errors import SERVICE_NAME as _SERVICE_NAME

__version__ = "0.1.0"

for _status, _error_cls in (
    (401, AuthError),
    (403, ClientPermissionError),
    (404, NotFoundError),
    (409, ConflictError),
    (429, RateLimitError),
):
    register_http_error_mapping(_SERVICE_NAME, _status, _error_cls)
del _status, _error_cls


def __getattr__(name: str) -> object:
    """Lazy import attributes for faster module loading.

    This function implements lazy imports, meaning modules are only loaded
    when their attributes are actually accessed. This improves startup time
    and reduces memory usage for imports that aren't used.
    """
    if name == "JiraAdapter":
        from vds_jira_orchestrator.adapter import JiraAdapter

        return JiraAdapter

    if name == "JiraSettings":
        from vds_jira_orchestrator.config import JiraSettings

        return JiraSettings

    if name == "load_settings":
        from vds_jira_orchestrator.config import load_settings

        return load_settings

    if name == "SettingsError":
        from vds_jira_orchestrator.config import SettingsError

        return SettingsError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "JiraAdapter",
    "JiraSettings",
    "load_settings",
    "SettingsError",
]
