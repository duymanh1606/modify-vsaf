from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConfluenceClientProtocol(Protocol):
    """Canonical Confluence client protocol for audit-facing operations."""

    async def get_page(self, page_id: str, *, expand: str | None = None) -> dict[str, Any] | None: ...
    async def search_cql(self, cql: str, limit: int = 25, start: int = 0) -> list[dict[str, Any]]: ...
    async def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body_file: Any,
        parent_id: str | None = None,
    ) -> dict[str, Any]: ...
    async def update_page(
        self,
        page_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        body_file: Any | None = None,
        version: int | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]: ...
    async def list_child_pages(self, page_id: str) -> list[dict[str, Any]]: ...
    async def create_or_update_page(
        self,
        *,
        space_key: str,
        title: str,
        body_file: Any,
        parent_id: str | None = None,
    ) -> dict[str, Any]: ...
    async def upload_attachment(self, *, page_id: str, file_path: Any) -> dict[str, Any]: ...
    async def delete_page(self, page_id: str) -> None: ...
    async def move_page(
        self,
        page_id: str,
        target_title: str,
        position: str = "append",
        *,
        space_key: str | None = None,
    ) -> dict[str, Any]: ...
    async def get_page_conditional(
        self,
        page_id: str,
        *,
        etag: str | None = None,
        last_modified: Any | None = None,
        cached_version: int | str | None = None,
        expand: str | None = None,
    ) -> tuple[bool, dict[str, Any] | None]: ...
    async def resolve_tiny_url(self, tiny_id: str) -> str | None: ...


__all__ = ["ConfluenceClientProtocol"]
