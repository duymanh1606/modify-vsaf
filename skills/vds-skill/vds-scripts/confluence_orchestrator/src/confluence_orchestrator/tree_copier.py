"""Confluence page-tree copy orchestrator.

Three-phase implementation:
  1. Crawl  — BFS walk of source tree → dict[page_id, PageNode]
  2. Copy   — Create/update pages in BFS order, copy attachments + labels
  3. Remap  — Rewrite internal links in all copied pages via regex
"""

from __future__ import annotations

import io
import re
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from .content import ContentClient

_log = structlog.get_logger(__name__)

_100MB = 100 * 1024 * 1024  # NFR-05: warn before downloading attachments > 100 MB

# Pattern 1: module-level constant — matches any ri:content-id attribute.
# Filtering against page_map is done in code (not the regex itself).
_CONTENT_ID_RE = re.compile(r'ri:content-id="(\d+)"')


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PageNode:
    """Immutable snapshot of one source page."""

    page_id: str
    title: str
    body_storage: str
    children: tuple[str, ...]  # child page IDs
    attachments: tuple[AttachmentMeta, ...]
    labels: tuple[str, ...]


@dataclass(frozen=True)
class AttachmentMeta:
    """Metadata for one attachment (no content bytes — fetched on demand)."""

    attachment_id: str
    filename: str
    content_type: str
    size: int  # bytes


@dataclass(frozen=True)
class CopyOptions:
    """Configuration for the copy operation."""

    skip_attachments: bool = False
    skip_labels: bool = False
    skip_link_remap: bool = False
    dry_run: bool = False
    max_depth: int | None = None  # None = unlimited; ceiling enforced in CLI (NFR-05)


@dataclass
class CopyResult:
    """Mutable result accumulator."""

    page_map: dict[str, str] = field(default_factory=dict)  # source_id → target_id
    pages_created: int = 0
    pages_updated: int = 0  # root page is updated, not created
    attachments_copied: int = 0
    labels_copied: int = 0
    links_remapped: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# TreeCopier
# ---------------------------------------------------------------------------


class TreeCopier:
    """Copies a Confluence page tree from one space/server to another."""

    def __init__(
        self,
        source_client: ContentClient,
        target_client: ContentClient,
        target_space_key: str,
        source_space_key: str,
        options: CopyOptions | None = None,
    ) -> None:
        self._source = source_client
        self._target_client = target_client
        self._target_space_key = target_space_key
        self._source_space_key = source_space_key
        self._options = options or CopyOptions()
        self._log = _log.bind(
            source_space=source_space_key,
            target_space=target_space_key,
        )
        # Base URLs for Pattern 4 link remapping (absolute URL rewrite)
        self._source_base_url = source_client.base_url
        self._target_base_url = target_client.base_url

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def copy_tree(
        self,
        source_root_id: str,
        target_root_id: str,
    ) -> CopyResult:
        """Main entry point. Runs all 3 phases."""
        self._log.info("copy_tree_start", source_root=source_root_id, target_root=target_root_id)
        page_tree = self._crawl_source(source_root_id)

        if self._options.dry_run:
            total_size = sum(att.size for node in page_tree.values() for att in node.attachments)
            self._log.info(
                "dry_run_summary",
                pages=len(page_tree),
                total_attachment_bytes=total_size,
            )
            return CopyResult(
                page_map=dict.fromkeys(page_tree, ""),
                pages_created=len(page_tree) - 1,  # root is updated, not created
                attachments_copied=sum(len(n.attachments) for n in page_tree.values()),
            )

        result = self._copy_pages(page_tree, source_root_id, target_root_id)
        if not self._options.skip_link_remap:
            self._remap_links(result, page_tree)
        self._log.info(
            "copy_tree_done",
            pages_created=result.pages_created,
            pages_updated=result.pages_updated,
            attachments_copied=result.attachments_copied,
            labels_copied=result.labels_copied,
            links_remapped=result.links_remapped,
            errors=len(result.errors),
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: Crawl
    # ------------------------------------------------------------------

    def _crawl_source(self, root_id: str) -> dict[str, PageNode]:
        """BFS walk of source tree. Returns {page_id: PageNode}."""
        tree: dict[str, PageNode] = {}
        # Queue items: (page_id, depth)
        queue: deque[tuple[str, int]] = deque([(root_id, 0)])
        while queue:
            page_id, depth = queue.popleft()
            if page_id in tree:
                continue
            if self._options.max_depth is not None and depth > self._options.max_depth:
                continue
            node = self._fetch_page_node(page_id)
            tree[page_id] = node
            self._log.debug("page_crawled", page_id=page_id, title=node.title, depth=depth)
            for child_id in node.children:
                queue.append((child_id, depth + 1))
        self._log.info("crawl_complete", total_pages=len(tree))
        return tree

    def _fetch_page_node(self, page_id: str) -> PageNode:
        """Fetch one page's content, attachments, and labels."""
        page = self._source.get_page(page_id, expand=["body.storage", "space"])
        body_storage = page.get("body", {}).get("storage", {}).get("value", "")

        # Children
        children_raw = self._source.get_child_pages(page_id)
        children = tuple(str(c["id"]) for c in children_raw if isinstance(c, dict) and "id" in c)

        # Attachments — list_attachments() returns {"results": [...]}
        raw_atts = self._source.list_attachments(page_id).get("results", [])
        attachments = tuple(
            AttachmentMeta(
                attachment_id=str(att["id"]),
                filename=str(att.get("title", f"attachment_{att['id']}")),
                content_type=str(att.get("metadata", {}).get("mediaType", "application/octet-stream")),
                size=int(att.get("extensions", {}).get("fileSize", 0)),
            )
            for att in raw_atts
            if isinstance(att, dict) and "id" in att
        )

        # Labels
        labels = tuple(self._source.get_page_labels(page_id))

        return PageNode(
            page_id=page_id,
            title=str(page.get("title", "")),
            body_storage=body_storage,
            children=children,
            attachments=attachments,
            labels=labels,
        )

    # ------------------------------------------------------------------
    # Phase 2: Copy
    # ------------------------------------------------------------------

    def _copy_pages(
        self,
        page_tree: dict[str, PageNode],
        source_root_id: str,
        target_root_id: str,
    ) -> CopyResult:
        """Create/update pages in BFS order. Copy attachments and labels."""
        result = CopyResult()
        result.page_map[source_root_id] = target_root_id  # seed root mapping

        # Queue items: (source_id, target_parent_id)
        # For root the target_parent_id is unused — the target page ID comes from page_map.
        queue: deque[tuple[str, str]] = deque([(source_root_id, "")])

        while queue:
            source_id, target_parent_id = queue.popleft()
            node = page_tree.get(source_id)
            if node is None:
                continue

            is_root = source_id == source_root_id
            existing_target_id = result.page_map.get(source_id) if is_root else None

            try:
                new_target_id = self._copy_single_page(
                    node,
                    target_parent_id=target_parent_id,
                    is_root=is_root,
                    target_page_id=existing_target_id,
                )
            except Exception as exc:
                msg = f"Failed to copy page {source_id!r} ({node.title!r}): {exc}"
                self._log.error(
                    "page_copy_failed",
                    source_id=source_id,
                    title=node.title,
                    exc_info=True,
                )
                result.errors.append(msg)
                # Skip entire subtree when a page fails (duplicate title, auth error, etc.)
                continue

            result.page_map[source_id] = new_target_id
            if is_root:
                result.pages_updated += 1
            else:
                result.pages_created += 1

            # Attachments
            if not self._options.skip_attachments and node.attachments:
                result.attachments_copied += self._copy_attachments(node, new_target_id, result)

            # Labels
            if not self._options.skip_labels and node.labels:
                result.labels_copied += self._copy_labels(node, new_target_id, result)

            # Enqueue children (only those present in the crawled tree)
            for child_id in node.children:
                if child_id in page_tree:
                    queue.append((child_id, new_target_id))

        return result

    def _copy_single_page(
        self,
        node: PageNode,
        target_parent_id: str,
        is_root: bool,
        target_page_id: str | None,
    ) -> str:
        """Copy one page. Returns the target page ID."""
        if is_root and target_page_id is not None:
            # Update root page body; preserve the target page's own title
            self._target_client.update_page(
                target_page_id,
                body=node.body_storage,
                representation="storage",
            )
            self._log.info("page_updated", source_id=node.page_id, target_id=target_page_id)
            return target_page_id

        created = self._target_client.create_page(
            space_key=self._target_space_key,
            title=node.title,
            body=node.body_storage,
            parent_id=target_parent_id,
            representation="storage",
        )
        new_id = str(created["id"])
        self._log.info("page_created", source_id=node.page_id, target_id=new_id, title=node.title)
        return new_id

    def _copy_attachments(
        self,
        node: PageNode,
        target_page_id: str,
        result: CopyResult,
    ) -> int:
        """Download from source, upload to target. Returns count of copied attachments."""
        copied = 0
        for att in node.attachments:
            if att.size > _100MB:
                self._log.warning(
                    "large_attachment",
                    attachment_id=att.attachment_id,
                    filename=att.filename,
                    size_bytes=att.size,
                )
            try:
                content = self._source._http.get_attachment_content(att.attachment_id)
                self._target_client.upload_attachment(
                    target_page_id,
                    io.BytesIO(content),
                    filename=att.filename,
                    content_type=att.content_type,
                )
                copied += 1
            except Exception as exc:
                msg = f"Attachment {att.attachment_id!r} ({att.filename!r}) failed: {exc}"
                self._log.error(
                    "attachment_copy_failed",
                    attachment_id=att.attachment_id,
                    filename=att.filename,
                    exc_info=True,
                )
                result.errors.append(msg)
        return copied

    def _copy_labels(
        self,
        node: PageNode,
        target_page_id: str,
        result: CopyResult,
    ) -> int:
        """Copy labels to target page. Returns count of successfully applied labels."""
        copied = 0
        for label in node.labels:
            try:
                self._target_client.set_page_label(target_page_id, label)
                copied += 1
            except Exception as exc:
                msg = f"Label {label!r} on page {node.page_id!r} failed: {exc}"
                self._log.warning(
                    "label_copy_failed",
                    label=label,
                    source_id=node.page_id,
                    target_page_id=target_page_id,
                    exc_info=True,
                )
                result.errors.append(msg)
        return copied

    # ------------------------------------------------------------------
    # Phase 3: Remap links
    # ------------------------------------------------------------------

    def _remap_links(
        self,
        result: CopyResult,
        page_tree: dict[str, PageNode],
    ) -> None:
        """Rewrite internal links in all copied pages.

        Four pattern classes (FR-01.5):
          1. ri:content-id="<old_id>" → remapped ID (only IDs in page_map)
          2. ri:space-key="<source_space>" → target space key
          3. /display/<source_space>/ relative paths → target space
          4. <source_base_url>/display/<source_space>/ absolute URLs → target
        """
        # Patterns 2–4 are compiled at runtime because they embed source_space_key
        # and source_base_url which are only known at runtime.  They MUST NOT be
        # pre-compiled as module-level constants — re.Pattern has no .format().
        escaped_space = re.escape(self._source_space_key)
        escaped_base_url = re.escape(self._source_base_url)

        space_key_re = re.compile(rf'ri:space-key="{escaped_space}"')
        display_url_re = re.compile(rf"/display/{escaped_space}/")
        abs_url_re = re.compile(rf"{escaped_base_url}/display/{escaped_space}/")

        def _remap_id(m: re.Match[str]) -> str:
            mapped = result.page_map.get(m.group(1))
            return f'ri:content-id="{mapped}"' if mapped else m.group(0)

        for _source_id, target_id in result.page_map.items():
            if not target_id:  # dry-run placeholder
                continue
            try:
                page = self._target_client.get_page(target_id, expand=["body.storage"])
                body = page.get("body", {}).get("storage", {}).get("value", "")
                new_body = body

                new_body, n1 = _CONTENT_ID_RE.subn(_remap_id, new_body)
                new_body, n2 = space_key_re.subn(f'ri:space-key="{self._target_space_key}"', new_body)
                # Pattern 4 must run before Pattern 3: abs URL contains /display/space/ as a
                # substring. If Pattern 3 fires first it rewrites the space portion, leaving the
                # source base URL intact and making Pattern 4 unable to match.
                new_body, n4 = abs_url_re.subn(f"{self._target_base_url}/display/{self._target_space_key}/", new_body)
                new_body, n3 = display_url_re.subn(f"/display/{self._target_space_key}/", new_body)

                result.links_remapped += n1 + n2 + n3 + n4
                if new_body != body:
                    self._target_client.update_page(target_id, body=new_body)
                    self._log.debug(
                        "links_remapped",
                        target_id=target_id,
                        replacements=n1 + n2 + n3 + n4,
                    )
            except Exception as exc:
                msg = f"Link remap failed for target {target_id!r}: {exc}"
                self._log.error("remap_failed", target_id=target_id, exc_info=True)
                result.errors.append(msg)


__all__ = [
    "AttachmentMeta",
    "CopyOptions",
    "CopyResult",
    "PageNode",
    "TreeCopier",
]
