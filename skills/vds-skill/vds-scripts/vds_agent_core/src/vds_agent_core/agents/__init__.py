"""Agent primitives — tool registry contract, bounded loop, behavior hooks."""

from vds_agent_core.agents.hooks import LoopBehaviorHooks, NoOpHooks
from vds_agent_core.agents.loop import (
    AgentLoopAction,
    AgentLoopConfig,
    AgentLoopResult,
    AgentLoopStep,
    BoundedAgentLoop,
    LoopTerminationReason,
)
from vds_agent_core.agents.tools import ToolName, ToolRegistry, ToolResponseEnvelope

__all__ = [
    "AgentLoopAction",
    "AgentLoopConfig",
    "AgentLoopResult",
    "AgentLoopStep",
    "BoundedAgentLoop",
    "LoopBehaviorHooks",
    "LoopTerminationReason",
    "NoOpHooks",
    "ToolName",
    "ToolRegistry",
    "ToolResponseEnvelope",
]
