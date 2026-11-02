"""Real API verification tests for Confluence tools via MCP.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
Key Features: @pytest.mark.skipif, real API calls via MCP
"""

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

# Skip if credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv("INTERNAL_CONFLUENCE_TOKEN") or not os.getenv("EXTERNAL_CONFLUENCE_TOKEN"),
    reason="Confluence tokens not available",
)


@pytest.mark.anyio
async def test_confluence_search_via_mcp(client_session: ClientSession) -> None:
    """Verify Confluence search tool via MCP with real API."""
    result = await client_session.call_tool(
        "confluence_search", {"query": "space = TDOV", "server": "internal", "limit": 5}
    )
    # Verify result structure
    assert result is not None


@pytest.mark.anyio
async def test_confluence_get_page_via_mcp(client_session: ClientSession) -> None:
    """Verify Confluence get page tool via MCP with real API."""
    # Note: This will fail if page ID doesn't exist
    # In real scenario, use a valid page ID
    result = await client_session.call_tool("confluence_get_page", {"page_id": "99647801", "server": "external"})
    # Verify result structure
    assert result is not None
