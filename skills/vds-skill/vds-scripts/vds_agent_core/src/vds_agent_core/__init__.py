"""VDS Agent Core — shared LLM, config, skills, and agentic infrastructure."""

from vds_agent_core.observability import (
    AgentTracer,
    BudgetEvent,
    BudgetEventType,
    TokenUsage,
    TraceSpanType,
    trace_audit,
    trace_llm_call,
    trace_span,
)
from vds_agent_core.profiles import DEFAULT_RUNTIME_PROFILES_FILE, CodexCredentialResolver

__version__ = "0.10.0"

__all__ = [
    "DEFAULT_RUNTIME_PROFILES_FILE",
    "AgentTracer",
    "BudgetEvent",
    "BudgetEventType",
    "CodexCredentialResolver",
    "TokenUsage",
    "TraceSpanType",
    "__version__",
    "trace_audit",
    "trace_llm_call",
    "trace_span",
]
