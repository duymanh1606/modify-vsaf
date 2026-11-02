"""Confluence automation orchestrator for VDS."""

from __future__ import annotations

from vds_platform_core.errors import (
    AuthError,
    ClientPermissionError,
    ConflictError,
    NotFoundError,
    RateLimitError,
)
from vds_platform_core.http.errors import register_http_error_mapping

__version__ = "0.2.0"

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

from .config import ConfluenceSettings, load_settings
from .http import ConfluenceClient
from .protocols import ConfluenceClientProtocol


def __getattr__(name: str) -> object:
    """Lazy import of public API members."""
    if name == "ConfluenceSettings":
        from confluence_orchestrator.config import ConfluenceSettings

        return ConfluenceSettings
    if name == "SettingsError":
        from vds_platform_core.errors import SettingsError

        return SettingsError
    if name == "load_settings":
        from confluence_orchestrator.config import load_settings

        return load_settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ConfluenceClient",
    "ConfluenceClientProtocol",
    "ConfluenceSettings",
    "SettingsError",
    "load_settings",
]
