"""Generic tool registry contract for agent loops.

Each orchestrator defines its own tool enum and registry implementation.
The core package defines only the Protocol contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ToolName is a plain str alias — each orchestrator defines its own enum.
# The ToolRegistry Protocol uses str for tool names so core stays generic.
type ToolName = str


@dataclass(slots=True)
class ToolResponseEnvelope:
    """Generic wrapper for validated tool responses.

    Mirrors the audit_orchestrator ToolResponseEnvelope shape so the
    BoundedAgentLoop can consume responses uniformly.
    """

    tool: str
    payload: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ToolRegistry(Protocol):
    """Minimal generic tool registry contract.

    Concrete implementations live in each orchestrator (e.g.,
    audit_orchestrator/agents/tool_registry.py). This Protocol
    defines the interface that BoundedAgentLoop depends on.
    """

    def get_tool(self, name: str) -> Callable[..., Any]: ...
    def list_tools(self) -> list[str]: ...
    def invoke(self, tool: str, payload: dict[str, Any]) -> ToolResponseEnvelope: ...
