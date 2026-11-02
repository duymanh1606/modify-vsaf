"""Unit tests for JIRA tools.

Based on pytest v8.3.3+ API
Context7: /pytest-dev/pytest
"""

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from mcp.client.session import ClientSession

pytestmark = pytest.mark.anyio


async def test_jira_search_tool(client_session: ClientSession) -> None:
    """Test jira_search tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "jira_search" in tool_names


async def test_jira_get_issue_tool(client_session: ClientSession) -> None:
    """Test jira_get_issue tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "jira_get_issue" in tool_names


async def test_jira_list_projects_tool(client_session: ClientSession) -> None:
    """Test jira_list_projects tool is available."""
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]
    assert "jira_list_projects" in tool_names
