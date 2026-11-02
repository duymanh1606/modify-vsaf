#!/usr/bin/env python3
"""
Move 14 wrong-department pages from Payment dept (88716694) to their correct
department parent pages. Also renames pages with '- 88716694' suffix and
archives a duplicate.

Usage:
    ./scripts/worktree_uv.sh run --project audit_orchestrator python3 scripts/move_wrong_dept_pages.py
"""

from __future__ import annotations

import asyncio
import sys

# ---------------------------------------------------------------------------
# Move plan: (page_id, target_parent_id)
# ---------------------------------------------------------------------------
PAGES_TO_MOVE = [
    # Admin Products (88716677)
    ("93487312", "88716677"),  # Project Analysis - 88718856
    ("93487308", "88716677"),  # Project Audit - 88718856
    ("93487326", "88716677"),  # Project Analysis - 88718889
    ("93487285", "88716677"),  # Project Audit - 88718884 - 88716694
    ("93487290", "88716677"),  # Project Audit - 88718886 - 88716694
    ("93487294", "88716677"),  # Project Audit - 88718879 - 88716694
    ("93487299", "88716677"),  # Project Audit - 88718877 - 88716694
    # App Platform (88716679)
    ("93487303", "88716679"),  # Project Audit - 88718882 - 88716694
    # Finance (88716692)
    ("93487316", "88716692"),  # Project Analysis - 88718866
    ("93487321", "88716692"),  # Project Analysis - 88718868
    ("93487314", "88716692"),  # Project Audit - 88718866
    ("93487319", "88716692"),  # Project Audit - 88718868
    # Core Tech (88718815)
    ("93487328", "88718815"),  # Project Analysis - 88718983
    ("93127125", "88718815"),  # Project Audit - 88718940 - 88716694
]

# ---------------------------------------------------------------------------
# Rename plan: (page_id, new_title)
# ---------------------------------------------------------------------------
PAGES_TO_RENAME = [
    ("93126787", "Project Audit - 88718943"),
    ("93127090", "Project Audit - 88718975"),
    ("93126805", "Project Audit - 88718977"),
    ("93126810", "Project Audit - 88719105"),
    ("93487279", "Project Audit - 91335346"),
]

# ---------------------------------------------------------------------------
# Archive duplicate: (page_id, new_title, target_parent_id)
# ---------------------------------------------------------------------------


def build_archive_title(base_title: str, source_page_id: str) -> str:
    """Build a deterministic archive title for moved Confluence pages.

    Format:
        [ARCHIVED] {base_title} - {source_page_id}

    This keeps the original title readable while making repeated archive
    operations collision-safe under a shared archive parent.
    """

    return f"[ARCHIVED] {base_title} - {source_page_id}"


ARCHIVE_PAGE = (
    "93487283",
    build_archive_title("Project Analysis - 91335346", "93487283"),
    "88727274",
)

SLEEP_BETWEEN_OPS = 5  # seconds


async def main() -> int:
    from vds_audit_orchestrator.clients.confluence_cli_client import ConfluenceCliClient

    print("=" * 70)
    print("Wrong-Department Page Migration & Cleanup")
    print("=" * 70)

    client = ConfluenceCliClient()

    # 1. Connectivity check — use get_page on a known page instead of probe_reachable
    # (probe_reachable calls get_all_groups which times out on this server)
    print("\n[Step 1] Checking Confluence connectivity via get_page(88716694)...")
    test_page = await client.get_page("88716694", expand="version,space")
    if not test_page or not test_page.get("title"):
        print("  [FAIL] Could not fetch Payment dept page 88716694.")
        print("  Check VPN/LAN and credentials in ~/.vds/.env")
        return 1
    space_key = test_page.get("space", {}).get("key", "")
    print(f"  [OK] Reachable — page: {test_page['title']!r} (space: {space_key})")

    # 2. Resolve target parent titles (needed by move_page which takes a title)
    print("\n[Step 2] Resolving target parent page titles...")
    unique_parent_ids = list({parent_id for _, parent_id in PAGES_TO_MOVE} | {ARCHIVE_PAGE[2]})
    parent_titles: dict[str, str] = {}

    for pid in unique_parent_ids:
        page = await client.get_page(pid, expand="version")
        if page and page.get("title"):
            parent_titles[pid] = page["title"]
            print(f"  [OK] {pid} -> {page['title']!r}")
        else:
            print(f"  [FAIL] Could not fetch parent page {pid}")
            return 1

    # 3. Move pages
    print(f"\n[Step 3] Moving {len(PAGES_TO_MOVE)} pages to correct departments...")
    move_success = 0
    move_fail = 0

    for page_id, target_parent_id in PAGES_TO_MOVE:
        target_title = parent_titles[target_parent_id]

        # Get current page info for logging
        page_info = await client.get_page(page_id, expand="version")
        current_title = page_info.get("title", page_id) if page_info else page_id

        print(f"\n  Moving: {current_title!r}")
        print(f"    page_id={page_id}  -> parent={target_parent_id} ({target_title!r})")

        try:
            result = await client.move_page(page_id, target_title, position="append")
            # move_page returns {} on success (empty body from Confluence REST)
            print(f"    [OK] Moved successfully (result={result!r})")
            move_success += 1
        except Exception as exc:
            print(f"    [FAIL] Exception: {exc}")
            # Retry once after 30s
            print("    Waiting 30s and retrying once...")
            await asyncio.sleep(30)
            try:
                result = await client.move_page(page_id, target_title, position="append")
                print(f"    [OK] Moved on retry (result={result!r})")
                move_success += 1
            except Exception as exc2:
                print(f"    [FAIL] Retry also failed: {exc2}")
                move_fail += 1
                continue

        await asyncio.sleep(SLEEP_BETWEEN_OPS)

    # 4. Rename pages (remove '- 88716694' suffix)
    print(f"\n[Step 4] Renaming {len(PAGES_TO_RENAME)} pages (remove '- 88716694' suffix)...")
    rename_success = 0
    rename_fail = 0

    for page_id, new_title in PAGES_TO_RENAME:
        page_info = await client.get_page(page_id, expand="version")
        current_title = page_info.get("title", page_id) if page_info else page_id

        print(f"\n  Renaming: {current_title!r}")
        print(f"    page_id={page_id}  -> new title: {new_title!r}")

        try:
            result = await client.rename_page(page_id, new_title)
            print(f"    [OK] Renamed successfully (result keys={list(result.keys()) if result else result!r})")
            rename_success += 1
        except Exception as exc:
            print(f"    [FAIL] Exception: {exc}")
            print("    Waiting 30s and retrying once...")
            await asyncio.sleep(30)
            try:
                result = await client.rename_page(page_id, new_title)
                print("    [OK] Renamed on retry")
                rename_success += 1
            except Exception as exc2:
                print(f"    [FAIL] Retry also failed: {exc2}")
                rename_fail += 1
                continue

        await asyncio.sleep(SLEEP_BETWEEN_OPS)

    # 5. Archive duplicate
    print(f"\n[Step 5] Archiving duplicate page {ARCHIVE_PAGE[0]}...")
    archive_id, archive_new_title, archive_parent_id = ARCHIVE_PAGE
    archive_parent_title = parent_titles[archive_parent_id]

    page_info = await client.get_page(archive_id, expand="version")
    current_title = page_info.get("title", archive_id) if page_info else archive_id
    print(f"  Current title: {current_title!r}")
    print(f"  New title: {archive_new_title!r}")
    print(f"  Target parent: {archive_parent_id} ({archive_parent_title!r})")

    archive_success = True

    # Step 5a: Rename first
    try:
        result = await client.rename_page(archive_id, archive_new_title)
        print("  [OK] Renamed archive page")
    except Exception as exc:
        print(f"  [FAIL] Could not rename archive page: {exc}")
        archive_success = False

    if archive_success:
        await asyncio.sleep(SLEEP_BETWEEN_OPS)
        # Step 5b: Move to archive parent
        try:
            result = await client.move_page(archive_id, archive_parent_title, position="append")
            print(f"  [OK] Moved archive page to {archive_parent_title!r}")
        except Exception as exc:
            print(f"  [FAIL] Could not move archive page: {exc}")
            print("  Waiting 30s and retrying once...")
            await asyncio.sleep(30)
            try:
                result = await client.move_page(archive_id, archive_parent_title, position="append")
                print("  [OK] Moved archive page on retry")
            except Exception as exc2:
                print(f"  [FAIL] Retry also failed: {exc2}")
                archive_success = False

    # 6. Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Moves:   {move_success} succeeded, {move_fail} failed (of {len(PAGES_TO_MOVE)})")
    print(f"  Renames: {rename_success} succeeded, {rename_fail} failed (of {len(PAGES_TO_RENAME)})")
    print(f"  Archive: {'OK' if archive_success else 'FAILED'}")

    total_failures = move_fail + rename_fail + (0 if archive_success else 1)
    if total_failures > 0:
        print(f"\n[WARN] {total_failures} operation(s) failed. Review output above.")
    else:
        print("\n[OK] All operations completed successfully.")

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
