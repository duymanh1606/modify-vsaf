"""OpenTelemetry-based observability for VDS Agent Core.

Provides distributed tracing with optional OpenTelemetry integration:
- Agent loop span tracking
- Tool call spans
- LLM call spans with token accounting
- Semantic convention attributes (gen_ai.agent.node.type)

The tracer is a no-op when OpenTelemetry is not installed.
Traces are opt-in only and activate when hooks return non-empty context.

Phase 3 wiring (TSK-P3-Theta)
-----------------------------
``AgentTracer.__post_init__`` auto-registers a :class:`JsonlUsageExporter`
observer whenever the env var ``VDS_LLM_USAGE_JSONL_ENABLED`` is unset or
truthy. This closes the LLMUsageCollector ``[unavailable]`` gap by ensuring
every LLM call traced through ``record_llm_call`` is persisted to
``~/.vds/cache/llm-usage/<UTC-date>.jsonl``.

For explicit / programmatic bootstrap (e.g. process startup hook), call
:func:`bootstrap_observability` once with an explicit ``base_dir`` override.
"""

from collections.abc import Callable
from pathlib import Path

from vds_agent_core.observability.decorators import trace_audit, trace_llm_call, trace_span
from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter
from vds_agent_core.observability.tracer import (
    ENV_JSONL_ENABLED,
    AgentTracer,
    BudgetEvent,
    BudgetEventType,
    TokenUsage,
    TraceSpanType,
)


def bootstrap_observability(
    tracer: AgentTracer,
    *,
    base_dir: Path | str | None = None,
) -> Callable[[], None]:
    """Explicitly wire a :class:`JsonlUsageExporter` onto ``tracer``.

    This is the **Option C** entry point — a single, documented hook that
    process bootstrap code can call to opt-in regardless of the env-var
    default. Returns the unregister callable so callers can tear down
    cleanly (e.g. tests, embedded use).

    Parameters
    ----------
    tracer:
        The :class:`AgentTracer` to receive the exporter.
    base_dir:
        Optional override for the JSONL output directory. ``None`` honors
        the ``VDS_LLM_USAGE_DIR`` env var or falls back to
        ``~/.vds/cache/llm-usage``.
    """

    exporter = JsonlUsageExporter(base_dir=base_dir)
    return tracer.register_usage_observer(exporter)


__all__ = [
    "ENV_JSONL_ENABLED",
    "AgentTracer",
    "BudgetEvent",
    "BudgetEventType",
    "JsonlUsageExporter",
    "TokenUsage",
    "TraceSpanType",
    "bootstrap_observability",
    "trace_audit",
    "trace_llm_call",
    "trace_span",
]
