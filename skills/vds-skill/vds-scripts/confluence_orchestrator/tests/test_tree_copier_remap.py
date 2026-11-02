"""Unit tests for TreeCopier link-remapping phase (FR-01.5 / TSK-D.5).

Tests cover all four pattern classes:
  Pattern 1 — ri:content-id attribute (only for IDs present in page_map)
  Pattern 2 — ri:space-key attribute (unconditional space substitution)
  Pattern 3 — relative /display/<source-space>/ URL paths
  Pattern 4 — absolute <source-base-url>/display/<source-space>/ URLs

Edge cases:
  - ID not in page_map → unchanged
  - Body with no matching links → update_page not called
  - Mixed patterns in single body → all replaced in one pass
"""

from __future__ import annotations

from typing import Any

from confluence_orchestrator.tree_copier import (
    CopyOptions,
    CopyResult,
    TreeCopier,
)

SOURCE_SPACE = "IIST"
TARGET_SPACE = "TTPMCOREPM"
SOURCE_BASE = "http://10.254.136.35:8090"
TARGET_BASE = "http://confluence.digital.vn"


# ---------------------------------------------------------------------------
# Mock infrastructure (minimal — remap only needs get_page + update_page)
# ---------------------------------------------------------------------------


class RemapHttp:
    """Minimal HTTP stub for remap tests — only needs base_url."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url


class RemapClient:
    """ContentClient stub scoped to remap test needs."""

    def __init__(self, base_url: str) -> None:
        self._http = RemapHttp(base_url)
        self.base_url = base_url
        # Configurable: page_id → body string
        self._bodies: dict[str, str] = {}
        self.updated: list[dict[str, Any]] = []
        self.get_page_calls: list[str] = []

    def get_page(self, page_id: str, *, expand: list[str] | None = None) -> dict[str, Any]:
        self.get_page_calls.append(page_id)
        body = self._bodies.get(page_id, "")
        return {"id": page_id, "body": {"storage": {"value": body}}}

    def update_page(self, page_id: str, **kwargs: Any) -> dict[str, Any]:
        self.updated.append({"page_id": page_id, **kwargs})
        return {"id": page_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_remap_copier(
    source_client: RemapClient,
    target_client: RemapClient,
    *,
    source_space: str = SOURCE_SPACE,
    target_space: str = TARGET_SPACE,
) -> TreeCopier:
    return TreeCopier(
        source_client,  # type: ignore[arg-type]
        target_client,  # type: ignore[arg-type]
        target_space,
        source_space,
        CopyOptions(skip_attachments=True, skip_labels=True),
    )


def remap_single(body: str, page_map: dict[str, str]) -> str:
    """Run _remap_links on a single page body and return the remapped body."""
    src = RemapClient(SOURCE_BASE)
    tgt = RemapClient(TARGET_BASE)
    tgt._bodies["T1"] = body
    copier = make_remap_copier(src, tgt)
    result = CopyResult(page_map=dict(page_map))
    copier._remap_links(result, {})
    if tgt.updated:
        return tgt.updated[0]["body"]
    return body  # unchanged — no update_page call made


# ---------------------------------------------------------------------------
# Pattern 1: ri:content-id
# ---------------------------------------------------------------------------


class TestPattern1ContentId:
    def test_remaps_id_present_in_page_map(self) -> None:
        body = '<ac:structured-macro><ri:content-id="111"/></ac:structured-macro>'
        result = remap_single(body, {"SRC-A": "T1", "111": "999"})
        assert 'ri:content-id="999"' in result
        assert 'ri:content-id="111"' not in result

    def test_leaves_numeric_id_unchanged_when_not_in_page_map(self) -> None:
        """A matching numeric ID that isn't in page_map must not be remapped."""
        body = '<ri:content-id="9999"/>'
        result = remap_single(body, {"SRC-A": "T1"})  # "9999" not in map
        assert 'ri:content-id="9999"' in result

    def test_only_remaps_ids_in_page_map_not_all_ids(self) -> None:
        body = '<p><ri:content-id="10"/> and <ri:content-id="20"/></p>'
        result = remap_single(body, {"SRC-A": "T1", "10": "100"})
        # "10" is in map → remapped; "20" is not → unchanged
        assert 'ri:content-id="100"' in result
        assert 'ri:content-id="20"' in result
        assert 'ri:content-id="10"' not in result

    def test_multiple_occurrences_all_remapped(self) -> None:
        body = '<ri:content-id="55"/> <ri:content-id="55"/>'
        result = remap_single(body, {"SRC": "T1", "55": "77"})
        assert result.count('ri:content-id="77"') == 2

    def test_remap_increments_links_remapped_counter(self) -> None:
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        tgt._bodies["T1"] = '<ri:content-id="10"/> <ri:content-id="10"/>'
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"SRC": "T1", "10": "20"})
        copier._remap_links(result, {})
        assert result.links_remapped == 2


# ---------------------------------------------------------------------------
# Pattern 2: ri:space-key
# ---------------------------------------------------------------------------


class TestPattern2SpaceKey:
    def test_replaces_source_space_key_attribute(self) -> None:
        body = f'<ri:space ri:space-key="{SOURCE_SPACE}"/>'
        result = remap_single(body, {"SRC": "T1"})
        assert f'ri:space-key="{TARGET_SPACE}"' in result
        assert f'ri:space-key="{SOURCE_SPACE}"' not in result

    def test_multiple_space_key_occurrences_all_replaced(self) -> None:
        body = f'<ri:space-key="{SOURCE_SPACE}"/> <ri:space-key="{SOURCE_SPACE}"/> <ri:space-key="OTHER"/>'
        result = remap_single(body, {"SRC": "T1"})
        assert result.count(f'ri:space-key="{TARGET_SPACE}"') == 2
        assert 'ri:space-key="OTHER"' in result  # different space not touched

    def test_applies_unconditionally_even_to_external_pages(self) -> None:
        """Patterns 2-4 apply to ALL occurrences of source space, not just page_map IDs."""
        body = f'<ri:space-key="{SOURCE_SPACE}"/> no page-id link here'
        result = remap_single(body, {"SRC": "T1"})  # page_map has no content-id
        assert f'ri:space-key="{TARGET_SPACE}"' in result


# ---------------------------------------------------------------------------
# Pattern 3: relative /display/ URL
# ---------------------------------------------------------------------------


class TestPattern3RelativeDisplayUrl:
    def test_replaces_relative_display_path(self) -> None:
        body = f'<a href="/display/{SOURCE_SPACE}/PageTitle">link</a>'
        result = remap_single(body, {"SRC": "T1"})
        assert f"/display/{TARGET_SPACE}/" in result
        assert f"/display/{SOURCE_SPACE}/" not in result

    def test_leaves_other_spaces_relative_paths_unchanged(self) -> None:
        body = '<a href="/display/OTHERSPACE/Page">other</a>'
        result = remap_single(body, {"SRC": "T1"})
        assert "/display/OTHERSPACE/" in result

    def test_multiple_relative_links_all_replaced(self) -> None:
        body = f'<a href="/display/{SOURCE_SPACE}/P1">p1</a><a href="/display/{SOURCE_SPACE}/P2">p2</a>'
        result = remap_single(body, {"SRC": "T1"})
        assert result.count(f"/display/{TARGET_SPACE}/") == 2


# ---------------------------------------------------------------------------
# Pattern 4: absolute source base URL
# ---------------------------------------------------------------------------


class TestPattern4AbsoluteUrl:
    def test_replaces_absolute_source_url(self) -> None:
        body = f'<a href="{SOURCE_BASE}/display/{SOURCE_SPACE}/Page">link</a>'
        result = remap_single(body, {"SRC": "T1"})
        assert f"{TARGET_BASE}/display/{TARGET_SPACE}/" in result
        assert SOURCE_BASE not in result

    def test_partial_url_not_affected(self) -> None:
        """Only the combination of base + space is replaced, not base URL alone."""
        # This URL has the base but not the /display/SPACE/ path — pattern 4 won't match
        body = f'<img src="{SOURCE_BASE}/download/attachments/123/img.png"/>'
        result = remap_single(body, {"SRC": "T1"})
        # The attachment download URL shouldn't be modified by pattern 4
        assert f"{SOURCE_BASE}/download/" in result

    def test_multiple_absolute_links_all_replaced(self) -> None:
        body = (
            f'<a href="{SOURCE_BASE}/display/{SOURCE_SPACE}/A">a</a>'
            f'<a href="{SOURCE_BASE}/display/{SOURCE_SPACE}/B">b</a>'
        )
        result = remap_single(body, {"SRC": "T1"})
        assert result.count(f"{TARGET_BASE}/display/{TARGET_SPACE}/") == 2


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestRemapEdgeCases:
    def test_body_with_no_links_no_update_page_called(self) -> None:
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        tgt._bodies["T1"] = "<p>plain text, no links at all</p>"
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"SRC": "T1"})
        copier._remap_links(result, {})
        assert tgt.updated == []
        assert result.links_remapped == 0

    def test_empty_body_no_update_page_called(self) -> None:
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        tgt._bodies["T1"] = ""
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"SRC": "T1"})
        copier._remap_links(result, {})
        assert tgt.updated == []

    def test_mixed_patterns_all_replaced_in_single_pass(self) -> None:
        """A realistic body with all 4 patterns should be fully remapped."""
        body = (
            f'<ri:content-id="10"/> '
            f'<ri:space-key="{SOURCE_SPACE}"/> '
            f'<a href="/display/{SOURCE_SPACE}/Page">rel</a> '
            f'<a href="{SOURCE_BASE}/display/{SOURCE_SPACE}/Page">abs</a>'
        )
        result = remap_single(body, {"SRC": "T1", "10": "20"})
        assert 'ri:content-id="20"' in result
        assert f'ri:space-key="{TARGET_SPACE}"' in result
        assert f"/display/{TARGET_SPACE}/" in result
        assert f"{TARGET_BASE}/display/{TARGET_SPACE}/" in result
        # Source artifacts gone
        assert 'ri:content-id="10"' not in result
        assert f'ri:space-key="{SOURCE_SPACE}"' not in result
        assert f"/display/{SOURCE_SPACE}/" not in result
        assert f"{SOURCE_BASE}/display/" not in result

    def test_dry_run_placeholders_skipped(self) -> None:
        """Dry-run entries have empty target_id — _remap_links must skip them."""
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"SRC-A": "", "SRC-B": ""})  # dry-run placeholders
        copier._remap_links(result, {})
        assert tgt.get_page_calls == []
        assert tgt.updated == []

    def test_links_remapped_total_count_across_all_pages(self) -> None:
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        tgt._bodies["T1"] = f'<ri:space-key="{SOURCE_SPACE}"/>'
        tgt._bodies["T2"] = f'<ri:space-key="{SOURCE_SPACE}"/> <ri:space-key="{SOURCE_SPACE}"/>'
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"S1": "T1", "S2": "T2"})
        copier._remap_links(result, {})
        assert result.links_remapped == 3  # 1 in T1 + 2 in T2

    def test_update_page_called_with_body_kwarg(self) -> None:
        src = RemapClient(SOURCE_BASE)
        tgt = RemapClient(TARGET_BASE)
        tgt._bodies["T1"] = f'<ri:space-key="{SOURCE_SPACE}"/>'
        copier = make_remap_copier(src, tgt)
        result = CopyResult(page_map={"S1": "T1"})
        copier._remap_links(result, {})
        assert tgt.updated[0]["page_id"] == "T1"
        assert "body" in tgt.updated[0]
        assert f'ri:space-key="{TARGET_SPACE}"' in tgt.updated[0]["body"]
