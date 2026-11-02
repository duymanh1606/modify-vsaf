"""Confluence Cloud REST v2 client utilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .http import ConfluenceClient


class ContentClientV2:
    """Minimal adapter for Confluence Cloud REST v2 endpoints."""

    def __init__(self, http_client: ConfluenceClient) -> None:
        self._http = http_client

    def get_page(
        self,
        page_id: str,
        *,
        expand: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        return self._http.get_page(page_id, expand=list(expand) if expand else None)

    def search_cql(
        self,
        cql: str,
        *,
        limit: int = 25,
        start: int = 0,
        cursor: str | None = None,
        expand: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        return self._http.search_cql(
            cql,
            limit=limit,
            start=start,
            cursor=cursor,
            expand=list(expand) if expand else None,
        )

    def cql_advanced(
        self,
        cql: str,
        *,
        limit: int = 25,
        start: int = 0,
        expand: Iterable[str] | None = None,
        excerpt: str | None = None,
    ) -> dict[str, Any]:
        return self._http.cql_advanced(
            cql,
            limit=limit,
            start=start,
            expand=list(expand) if expand else None,
            excerpt=excerpt,
        )

    def search_by_space_and_type(
        self,
        *,
        space_key: str | None = None,
        content_type: str | None = None,
        limit: int = 25,
        start: int = 0,
        expand: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        return self._http.search_by_space_and_type(
            space_key=space_key,
            content_type=content_type,
            limit=limit,
            start=start,
            expand=list(expand) if expand else None,
        )

    def list_templates(
        self,
        space_key: str | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if space_key:
            params["spaceKey"] = space_key
        if cursor:
            params["cursor"] = cursor
        response = self._http.request("GET", "/wiki/api/v2/content-templates", params=params)
        return response.json()

    def get_content(
        self,
        page_id: str,
        *,
        expand: Iterable[str] | None = None,
        format: str | None = None,
    ) -> dict[str, Any]:
        """Get content by page ID - alias for get_page for compatibility."""
        return self.get_page(page_id, expand=expand)

    def get_child_pages(
        self,
        page_id: str,
        *,
        expand: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self._http.get_child_pages(page_id, expand=list(expand) if expand else None)

    def list_attachments(self, page_id: str, *, expand: Iterable[str] | None = None) -> dict[str, Any]:
        """List attachments for a specific page."""
        params: dict[str, Any] = {}
        if expand:
            params["expand"] = ",".join(expand)
        response = self._http.request("GET", f"/wiki/api/v2/pages/{page_id}/attachments", params=params)
        return response.json()

    def upload_attachment(
        self, page_id: str, file, filename: str | None = None, comment: str | None = None
    ) -> dict[str, Any]:
        """Upload attachment to a page using Confluence v2 API."""
        from pathlib import Path

        if isinstance(file, (str, Path)):
            file_path = Path(file)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            filename = filename or file_path.name
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "application/octet-stream")}
                data = {"comment": comment} if comment else None
                response = self._http.request(
                    "POST", f"/wiki/api/v2/pages/{page_id}/attachments", files=files, data=data
                )
                return response.json()
        else:
            # Handle file-like objects
            filename = filename or "upload"
            files = {"file": (filename, file, "application/octet-stream")}
            data = {"comment": comment} if comment else None
            response = self._http.request("POST", f"/wiki/api/v2/pages/{page_id}/attachments", files=files, data=data)
            return response.json()


__all__ = ["ContentClientV2"]
