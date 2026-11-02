#!/usr/bin/env python3
"""
Move audit artifact pages under an 'Audit History' child page.

Target: Department page 88716694 (Payment department)
Pages to move:
  - "Project Analysis - 88718879"
  - "Project Analysis - 88718884"
  - "Project Analysis - 88718886"
  - "Project Analysis - 88718943"
  - "Project Analysis - 88718977"
  - "Project Audit - 88718879"
  - "Project Audit - 88718884"
  - "Project Audit - 88718886"
  - "Project Audit - 88718943"
  - "Project Audit - 88718977"

Usage:
    ./scripts/worktree_uv.sh run --project audit_orchestrator python3 scripts/move_audit_artifact_pages.py

Prerequisites:
  - ~/.vds/.env must be populated with VDS_USERNAME, VDS_PASSWORD
  - CONFLUENCE_INTERNAL_URL must be accessible (requires VPN/internal network)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap environment
# ---------------------------------------------------------------------------
env_path = Path("/Users/vds-ai/.vds/.env")
if env_path.exists():
    from dotenv import load_dotenv

    load_dotenv(env_path)

from vds_audit_orchestrator.clients.confluence_cli_client import ConfluenceCliClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEPARTMENT_PAGE_ID = "88716694"
AUDIT_HISTORY_TITLE = "Audit History"

# Pages to move: (title, page_id_in_title) - the IDs embedded in the titles
ARTIFACT_PAGE_IDS = [
    "88718879",
    "88718884",
    "88718886",
    "88718943",
    "88718977",
]

ARTIFACT_PAGE_TITLES = [f"Project Analysis - {pid}" for pid in ARTIFACT_PAGE_IDS] + [
    f"Project Audit - {pid}" for pid in ARTIFACT_PAGE_IDS
]


async def connectivity_check(client: ConfluenceCliClient) -> bool:
    """Verify Confluence is reachable by fetching the department page."""
    try:
        page = await asyncio.wait_for(
            client.get_page(DEPARTMENT_PAGE_ID, expand="version,space"),
            timeout=15,
        )
        if page and page.get("title"):
            print(f"[OK] Connected to Confluence. Department page: {page['title']!r}")
            return True
        print(f"[WARN] Page {DEPARTMENT_PAGE_ID} not found or no permission.")
        return False
    except TimeoutError:
        print("[ERROR] Confluence connection timed out. Check VPN/network access.")
        return False
    except Exception as exc:
        print(f"[ERROR] Confluence connectivity check failed: {exc}")
        return False


async def find_or_create_audit_history_page(
    client: ConfluenceCliClient,
    space_key: str,
) -> str:
    """Return the page ID of 'Audit History' under the department page, creating it if absent."""
    children = await client.get_child_pages(DEPARTMENT_PAGE_ID)
    for child in children:
        if child.get("title") == AUDIT_HISTORY_TITLE:
            page_id = child["id"]
            print(f"[OK] Found existing 'Audit History' page: {page_id}")
            return page_id

    print(f"[INFO] 'Audit History' page not found under {DEPARTMENT_PAGE_ID}. Creating...")
    body_file = Path("/tmp/audit_history_body.html")
    body_file.write_text(
        "<p>This page archives historical audit artifacts for the Payment department.</p>",
        encoding="utf-8",
    )
    result = await client.create_page(
        space_key=space_key,
        title=AUDIT_HISTORY_TITLE,
        body_file=body_file,
        parent_id=DEPARTMENT_PAGE_ID,
    )
    new_id = result.get("id") or result.get("page_id")
    if not new_id:
        raise RuntimeError(f"Failed to create 'Audit History' page. Response: {result}")
    print(f"[OK] Created 'Audit History' page: {new_id}")
    return str(new_id)


async def get_pages_to_move(client: ConfluenceCliClient) -> list[dict]:
    """Get the current children of the department page that match the artifact pattern."""
    children = await client.get_child_pages(DEPARTMENT_PAGE_ID)
    pages_to_move = []
    for child in children:
        title = child.get("title", "")
        if title in ARTIFACT_PAGE_TITLES:
            pages_to_move.append(child)
            print(f"  Found artifact page: {title!r} (id={child['id']})")
    return pages_to_move


async def move_pages(
    client: ConfluenceCliClient,
    pages: list[dict],
    audit_history_page_id: str,
    _space_key: str,
) -> dict[str, list[str]]:
    """Move all artifact pages under the Audit History page."""
    results: dict[str, list[str]] = {"moved": [], "failed": []}

    for page in pages:
        page_id = page["id"]
        title = page.get("title", page_id)
        try:
            # Use PUT to update ancestors (move page)
            # The move_page method uses content.move_page which moves by title
            # We need to reparent using update_page's ancestor field
            # Use the REST API approach: update with new ancestors
            await reparent_page(client, page_id, audit_history_page_id, title)
            print(f"  [OK] Moved: {title!r} -> Audit History")
            results["moved"].append(title)
        except Exception as exc:
            print(f"  [FAIL] Could not move {title!r}: {exc}")
            results["failed"].append(f"{title}: {exc}")

    return results


async def reparent_page(
    client: ConfluenceCliClient,
    page_id: str,
    new_parent_id: str,
    title: str,
) -> None:
    """Move a page to a new parent by calling atlassian update_page with parent_id."""
    # Get current page body (required to not wipe content on update)
    page = await client.get_page(page_id, expand="version,body.storage,space")
    if not page:
        raise ValueError(f"Page {page_id} not found")

    body_content = page.get("body", {}).get("storage", {}).get("value", "")

    # Use the atlassian-python-api client directly — it supports parent_id
    # client._http._client is the atlassian.Confluence instance
    result = await asyncio.to_thread(
        client._http._client.update_page,
        page_id,
        title,
        body_content,
        parent_id=new_parent_id,
        representation="storage",
        always_update=True,
        version_comment="Moved to Audit History archive",
    )
    if not result:
        raise RuntimeError(f"update_page returned falsy result for page {page_id}")


async def main() -> int:
    print("=" * 60)
    print("Audit Artifact Page Migration")
    print(f"Department page: {DEPARTMENT_PAGE_ID}")
    print(f"Target: '{AUDIT_HISTORY_TITLE}' child page")
    print("=" * 60)

    client = ConfluenceCliClient(timeout=30)

    # Step 1: Connectivity check
    print("\n[1/4] Checking Confluence connectivity...")
    if not await connectivity_check(client):
        print("\nABORTED: Cannot reach Confluence. Ensure you have VPN/network access.")
        return 1

    # Step 2: Get space key for creating the Audit History page
    dept_page = await client.get_page(DEPARTMENT_PAGE_ID, expand="space")
    space_key = dept_page.get("space", {}).get("key", "") if dept_page else ""
    if not space_key:
        print("[ERROR] Could not determine space key from department page.")
        return 1
    print(f"[OK] Space key: {space_key}")

    # Step 3: Find pages to move
    print("\n[2/4] Scanning children of department page for artifact pages...")
    pages_to_move = await get_pages_to_move(client)
    if not pages_to_move:
        print("[INFO] No artifact pages found. Already moved or not present.")
        return 0
    print(f"Found {len(pages_to_move)} pages to move.")

    # Step 4: Ensure Audit History page exists
    print("\n[3/4] Ensuring 'Audit History' page exists...")
    audit_history_id = await find_or_create_audit_history_page(client, space_key)

    # Step 5: Move pages
    print(f"\n[4/4] Moving {len(pages_to_move)} pages to Audit History ({audit_history_id})...")
    results = await move_pages(client, pages_to_move, audit_history_id, space_key)

    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print(f"  Moved:  {len(results['moved'])}")
    print(f"  Failed: {len(results['failed'])}")
    if results["moved"]:
        print("\nSuccessfully moved:")
        for t in results["moved"]:
            print(f"  - {t}")
    if results["failed"]:
        print("\nFailed:")
        for t in results["failed"]:
            print(f"  - {t}")
    print("=" * 60)

    # Verify final state
    print("\n[Verify] Remaining children of department page...")
    remaining = await client.get_child_pages(DEPARTMENT_PAGE_ID)
    artifact_remaining = [c for c in remaining if c.get("title", "") in ARTIFACT_PAGE_TITLES]
    if artifact_remaining:
        print(f"[WARN] {len(artifact_remaining)} artifact pages still under department page:")
        for c in artifact_remaining:
            print(f"  - {c.get('title')} (id={c['id']})")
    else:
        print("[OK] No artifact pages remain directly under the department page.")

    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
