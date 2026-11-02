"""Confluence page tree traversal and export utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from .http import ConfluenceClient


@dataclass
class TreeNode:
    """Represents a Confluence page in the tree."""

    page_id: str
    title: str
    space_key: str
    url: str
    children: list[TreeNode] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    body: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert tree node to dictionary."""
        return {
            "id": self.page_id,
            "title": self.title,
            "space": self.space_key,
            "url": self.url,
            "body": self.body,
            "attachments": self.attachments,
            "children": [child.to_dict() for child in self.children],
        }


class TreeExporter:
    """Recursively fetch Confluence page tree."""

    def __init__(self, client: ConfluenceClient) -> None:
        self._client = client
        self._log = structlog.get_logger(__name__)

    def build_tree(
        self,
        root_id: str,
        *,
        depth: int = -1,
        include_content: bool = False,
        include_attachments: bool = False,
    ) -> TreeNode:
        """
        Recursively build a tree of pages.

        Args:
            root_id: The root page ID to start from.
            depth: How deep to recurse. -1 for infinite, 0 for just root.
            include_content: Whether to fetch page body (storage format).
            include_attachments: Whether to fetch attachment metadata.
        """
        self._log.info("fetching_page", page_id=root_id)

        # Prepare expand fields
        expand = ["space"]
        if include_content:
            expand.append("body.storage")

        # Fetch page details
        page = self._client.get_page(root_id, expand=expand)
        title = page.get("title", "Unknown")
        space_key = page.get("space", {}).get("key", "Unknown")
        links = page.get("_links", {})
        base_url = links.get("base", "")
        web_ui = links.get("webui", "")
        full_url = f"{base_url}{web_ui}" if base_url and web_ui else web_ui

        body = None
        if include_content:
            body = page.get("body", {}).get("storage", {}).get("value")

        attachments = []
        if include_attachments:
            try:
                # This fetches metadata, not content
                attachments = self._client.get_attachments(root_id)
            except Exception as e:
                self._log.warning("failed_fetching_attachments", page_id=root_id, error=str(e))

        node = TreeNode(
            page_id=root_id,
            title=title,
            space_key=space_key,
            url=full_url,
            children=[],
            attachments=attachments,
            body=body,
        )

        # Recurse if depth allows
        if depth != 0:
            try:
                # Fetch immediate children summaries
                children_summaries = self._client.get_child_pages(root_id)

                next_depth = depth - 1 if depth > 0 else -1

                for child_summary in children_summaries:
                    child_id = child_summary.get("id")
                    if child_id:
                        child_node = self.build_tree(
                            child_id,
                            depth=next_depth,
                            include_content=include_content,
                            include_attachments=include_attachments,
                        )
                        node.children.append(child_node)
            except Exception as e:
                self._log.warning("failed_fetching_children", page_id=root_id, error=str(e))

        return node
