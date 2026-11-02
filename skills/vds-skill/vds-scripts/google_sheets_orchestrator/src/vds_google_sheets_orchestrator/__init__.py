"""Google Sheets orchestrator for VDS."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    """Lazy import attributes for faster module loading."""
    if name == "GoogleSheetsClient":
        from vds_google_sheets_orchestrator.client import GoogleSheetsClient

        return GoogleSheetsClient

    if name == "GoogleSheetsSettings":
        from vds_google_sheets_orchestrator.config import GoogleSheetsSettings

        return GoogleSheetsSettings

    if name == "load_settings":
        from vds_google_sheets_orchestrator.config import load_settings

        return load_settings

    if name == "GoogleSheetsError":
        from vds_google_sheets_orchestrator.errors import GoogleSheetsError

        return GoogleSheetsError

    if name == "AuthenticationError":
        from vds_google_sheets_orchestrator.errors import AuthenticationError

        return AuthenticationError

    if name == "AuthorizationError":
        from vds_google_sheets_orchestrator.errors import AuthorizationError

        return AuthorizationError

    if name == "SpreadsheetNotFoundError":
        from vds_google_sheets_orchestrator.errors import SpreadsheetNotFoundError

        return SpreadsheetNotFoundError

    if name == "WorksheetNotFoundError":
        from vds_google_sheets_orchestrator.errors import WorksheetNotFoundError

        return WorksheetNotFoundError

    if name == "app":
        from vds_google_sheets_orchestrator.cli import app

        return app

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "GoogleSheetsClient",
    "GoogleSheetsError",
    "GoogleSheetsSettings",
    "SpreadsheetNotFoundError",
    "WorksheetNotFoundError",
    "__version__",
    "app",
    "load_settings",
]
