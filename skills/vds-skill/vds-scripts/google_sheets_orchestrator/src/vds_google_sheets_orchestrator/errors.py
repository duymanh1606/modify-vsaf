"""Custom error types for Google Sheets orchestrator."""

from __future__ import annotations

from typing import Any


class GoogleSheetsError(RuntimeError):
    """Base error for Google Sheets orchestrator."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class AuthenticationError(GoogleSheetsError):
    """Raised when authentication fails or credentials are missing."""


class AuthorizationError(GoogleSheetsError):
    """Raised when an operation is not permitted for the auth method."""


class InvalidAuthMethodError(GoogleSheetsError):
    """Raised when an unsupported auth method is requested."""


class SpreadsheetNotFoundError(GoogleSheetsError):
    """Raised when a spreadsheet cannot be found or opened."""

    def __init__(self, url: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(f"Spreadsheet not found: {url}", context=context)
        self.url = url


class WorksheetNotFoundError(GoogleSheetsError):
    """Raised when a worksheet cannot be found."""

    def __init__(self, sheet_name: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(f"Worksheet not found: {sheet_name}", context=context)
        self.sheet_name = sheet_name
