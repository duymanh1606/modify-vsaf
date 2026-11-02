#!/usr/bin/env python3
"""
Move audit artifact pages under an 'Audit History' child page.
Uses ConfluenceCliClient (vds-scripts SDK) — no raw HTTP calls.

Usage:
    ./scripts/worktree_uv.sh run --project audit_orchestrator python3 scripts/move_audit_artifact_pages_rest.py
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPARTMENT_PAGE_ID = "88716694"
AUDIT_HISTORY_TITLE = "Audit History"

ARTIFACT_PAGE_IDS = ["88718879", "88718884", "88718886", "88718943", "88718977"]
ARTIFACT_PAGE_TITLES = set(
    [f"Project Analysis - {pid}" for pid in ARTIFACT_PAGE_IDS] + [f"Project Audit - {pid}" for pid in ARTIFACT_PAGE_IDS]
)


async def main() -> int:
    from vds_audit_orchestrator.clients.confluence_cli_client import ConfluenceCliClient

    print("=" * 60)
    print("Audit Artifact Page Migration (ConfluenceCliClient SDK)")
    print(f"  Department page: {DEPARTMENT_PAGE_ID}")
    print(f"  Target container: '{AUDIT_HISTORY_TITLE}'")
    print("=" * 60)

    client = ConfluenceCliClient()

    # 1. Connectivity check
    print("\n[1/4] Checking Confluence connectivity...")
    reachable, detail = await client.probe_reachable()
    if not reachable:
        print(f"  [FAIL] Confluence not reachable: {detail}")
        print("  Check VPN/credentials in ~/.vds/.env")
        return 1

    dept_page = await client.get_page(DEPARTMENT_PAGE_ID, expand="version,space")
    if not dept_page or not dept_page.get("title"):
        print(f"  [FAIL] Could not fetch department page {DEPARTMENT_PAGE_ID}.")
        return 1

    space_key = dept_page.get("space", {}).get("key", "")
    if not space_key:
        print("[ERROR] Cannot determine space key.")
        return 1
    print(f"  [OK] Department page: {dept_page['title']!r} (space: {space_key})")

    # 2. List current children
    print("\n[2/4] Listing children of department page...")
    children = await client.list_child_pages(DEPARTMENT_PAGE_ID)
    print(f"  Total children found: {len(children)}")

    pages_to_move = [c for c in children if c.get("title", "") in ARTIFACT_PAGE_TITLES]
    audit_history_existing = [c for c in children if c.get("title", "") == AUDIT_HISTORY_TITLE]

    print(f"  Artifact pages to move: {len(pages_to_move)}")
    for p in pages_to_move:
        print(f"    - {p.get('title')!r} (id={p['id']})")

    if not pages_to_move:
        print("  [INFO] No artifact pages found. Already moved or not present.")
        return 0

    # 3. Get or create Audit History page
    print("\n[3/4] Getting/creating 'Audit History' page...")
    if audit_history_existing:
        audit_history_id = audit_history_existing[0]["id"]
        print(f"  [OK] Found existing: id={audit_history_id}")
    else:
        print("  Creating 'Audit History' page...")
        body_html = (
            "<p>This page archives historical audit artifact pages "
            "for the <strong>3.2.4 Nền tảng thanh toán</strong> department.</p>"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as tmp:
            tmp.write(body_html)
            tmp_path = Path(tmp.name)

        try:
            new_page = await client.create_page(
                space_key=space_key,
                title=AUDIT_HISTORY_TITLE,
                body_file=tmp_path,
                parent_id=DEPARTMENT_PAGE_ID,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        if not new_page or not new_page.get("id"):
            print(f"  [ERROR] Failed to create 'Audit History' page. Response: {new_page}")
            return 1
        audit_history_id = str(new_page["id"])
        print(f"  [OK] Created: id={audit_history_id}")

    # 4. Move pages using move_page (by target title)
    print(f"\n[4/4] Moving {len(pages_to_move)} pages to '{AUDIT_HISTORY_TITLE}' ({audit_history_id})...")
    moved: list[str] = []
    failed: list[str] = []

    for page_meta in pages_to_move:
        page_id = page_meta["id"]
        title = page_meta.get("title", page_id)

        result = await client.move_page(
            page_id,
            AUDIT_HISTORY_TITLE,
            position="append",
        )

        if result or result == {}:
            # move_page returns {} on success (no body) or a dict
            print(f"  [OK] Moved: {title!r}")
            moved.append(title)
        else:
            print(f"  [FAIL] Could not move: {title!r}")
            failed.append(f"{title}: move_page returned no result")

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print(f"  Moved:  {len(moved)}")
    print(f"  Failed: {len(failed)}")
    if moved:
        print("\nSuccessfully moved:")
        for t in moved:
            print(f"  - {t}")
    if failed:
        print("\nFailed:")
        for t in failed:
            print(f"  - {t}")
    print("=" * 60)

    # Verify
    print("\n[Verify] Remaining artifact pages under department page...")
    remaining_children = await client.list_child_pages(DEPARTMENT_PAGE_ID)
    still_there = [c for c in remaining_children if c.get("title", "") in ARTIFACT_PAGE_TITLES]
    if still_there:
        print(f"[WARN] {len(still_there)} artifact pages still directly under department:")
        for c in still_there:
            print(f"  - {c.get('title')} (id={c['id']})")
    else:
        print("[OK] No artifact pages remain directly under the department page.")

    print(f"\n[Verify] Children of 'Audit History' page ({audit_history_id})...")
    ah_children = await client.list_child_pages(audit_history_id)
    print(f"  {len(ah_children)} pages now under 'Audit History':")
    for c in ah_children:
        print(f"  - {c.get('title')} (id={c['id']})")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
