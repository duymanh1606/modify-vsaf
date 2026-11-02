"""Google Sheets client wrapper."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import gspread
import structlog
from gspread.auth import DEFAULT_SCOPES, READONLY_SCOPES
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from .config import GoogleSheetsSettings
from .errors import (
    AuthenticationError,
    AuthorizationError,
    GoogleSheetsError,
    InvalidAuthMethodError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)

logger = structlog.get_logger(__name__)


class GoogleSheetsClient:
    """Wrapper around gspread with VDS-standard auth handling."""

    def __init__(
        self,
        settings: GoogleSheetsSettings | None = None,
        *,
        auth_method: str | None = None,
        credentials_path: Path | None = None,
        oauth_credentials_path: Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self.settings = settings or GoogleSheetsSettings()
        self.auth_method = (auth_method or self.settings.default_auth_method).lower()
        self.credentials_path = credentials_path or self.settings.credentials_path
        self.oauth_credentials_path = oauth_credentials_path or self.settings.oauth_credentials_path
        self.api_key = api_key or self.settings.api_key
        if not self.api_key and self.settings.api_key_path.exists():
            self.api_key = self.settings.api_key_path.read_text(encoding="utf-8").strip()

    def _ensure_writable(self) -> None:
        if self.auth_method == "api_key":
            raise AuthorizationError("API key authentication is read-only and cannot perform write operations.")

    def _get_client(self, *, read_only: bool = False) -> gspread.Client:
        scopes = READONLY_SCOPES if read_only else DEFAULT_SCOPES

        if self.auth_method == "service_account":
            if not self.credentials_path.exists():
                raise AuthenticationError(f"Service account credentials not found at {self.credentials_path}")
            return gspread.service_account(filename=str(self.credentials_path), scopes=scopes)

        if self.auth_method == "oauth":
            if not self.oauth_credentials_path.exists():
                raise AuthenticationError(f"OAuth credentials not found at {self.oauth_credentials_path}")
            authorized_user_path = self.oauth_credentials_path.with_name("gspread_authorized_user.json")
            return gspread.oauth(
                credentials_filename=str(self.oauth_credentials_path),
                authorized_user_filename=str(authorized_user_path),
                scopes=scopes,
            )

        if self.auth_method == "api_key":
            if not self.api_key:
                raise AuthenticationError("VDS_GOOGLE_API_KEY is required for api_key auth.")
            return gspread.api_key(self.api_key)

        raise InvalidAuthMethodError(
            f"Unsupported auth method '{self.auth_method}'. Use service_account, oauth, or api_key."
        )

    def _open_spreadsheet(self, spreadsheet_url: str, *, read_only: bool = False) -> gspread.Spreadsheet:
        client = self._get_client(read_only=read_only)
        try:
            return client.open_by_url(spreadsheet_url)
        except SpreadsheetNotFound as exc:
            raise SpreadsheetNotFoundError(spreadsheet_url, context={"auth_method": self.auth_method}) from exc
        except APIError as exc:
            raise GoogleSheetsError(
                str(exc), context={"url": spreadsheet_url, "auth_method": self.auth_method}
            ) from exc

    def read_sheet(self, spreadsheet_url: str, sheet_name: str) -> list[list[str]]:
        """Read all values from a worksheet."""
        spreadsheet = self._open_spreadsheet(spreadsheet_url, read_only=True)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(sheet_name, context={"spreadsheet_url": spreadsheet_url}) from exc
        return worksheet.get_all_values()

    def read_range(self, spreadsheet_url: str, sheet_name: str, range_name: str) -> list[list[str]]:
        """Read values from a specific A1 range in a worksheet."""
        spreadsheet = self._open_spreadsheet(spreadsheet_url, read_only=True)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(
                sheet_name, context={"spreadsheet_url": spreadsheet_url, "range": range_name}
            ) from exc
        return worksheet.get(range_name)

    def list_worksheets(self, spreadsheet_url: str) -> list[str]:
        """List worksheet titles in a spreadsheet."""
        spreadsheet = self._open_spreadsheet(spreadsheet_url, read_only=True)
        return [worksheet.title for worksheet in spreadsheet.worksheets()]

    def write_range(
        self,
        spreadsheet_url: str,
        sheet_name: str,
        target_range: str,
        values: Sequence[Sequence[str]],
    ) -> None:
        """Write values to a range in a worksheet."""
        self._ensure_writable()
        spreadsheet = self._open_spreadsheet(spreadsheet_url)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(
                sheet_name, context={"spreadsheet_url": spreadsheet_url, "range": target_range}
            ) from exc
        worksheet.update(target_range, values)

    def append_rows(
        self,
        spreadsheet_url: str,
        sheet_name: str,
        values: Sequence[Sequence[str]],
    ) -> None:
        """Append rows to the end of a worksheet."""
        self._ensure_writable()
        spreadsheet = self._open_spreadsheet(spreadsheet_url)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(sheet_name, context={"spreadsheet_url": spreadsheet_url}) from exc
        worksheet.append_rows(values)

    def clear_range(self, spreadsheet_url: str, sheet_name: str, target_range: str) -> None:
        """Clear values in a worksheet range."""
        self._ensure_writable()
        spreadsheet = self._open_spreadsheet(spreadsheet_url)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(
                sheet_name, context={"spreadsheet_url": spreadsheet_url, "range": target_range}
            ) from exc
        worksheet.batch_clear([target_range])

    def create_spreadsheet(self, title: str) -> str:
        """Create a new spreadsheet and return its URL."""
        self._ensure_writable()
        client = self._get_client()
        spreadsheet = client.create(title)
        logger.info("Created spreadsheet", title=title, url=spreadsheet.url)
        return spreadsheet.url

    def create_worksheet(
        self,
        spreadsheet_url: str,
        title: str,
        rows: int = 100,
        cols: int = 26,
    ) -> None:
        """Create a worksheet in an existing spreadsheet."""
        self._ensure_writable()
        spreadsheet = self._open_spreadsheet(spreadsheet_url)
        spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    def delete_worksheet(self, spreadsheet_url: str, sheet_name: str) -> None:
        """Delete a worksheet from a spreadsheet."""
        self._ensure_writable()
        spreadsheet = self._open_spreadsheet(spreadsheet_url)
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound as exc:
            raise WorksheetNotFoundError(sheet_name, context={"spreadsheet_url": spreadsheet_url}) from exc
        spreadsheet.del_worksheet(worksheet)
