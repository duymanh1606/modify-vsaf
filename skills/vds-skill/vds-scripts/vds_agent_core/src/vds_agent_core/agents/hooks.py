"""Injectable behavior hooks for BoundedAgentLoop.

The Protocol defines audit-specific branching points that the generic loop
delegates to.  ``NoOpHooks`` provides neutral defaults so the loop works
standalone without any orchestrator coupling.

Concrete implementations (e.g. ``AuditLoopHooks``) live in each orchestrator
package and restore the original branching logic.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LoopBehaviorHooks(Protocol):
    """Injectable hooks for orchestrator-specific loop behavior.

    Default implementation (NoOpHooks) does nothing — generic loop behavior.
    Audit provides AuditLoopHooks with the original branching logic.
    """

    def should_skip_first_step(self, tool: str, context: dict[str, Any]) -> bool:
        """Return True if the first step's tool output should be wired into context specially."""
        ...

    def is_evidence_recording(self, tool: str) -> bool:
        """Return True if this tool records evidence refs (e.g. RECORD_EVIDENCE_REFS)."""
        ...

    def is_context_query(self, tool: str) -> bool:
        """Return True if this tool is a context-fetching query (e.g. GET_ROW_CONTEXT)."""
        ...

    def has_read_activity(self, trace: list[Any]) -> bool:
        """Return True if the trace contains concrete read activity (doc/code reads)."""
        ...

    def count_doc_reads(self, trace: list[Any]) -> int:
        """Count documentation-related tool steps in the trace."""
        ...

    def is_doc_search(self, tool: str) -> bool:
        """Return True if the tool performs documentation search."""
        ...

    def lookup_evidence_requirements(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return evidence threshold requirements for the current context.

        Returns a dict with at minimum ``min_evidence_refs`` and
        ``min_search_patterns`` keys, plus a ``is_default`` flag indicating
        whether the returned requirements are the generic defaults (True)
        or orchestrator-specific overrides (False).
        """
        ...

    def get_trace_context(self) -> dict[str, Any]:
        """Return trace context for OpenTelemetry propagation.

        Returns an empty dict when tracing is disabled.
        Override to return context attributes for active tracing.
        """
        return {}

    def get_trace_span_name(self, step: int, tool: str) -> str:
        """Return the span name for a given loop step.

        Args:
            step: Step number
            tool: Tool name being executed

        Default implementation returns "step-N/tool" format.
        """
        return f"step-{step}/{tool}"

    def get_service_name(self) -> str:
        """Return the service name for the tracer resource.

        Default implementation returns "vds-agent-core".
        """
        return "vds-agent-core"


# --- NoOpHooks implementation -----------------------------------------


class NoOpHooks:
    """Default no-op implementation — all hooks return neutral values."""

    def should_skip_first_step(self, tool: str, context: dict[str, Any]) -> bool:
        return False

    def is_evidence_recording(self, tool: str) -> bool:
        return False

    def is_context_query(self, tool: str) -> bool:
        return False

    def has_read_activity(self, trace: list[Any]) -> bool:
        return False

    def count_doc_reads(self, trace: list[Any]) -> int:
        return 0

    def is_doc_search(self, tool: str) -> bool:
        return False

    def lookup_evidence_requirements(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"min_evidence_refs": 1, "min_search_patterns": 1, "is_default": True}

    def get_trace_context(self) -> dict[str, Any]:
        return {}

    def get_trace_span_name(self, step: int, tool: str) -> str:
        return f"step-{step}/{tool}"

    def get_service_name(self) -> str:
        return "vds-agent-core"
