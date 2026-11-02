"""Unit tests for TreeCopier core module (FR-01 / Package D).

Tests cover:
- Phase 1: _crawl_source BFS, PageNode construction, max_depth enforcement
- Phase 2: _copy_pages parent-first order, root=update / children=create, page_map
- _copy_attachments: get_attachment_content + upload_attachment
- _copy_labels: label copy, count
- copy_tree: full pipeline, dry_run, skip_* flags
- Edge cases: empty tree, duplicate title skip, Unicode titles, 100MB warning
"""

from __future__ import annotations

from typing import Any

import pytest
from confluence_orchestrator.tree_copier import (
    AttachmentMeta,
    CopyOptions,
    CopyResult,
    PageNode,
    TreeCopier,
)

# ---------------------------------------------------------------------------
# Mock infrastructure
# ---------------------------------------------------------------------------


class MockHttpClient:
    """Stub for ConfluenceClient's _http layer (content._http access in _copy_attachments)."""

    def __init__(self, base_url: str = "http://source.example.com") -> None:
        self.base_url = base_url
        self._attachment_data: dict[str, bytes] = {}
        self.download_calls: list[str] = []

    def get_attachment_content(self, attachment_id: str) -> bytes:
        self.download_calls.append(attachment_id)
        return self._attachment_data.get(attachment_id, b"binary-content")


class MockContentClient:
    """Full stub of ContentClient with configurable response data and call capture."""

    def __init__(self, base_url: str = "http://source.example.com") -> None:
        self._http = MockHttpClient(base_url)
        self.base_url = base_url

        # Configurable source data
        self._pages: dict[str, dict[str, Any]] = {}
        self._children: dict[str, list[dict[str, Any]]] = {}
        self._attachments: dict[str, list[dict[str, Any]]] = {}
        self._labels_by_id: dict[str, list[str]] = {}

        # Call capture
        self.created: list[dict[str, Any]] = []
        self.updated: list[dict[str, Any]] = []
        self.uploaded: list[dict[str, Any]] = []
        self.set_labels: list[tuple[str, str]] = []
        self._id_counter: int = 900

    # ── Read methods ─────────────────────────────────────────────────────

    def get_page(self, page_id: str, *, expand: list[str] | None = None) -> dict[str, Any]:
        return self._pages.get(
            page_id,
            {
                "id": page_id,
                "title": f"Page-{page_id}",
                "space": {"key": "SRC"},
                "body": {"storage": {"value": f"<p>Body of {page_id}</p>"}},
            },
        )

    def get_child_pages(self, page_id: str, *, expand: list[str] | None = None) -> list[dict[str, Any]]:
        return self._children.get(page_id, [])

    def list_attachments(self, page_id: str) -> dict[str, Any]:
        return {"results": self._attachments.get(page_id, [])}

    def get_page_labels(self, page_id: str) -> list[str]:
        return self._labels_by_id.get(page_id, [])

    # ── Write methods ─────────────────────────────────────────────────────

    def create_page(
        self,
        *,
        space_key: str,
        title: str,
        body: str,
        parent_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        new_id = str(self._id_counter)
        self._id_counter += 1
        self.created.append(
            {"id": new_id, "title": title, "parent_id": parent_id, "body": body, "space_key": space_key}
        )
        return {"id": new_id, "title": title}

    def update_page(self, page_id: str, **kwargs: Any) -> dict[str, Any]:
        self.updated.append({"page_id": page_id, **kwargs})
        return {"id": page_id}

    def upload_attachment(
        self,
        page_id: str,
        file: Any,
        *,
        filename: str | None = None,
        content_type: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.uploaded.append({"page_id": page_id, "filename": filename, "content_type": content_type})
        return {"id": "att-new"}

    def set_page_label(self, page_id: str, label: str) -> None:
        self.set_labels.append((page_id, label))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_page_resp(
    page_id: str,
    *,
    title: str = "Test Page",
    body: str = "<p>content</p>",
    space_key: str = "SRC",
) -> dict[str, Any]:
    return {
        "id": page_id,
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body}},
    }


def make_att_resp(
    attachment_id: str,
    *,
    filename: str = "file.png",
    content_type: str = "image/png",
    size: int = 1024,
) -> dict[str, Any]:
    """Build attachment dict matching the format _fetch_page_node expects."""
    return {
        "id": attachment_id,
        "title": filename,
        "metadata": {"mediaType": content_type},
        "extensions": {"fileSize": size},
    }


@pytest.fixture()
def source() -> MockContentClient:
    return MockContentClient(base_url="http://source.example.com")


@pytest.fixture()
def target() -> MockContentClient:
    return MockContentClient(base_url="http://target.example.com")


def make_copier(
    source: MockContentClient,
    target: MockContentClient,
    *,
    target_space: str = "TGT",
    source_space: str = "SRC",
    options: CopyOptions | None = None,
) -> TreeCopier:
    return TreeCopier(
        source,  # type: ignore[arg-type]
        target,  # type: ignore[arg-type]
        target_space,
        source_space,
        options,
    )


# ---------------------------------------------------------------------------
# _crawl_source
# ---------------------------------------------------------------------------


class TestCrawlSource:
    def test_single_root_no_children(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", title="Root", body="<p>hello</p>")
        tree = make_copier(source, target)._crawl_source("10")
        assert list(tree.keys()) == ["10"]
        node = tree["10"]
        assert node.page_id == "10"
        assert node.title == "Root"
        assert node.body_storage == "<p>hello</p>"
        assert node.children == ()

    def test_bfs_includes_all_descendants(self, source: MockContentClient, target: MockContentClient) -> None:
        # 10 → [11, 12], 11 → [13]
        for pid, title in [("10", "Root"), ("11", "C1"), ("12", "C2"), ("13", "GC")]:
            source._pages[pid] = make_page_resp(pid, title=title)
        source._children["10"] = [{"id": "11"}, {"id": "12"}]
        source._children["11"] = [{"id": "13"}]
        tree = make_copier(source, target)._crawl_source("10")
        assert set(tree.keys()) == {"10", "11", "12", "13"}

    def test_children_tuple_matches_api_order(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}, {"id": "12"}]
        for pid in ("11", "12"):
            source._pages[pid] = make_page_resp(pid)
        tree = make_copier(source, target)._crawl_source("10")
        assert tree["10"].children == ("11", "12")

    def test_max_depth_1_excludes_grandchildren(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}]
        source._pages["11"] = make_page_resp("11")
        source._children["11"] = [{"id": "12"}]
        source._pages["12"] = make_page_resp("12")
        tree = make_copier(source, target, options=CopyOptions(max_depth=1))._crawl_source("10")
        assert "12" not in tree
        assert "10" in tree and "11" in tree

    def test_max_depth_0_returns_only_root(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}]
        source._pages["11"] = make_page_resp("11")
        tree = make_copier(source, target, options=CopyOptions(max_depth=0))._crawl_source("10")
        assert set(tree.keys()) == {"10"}

    def test_attachments_constructed_from_api_response(
        self, source: MockContentClient, target: MockContentClient
    ) -> None:
        source._pages["10"] = make_page_resp("10")
        source._attachments["10"] = [make_att_resp("a1", filename="img.png", content_type="image/png", size=512)]
        tree = make_copier(source, target)._crawl_source("10")
        atts = tree["10"].attachments
        assert len(atts) == 1
        assert atts[0].attachment_id == "a1"
        assert atts[0].filename == "img.png"
        assert atts[0].content_type == "image/png"
        assert atts[0].size == 512

    def test_labels_collected_as_tuple(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._labels_by_id["10"] = ["api", "backend"]
        tree = make_copier(source, target)._crawl_source("10")
        assert tree["10"].labels == ("api", "backend")

    def test_empty_body_stored_as_empty_string(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", body="")
        tree = make_copier(source, target)._crawl_source("10")
        assert tree["10"].body_storage == ""


# ---------------------------------------------------------------------------
# _copy_pages
# ---------------------------------------------------------------------------


class TestCopyPages:
    def test_root_updated_not_created(self, source: MockContentClient, target: MockContentClient) -> None:
        page_tree = {
            "10": PageNode("10", "Root", "<p>r</p>", (), (), ()),
        }
        result = make_copier(source, target, options=CopyOptions(skip_attachments=True, skip_labels=True))._copy_pages(
            page_tree, "10", "T-ROOT"
        )

        assert len(target.updated) == 1
        assert target.updated[0]["page_id"] == "T-ROOT"
        assert len(target.created) == 0
        assert result.pages_updated == 1
        assert result.pages_created == 0

    def test_children_created_under_correct_parent(self, source: MockContentClient, target: MockContentClient) -> None:
        page_tree = {
            "10": PageNode("10", "Root", "", ("11",), (), ()),
            "11": PageNode("11", "Child", "<p>c</p>", (), (), ()),
        }
        result = make_copier(source, target, options=CopyOptions(skip_attachments=True, skip_labels=True))._copy_pages(
            page_tree, "10", "T-ROOT"
        )

        assert result.pages_created == 1
        assert len(target.created) == 1
        assert target.created[0]["title"] == "Child"
        assert target.created[0]["parent_id"] == "T-ROOT"

    def test_bfs_parents_created_before_children(self, source: MockContentClient, target: MockContentClient) -> None:
        # 10 → 11 → 12: "Mid" must appear in created before "Leaf"
        page_tree = {
            "10": PageNode("10", "Root", "", ("11",), (), ()),
            "11": PageNode("11", "Mid", "", ("12",), (), ()),
            "12": PageNode("12", "Leaf", "", (), (), ()),
        }
        make_copier(source, target, options=CopyOptions(skip_attachments=True, skip_labels=True))._copy_pages(
            page_tree, "10", "T-ROOT"
        )

        titles = [c["title"] for c in target.created]
        assert titles.index("Mid") < titles.index("Leaf")

    def test_page_map_contains_all_pages(self, source: MockContentClient, target: MockContentClient) -> None:
        page_tree = {
            "10": PageNode("10", "Root", "", ("11", "12"), (), ()),
            "11": PageNode("11", "C1", "", (), (), ()),
            "12": PageNode("12", "C2", "", (), (), ()),
        }
        result = make_copier(source, target, options=CopyOptions(skip_attachments=True, skip_labels=True))._copy_pages(
            page_tree, "10", "T-ROOT"
        )

        assert set(result.page_map.keys()) == {"10", "11", "12"}
        assert result.page_map["10"] == "T-ROOT"

    def test_root_mapped_to_given_target_root_id(self, source: MockContentClient, target: MockContentClient) -> None:
        page_tree = {"10": PageNode("10", "Root", "", (), (), ())}
        result = make_copier(source, target, options=CopyOptions(skip_attachments=True, skip_labels=True))._copy_pages(
            page_tree, "10", "TARGET-789"
        )
        assert result.page_map["10"] == "TARGET-789"

    def test_target_space_key_used_for_child_creation(
        self, source: MockContentClient, target: MockContentClient
    ) -> None:
        page_tree = {
            "10": PageNode("10", "Root", "", ("11",), (), ()),
            "11": PageNode("11", "Child", "", (), (), ()),
        }
        make_copier(
            source, target, target_space="DST", options=CopyOptions(skip_attachments=True, skip_labels=True)
        )._copy_pages(page_tree, "10", "T-ROOT")
        assert target.created[0]["space_key"] == "DST"


# ---------------------------------------------------------------------------
# _copy_attachments
# ---------------------------------------------------------------------------


class TestCopyAttachments:
    def _make_node_with_att(
        self,
        att_id: str,
        filename: str = "img.png",
        content_type: str = "image/png",
        size: int = 1024,
    ) -> PageNode:
        return PageNode(
            "10",
            "Root",
            "",
            (),
            (AttachmentMeta(att_id, filename, content_type, size),),
            (),
        )

    def test_downloads_from_source_http_and_uploads_to_target(
        self, source: MockContentClient, target: MockContentClient
    ) -> None:
        node = self._make_node_with_att("a1")
        source._http._attachment_data["a1"] = b"image-bytes"
        copier = make_copier(source, target)
        count = copier._copy_attachments(node, "T-10", CopyResult())
        assert count == 1
        assert source._http.download_calls == ["a1"]
        assert target.uploaded[0] == {"page_id": "T-10", "filename": "img.png", "content_type": "image/png"}

    def test_returns_count_of_copied_attachments(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode(
            "10",
            "Root",
            "",
            (),
            (
                AttachmentMeta("a1", "f1.txt", "text/plain", 100),
                AttachmentMeta("a2", "f2.txt", "text/plain", 200),
            ),
            (),
        )
        count = make_copier(source, target)._copy_attachments(node, "T-10", CopyResult())
        assert count == 2

    def test_zero_attachments_returns_zero(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode("10", "Root", "", (), (), ())
        count = make_copier(source, target)._copy_attachments(node, "T-10", CopyResult())
        assert count == 0
        assert target.uploaded == []

    def test_large_attachment_logs_warning(
        self, source: MockContentClient, target: MockContentClient, capfd: pytest.CaptureFixture[str]
    ) -> None:
        """Attachments > 100 MB must log a warning before downloading (NFR-05)."""
        large_size = 101 * 1024 * 1024
        node = self._make_node_with_att("a1", filename="huge.zip", size=large_size)
        copier = make_copier(source, target)
        copier._copy_attachments(node, "T-10", CopyResult())
        # structlog writes to stdout by default; capfd captures at the fd level
        captured = capfd.readouterr()
        out = captured.out + captured.err
        assert "huge.zip" in out or "large" in out.lower(), "Expected a large-attachment warning"

    def test_failed_attachment_recorded_in_errors_not_raised(
        self, source: MockContentClient, target: MockContentClient
    ) -> None:
        node = self._make_node_with_att("a1")

        def boom(*args: Any, **kw: Any) -> bytes:
            raise RuntimeError("network timeout")

        source._http.get_attachment_content = boom  # type: ignore[method-assign]
        result = CopyResult()
        count = make_copier(source, target)._copy_attachments(node, "T-10", result)
        assert count == 0
        assert len(result.errors) == 1
        assert "a1" in result.errors[0] or "network timeout" in result.errors[0]


# ---------------------------------------------------------------------------
# _copy_labels
# ---------------------------------------------------------------------------


class TestCopyLabels:
    def test_copies_all_labels_to_target(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode("10", "Root", "", (), (), ("api", "backend"))
        count = make_copier(source, target)._copy_labels(node, "T-10", CopyResult())
        assert count == 2
        assert ("T-10", "api") in target.set_labels
        assert ("T-10", "backend") in target.set_labels

    def test_returns_count(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode("10", "Root", "", (), (), ("x", "y", "z"))
        count = make_copier(source, target)._copy_labels(node, "T-10", CopyResult())
        assert count == 3

    def test_empty_labels_returns_zero(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode("10", "Root", "", (), (), ())
        count = make_copier(source, target)._copy_labels(node, "T-10", CopyResult())
        assert count == 0
        assert target.set_labels == []

    def test_failed_label_recorded_not_raised(self, source: MockContentClient, target: MockContentClient) -> None:
        node = PageNode("10", "Root", "", (), (), ("ok", "bad"))

        call_count = 0

        def boom_on_second(page_id: str, label: str) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("label API error")
            target.set_labels.append((page_id, label))

        target.set_page_label = boom_on_second  # type: ignore[method-assign]
        result = CopyResult()
        count = make_copier(source, target)._copy_labels(node, "T-10", result)
        assert count == 1
        assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# copy_tree integration
# ---------------------------------------------------------------------------


class TestCopyTree:
    def test_full_pipeline_pages_and_labels(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", title="Root")
        source._children["10"] = [{"id": "11"}]
        source._pages["11"] = make_page_resp("11", title="Child")
        source._labels_by_id["10"] = ["tag1"]
        source._labels_by_id["11"] = ["tag2"]
        # Target serves pages for remap phase
        target._pages["T-ROOT"] = make_page_resp("T-ROOT", body="<p>root</p>")
        target._pages["900"] = make_page_resp("900", body="<p>child</p>")

        result = make_copier(
            source,
            target,
            options=CopyOptions(skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")

        assert result.pages_updated == 1
        assert result.pages_created == 1
        assert result.labels_copied == 2
        assert "10" in result.page_map and "11" in result.page_map
        assert result.errors == []

    def test_dry_run_no_api_writes(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}, {"id": "12"}]
        source._pages["11"] = make_page_resp("11")
        source._pages["12"] = make_page_resp("12")
        make_copier(source, target, options=CopyOptions(dry_run=True)).copy_tree("10", "T-ROOT")
        assert target.created == []
        assert target.updated == []
        assert target.uploaded == []

    def test_dry_run_counts_pages(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}, {"id": "12"}]
        source._pages["11"] = make_page_resp("11")
        source._pages["12"] = make_page_resp("12")
        result = make_copier(source, target, options=CopyOptions(dry_run=True)).copy_tree("10", "T-ROOT")
        # 3 pages total; root is "updated" (counts as created=2, one for each non-root)
        assert result.pages_created == 2
        assert len(result.page_map) == 3

    def test_dry_run_counts_attachments(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._attachments["10"] = [make_att_resp("a1"), make_att_resp("a2")]
        result = make_copier(source, target, options=CopyOptions(dry_run=True)).copy_tree("10", "T-ROOT")
        assert result.attachments_copied == 2

    def test_skip_attachments_does_not_upload(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._attachments["10"] = [make_att_resp("a1")]
        make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")
        assert target.uploaded == []

    def test_skip_labels_does_not_set_labels(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10")
        source._labels_by_id["10"] = ["api"]
        make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")
        assert target.set_labels == []

    def test_partial_failure_continues_siblings(self, source: MockContentClient, target: MockContentClient) -> None:
        """A failing child doesn't abort its sibling."""
        source._pages["10"] = make_page_resp("10")
        source._children["10"] = [{"id": "11"}, {"id": "12"}]
        source._pages["11"] = make_page_resp("11", title="BadPage")
        source._pages["12"] = make_page_resp("12", title="GoodPage")

        def create_fails_on_bad(
            *, space_key: str, title: str, body: str, parent_id: str | None = None, **kw: Any
        ) -> dict[str, Any]:
            if title == "BadPage":
                raise Exception("duplicate title on target")
            new_id = str(target._id_counter)
            target._id_counter += 1
            target.created.append(
                {"id": new_id, "title": title, "parent_id": parent_id, "body": body, "space_key": space_key}
            )
            return {"id": new_id, "title": title}

        target.create_page = create_fails_on_bad  # type: ignore[method-assign]
        result = make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")

        good_titles = [c["title"] for c in target.created]
        assert "GoodPage" in good_titles
        assert "11" not in result.page_map
        assert len(result.errors) >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_tree_single_root(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", title="Solo Root")
        result = make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")
        assert result.pages_updated == 1
        assert result.pages_created == 0
        assert result.page_map == {"10": "T-ROOT"}
        assert result.errors == []

    def test_duplicate_title_skips_page_and_subtree(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", title="Root")
        source._children["10"] = [{"id": "11"}]
        source._pages["11"] = make_page_resp("11", title="Duplicate")
        source._children["11"] = [{"id": "12"}]
        source._pages["12"] = make_page_resp("12", title="Child of Dup")

        def raises_on_dup(*, title: str, **kw: Any) -> dict[str, Any]:
            if title == "Duplicate":
                raise Exception("title already exists on target")
            new_id = str(target._id_counter)
            target._id_counter += 1
            target.created.append({"id": new_id, "title": title, **kw})
            return {"id": new_id, "title": title}

        target.create_page = raises_on_dup  # type: ignore[method-assign]
        result = make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")

        assert "11" not in result.page_map
        assert "12" not in result.page_map  # subtree of failed page also absent
        assert len(result.errors) >= 1

    def test_unicode_title_passed_through_unchanged(self, source: MockContentClient, target: MockContentClient) -> None:
        unicode_title = "Xử lý 处理 テスト"
        source._pages["10"] = make_page_resp("10", title="Root")
        source._children["10"] = [{"id": "11"}]
        source._pages["11"] = make_page_resp("11", title=unicode_title)
        make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")
        created_titles = [c["title"] for c in target.created]
        assert unicode_title in created_titles

    def test_empty_body_copied_without_error(self, source: MockContentClient, target: MockContentClient) -> None:
        source._pages["10"] = make_page_resp("10", body="")
        result = make_copier(
            source,
            target,
            options=CopyOptions(skip_attachments=True, skip_labels=True, skip_link_remap=True),
        ).copy_tree("10", "T-ROOT")
        assert result.errors == []
        assert target.updated[0]["body"] == ""

    def test_source_space_auto_detect_attribute(self, source: MockContentClient, target: MockContentClient) -> None:
        """TreeCopier stores source_space_key so _remap_links can use it."""
        copier = make_copier(source, target, source_space="DETECTED")
        assert copier._source_space_key == "DETECTED"
