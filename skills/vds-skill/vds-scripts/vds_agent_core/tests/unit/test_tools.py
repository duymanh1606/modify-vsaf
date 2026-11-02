"""Tests for vds_agent_core.agents.tools — ToolRegistry Protocol and ToolName alias."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vds_agent_core.agents.tools import ToolName, ToolRegistry


class _FakeRegistry:
    """Minimal concrete implementation satisfying ToolRegistry structurally."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {"echo": lambda x: x}

    def get_tool(self, name: str) -> Callable[..., Any]:
        return self._tools[name]

    def list_tools(self) -> list[str]:
        return list(self._tools)

    def invoke(self, tool: str, payload: dict[str, Any]) -> Any:
        from vds_agent_core.agents.tools import ToolResponseEnvelope

        fn = self._tools[tool]
        result = fn(**payload)
        return ToolResponseEnvelope(tool=tool, payload={"result": result})


class TestToolRegistry:
    def test_structural_isinstance(self) -> None:
        """A class with matching methods satisfies the runtime_checkable Protocol."""
        registry = _FakeRegistry()
        assert isinstance(registry, ToolRegistry)

    def test_get_tool_returns_callable(self) -> None:
        registry = _FakeRegistry()
        tool = registry.get_tool("echo")
        assert tool("hello") == "hello"

    def test_list_tools_returns_names(self) -> None:
        registry = _FakeRegistry()
        assert registry.list_tools() == ["echo"]


class TestToolName:
    def test_tool_name_is_str(self) -> None:
        """ToolName is a str alias — any str value is valid."""
        name: ToolName = "my_tool"
        assert isinstance(name, str)
