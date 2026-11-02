"""Verify MCP tool registration and discovery.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

pytestmark = pytest.mark.anyio


async def test_all_tools_registered(client_session: ClientSession) -> None:
    """Verify all expected tools are registered."""
    tools = await client_session.list_tools()
    tool_names = {tool.name for tool in tools.tools}

    # Expected tools
    expected_tools = {
        # JIRA tools
        "jira_search",
        "jira_get_issue",
        "jira_list_projects",
        # Confluence tools
        "confluence_search",
        "confluence_get_page",
        # Bitbucket tools
        "bitbucket_list_projects",
        "bitbucket_list_repositories",
        # Git tools
        "git_clone",
        "git_status",
        "git_pull",
    }

    assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"


async def test_tool_schemas_valid(client_session: ClientSession) -> None:
    """Verify tool schemas are valid."""
    tools = await client_session.list_tools()

    for tool in tools.tools:
        assert tool.name, f"Tool missing name: {tool}"
        assert tool.description, f"Tool {tool.name} missing description"
        assert tool.inputSchema, f"Tool {tool.name} missing inputSchema"
