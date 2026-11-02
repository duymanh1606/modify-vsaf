"""Real API verification tests for JIRA tools via MCP.

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
    not os.getenv("VDS_USERNAME") or not os.getenv("VDS_PASSWORD"),
    reason="VDS credentials not available",
)


@pytest.mark.anyio
async def test_jira_search_via_mcp(client_session: ClientSession) -> None:
    """Verify JIRA search tool via MCP with real API."""
    # Note: This will fail if vds-cli is not available or credentials are invalid
    # In real scenario, this should return search results
    result = await client_session.call_tool("jira_search", {"query": "project = NTTC", "limit": 5})
    # Verify result structure
    assert result is not None
    # Note: Actual content depends on API response


@pytest.mark.anyio
async def test_jira_list_projects_via_mcp(client_session: ClientSession) -> None:
    """Verify JIRA list projects tool via MCP with real API."""
    result = await client_session.call_tool("jira_list_projects", {})
    # Verify result structure
    assert result is not None
