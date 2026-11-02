"""Confluence REST v1 helpers covering read and write flows."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Any, BinaryIO

if TYPE_CHECKING:
    from .http import ConfluenceClient

FileLike = str | Path | BinaryIO


class ContentClient:
    """Operations against Confluence content endpoints (REST v1)."""

    def __init__(self, http_client: ConfluenceClient) -> None:
        self._http = http_client

    # ------------------------------------------------------------------
    # Read-only endpoints
    # ------------------------------------------------------------------

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
        expand: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        return self._http.search_cql(cql, limit=limit, expand=list(expand) if expand else None, start=start)

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

    def get_child_pages(
        self,
        page_id: str,
        *,
        expand: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get child pages of a page."""
        return self._http.get_child_pages(page_id, expand=list(expand) if expand else None)

    def get_page_labels(self, page_id: str) -> list[str]:
        """Get label names for a page."""
        raw = self._http.get_page_labels(page_id)
        return [lbl.get("name", "") for lbl in raw if isinstance(lbl, dict)]

    def set_page_label(self, page_id: str, label: str) -> None:
        """Add a label to a page."""
        self._http.set_page_label(page_id, label)

    @property
    def base_url(self) -> str:
        """Base URL of the underlying Confluence server (no trailing slash)."""
        return self._http.base_url

    # ------------------------------------------------------------------
    # Mutating endpoints
    # ------------------------------------------------------------------

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        representation: str = "storage",
        status: str = "current",
        notify_watchers: bool | None = None,
    ) -> dict[str, Any]:
        if notify_watchers:
            raise ValueError("notify_watchers is not supported by the Confluence Server SDK; omit the flag.")

        return self._http.create_page(
            space_key,
            title,
            body,
            parent_id=parent_id,
            representation=representation,
            status=status,
        )

    def update_page(
        self,
        page_id: str,
        *,
        title: str | None = None,
        body: str | None = None,
        space_key: str | None = None,
        representation: str = "storage",
        version: int | None = None,
        minor_edit: bool = False,
        message: str | None = None,
        status: str = "current",
        notify_watchers: bool | None = None,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        if title is None and body is None:
            raise ValueError("At least one of title/body must be provided when updating a page")

        # Get current page info if needed
        if title is None:
            current = self.get_page(page_id, expand=["version", "space", f"body.{representation}"])
            title = current["title"]
        assert title is not None

        if notify_watchers:
            raise ValueError("notify_watchers is not supported by the Confluence Server SDK; omit the flag.")

        return self._http.update_page(
            page_id,
            title,
            body,
            version=version,
            representation=representation,
            minor_edit=minor_edit,
            version_comment=message,
            status=status,
            parent_id=parent_id,
        )

    def delete_page(self, page_id: str, *, status: str = "current") -> None:
        self._http.delete_page(page_id)

    def upload_attachment(
        self,
        page_id: str,
        file: FileLike,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        with ExitStack() as stack:
            stream, resolved_name = self._prepare_file(file, filename, stack)
            # Read file content into memory for atlassian library
            content = stream.read()

            return self._http.add_attachment(
                page_id,
                resolved_name,
                content,
                content_type=content_type,
                comment=comment,
            )

    def list_attachments(self, page_id: str, *, expand: Iterable[str] | None = None) -> dict[str, Any]:
        """List attachments for a specific page."""
        result = self._http.get_attachments(page_id)
        if isinstance(result, dict):
            return result
        return {"results": result or []}

    def add_comment(self, page_id: str, body: str, *, parent_id: str | None = None) -> dict[str, Any]:
        """Add a storage-format comment to a page or reply to an existing comment."""
        if not body or not body.strip():
            raise ValueError("Comment body cannot be empty")
        return self._http.add_comment(page_id, body, parent_id=parent_id)

    def download_attachment(
        self,
        attachment_id: str,
        output_path: str | Path,
        *,
        filename: str | None = None,
    ) -> Path:
        """Download an attachment by ID to a local file."""
        content = self._http.get_attachment_content(attachment_id)
        output = Path(output_path)
        if output.is_dir():
            filename = filename or f"attachment_{attachment_id}"
            output = output / filename
        elif filename:
            output = output.parent / filename
        else:
            output.parent.mkdir(parents=True, exist_ok=True)

        output.write_bytes(content)
        return output

    def update_attachment(
        self,
        page_id: str,
        attachment_id: str,
        file: FileLike,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing attachment."""
        with ExitStack() as stack:
            stream, resolved_name = self._prepare_file(file, filename, stack)
            content = stream.read()

            return self._http.update_attachment_data(
                page_id,
                attachment_id,
                resolved_name,
                content,
                content_type=content_type,
                comment=comment,
            )

    def delete_attachment(
        self,
        page_id: str,
        attachment_id: str | None = None,
        *,
        version: int | None = None,
        filename: str | None = None,
    ) -> None:
        """Delete an attachment by ID or filename.

        If ``filename`` is provided we delegate to the SDK's delete-by-filename helper,
        which deletes the current attachment (all versions when ``version`` is None).
        Otherwise we fall back to deleting by attachment ID/version.
        """

        if filename:
            self._http.delete_attachment(page_id, filename, version=version)
            return

        if not attachment_id:
            raise ValueError("Provide attachment ID or --filename for deletion")

        self._http.delete_attachment_by_id(page_id, attachment_id, version=version)

    def move_page(
        self,
        page_id: str,
        target_title: str,
        position: str = "append",
        *,
        space_key: str | None = None,
    ) -> dict[str, Any]:
        """Move a page to a new location under the target page."""
        return self._http.move_page(page_id, target_title, position=position, space_key=space_key)

    # ------------------------------------------------------------------
    # Template operations
    # ------------------------------------------------------------------

    def list_templates(self, space_key: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if space_key:
            params["spaceKey"] = space_key
        response = self._http.request("GET", "/rest/api/template", params=params)
        payload = response.json()
        return payload if isinstance(payload, dict) else {"results": payload}

    def create_template(
        self,
        *,
        name: str,
        body: str,
        template_type: str = "page",
        space_key: str | None = None,
        description: str | None = None,
        representation: str = "storage",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": name,
            "body": {"value": body, "representation": representation},
            "templateType": template_type,
        }
        if space_key:
            payload["space"] = {"key": space_key}
        if description:
            payload["description"] = description
        response = self._http.request("POST", "/rest/api/template", json=payload)
        return response.json()

    def get_template(self, template_id: str) -> dict[str, Any]:
        response = self._http.request("GET", f"/rest/api/template/{template_id}")
        return response.json()

    def update_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        body: str | None = None,
        description: str | None = None,
        representation: str = "storage",
        template_type: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_template(template_id)
        payload = {
            "name": name or existing.get("name"),
            "templateType": template_type or existing.get("templateType", "page"),
            "description": description or existing.get("description"),
            "body": (body and {"value": body, "representation": representation}) or existing.get("body"),
        }
        response = self._http.request("PUT", f"/rest/api/template/{template_id}", json=payload)
        return response.json()

    def delete_template(self, template_id: str) -> None:
        self._http.request("DELETE", f"/rest/api/template/{template_id}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prepare_file(
        self,
        file: FileLike,
        filename: str | None,
        stack: ExitStack,
    ) -> tuple[BinaryIO, str]:
        if isinstance(file, (str, Path)):
            path = Path(file)
            stream = stack.enter_context(path.open("rb"))
            name = filename or path.name
            return stream, name

        stream = file  # BinaryIO
        inferred_name = getattr(stream, "name", None)
        resolved = filename or (Path(inferred_name).name if inferred_name else "attachment")
        return stream, resolved


__all__ = ["ContentClient"]
