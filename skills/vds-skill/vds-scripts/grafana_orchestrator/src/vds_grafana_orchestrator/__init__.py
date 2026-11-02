"""VDS Grafana Orchestrator - Query logs via Grafana datasource proxy.

This package provides:
- GrafanaClient: Low-level Grafana API client
- QuickwitClient: High-level Quickwit log query client
- CLI: Command-line interface for log queries
- Configuration: pydantic-settings based config from the shared VDS env path/config layer

Example:
    >>> from vds_grafana_orchestrator import GrafanaClient, load_settings
    >>> settings = load_settings()
    >>> with GrafanaClient(settings) as client:
    ...     health = client.health()
    ...     print(health)
"""

from __future__ import annotations

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

__version__ = "0.1.0"

from .errors import SERVICE_NAME as _SERVICE_NAME

for _status, _error_cls in (
    (401, AuthError),
    (403, ClientPermissionError),
    (404, NotFoundError),
    (409, ConflictError),
    (429, RateLimitError),
):
    register_http_error_mapping(_SERVICE_NAME, _status, _error_cls)
del _status, _error_cls


# Lazy imports to avoid circular dependencies and speed up CLI startup
def __getattr__(name: str):
    """Lazy import pattern for public API."""
    if name == "GrafanaSettings":
        from vds_grafana_orchestrator.config import GrafanaSettings

        return GrafanaSettings
    if name == "load_settings":
        from vds_grafana_orchestrator.config import load_settings

        return load_settings
    if name == "SettingsError":
        from vds_grafana_orchestrator.config import SettingsError

        return SettingsError
    if name == "GrafanaClient":
        from vds_grafana_orchestrator.client import GrafanaClient

        return GrafanaClient
    if name == "QuickwitClient":
        from vds_grafana_orchestrator.client import QuickwitClient

        return QuickwitClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    # Config
    "GrafanaSettings",
    "load_settings",
    "SettingsError",
    # Client
    "GrafanaClient",
    "QuickwitClient",
]
