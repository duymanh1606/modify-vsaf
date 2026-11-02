"""Tracing decorators for agent execution phases.

Provides @trace_span and @trace_llm_call decorators that integrate
with AgentTracer for OpenTelemetry span creation.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# Bug W3 (Wave 8 audit): each `@trace_span` / `@trace_llm_call` decoration
# was constructing a new AgentTracer instance whose __post_init__ calls
# `trace.set_tracer_provider()` globally. Applying decorators to N functions
# would clobber the global provider N times. Reuse a single module-level
# instance so OTel provider initialization happens exactly once.
_TRACER: Any = None


def _module_tracer() -> Any:
    """Return the singleton AgentTracer used by all decorators."""
    global _TRACER
    if _TRACER is None:
        from vds_agent_core.observability.tracer import AgentTracer

        _TRACER = AgentTracer()
    return _TRACER


def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Decorator to create a span around a function call.

    The span is only created when AgentTracer tracing is enabled.
    Otherwise the wrapped function executes normally.

    Args:
        name: Span name (e.g., "agent.decision", "search.vector")
        attributes: Optional span attributes

    Returns:
        Decorated function that creates a span when called

    Example:
        @trace_span("agent.decision", {"decision.type": "route_selection"})
        async def make_decision(context):
            ...
    """
    # Bug W3 (Wave 8 audit): each decoration was constructing a new
    # AgentTracer, whose __post_init__ calls trace.set_tracer_provider()
    # globally — clobbering any previously-installed exporter / sampler
    # config. Reuse the module-level singleton so OTel provider is set
    # exactly once per process.
    tracer = _module_tracer()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return func(*args, **kwargs)

            with tracer._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                try:
                    result = func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("error", str(e))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return await func(*args, **kwargs)

            with tracer._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("error", str(e))
                    raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def trace_llm_call(model: str) -> Callable[[F], F]:
    """Decorator to create a span around an LLM API call.

    Extracts token usage from the response if available and records
    it as span attributes.

    Args:
        model: Model identifier (e.g., "claude-3-5-sonnet")

    Returns:
        Decorated function that creates an LLM call span

    Example:
        @trace_llm_call("claude-3-5-sonnet")
        async def call_llm(messages):
            response = await client.messages.create(...)
            return response
    """
    # Bug W3 (Wave 8 audit): reuse module-level singleton — see trace_span.
    tracer = _module_tracer()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return await func(*args, **kwargs)

            attributes = {
                "gen_ai.agent.node.type": "llm_call",
                "llm.model": model,
            }
            with tracer._tracer.start_as_current_span(f"llm.{model}", attributes=attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                        _extract_and_record_usage(span, result)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("llm.error", str(e))
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return func(*args, **kwargs)

            attributes = {
                "gen_ai.agent.node.type": "llm_call",
                "llm.model": model,
            }
            with tracer._tracer.start_as_current_span(f"llm.{model}", attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                        _extract_and_record_usage(span, result)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("llm.error", str(e))
                    raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def _extract_and_record_usage(span: Any, result: Any) -> None:
    """Extract token usage from LLM response and record on span."""
    try:
        usage = None
        usage_attr = getattr(result, "usage", None)
        if usage_attr is not None:
            usage = usage_attr() if callable(usage_attr) else usage_attr
        if usage is not None:
            prompt_tokens = getattr(usage, "input_tokens", 0) or getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "output_tokens", 0) or getattr(usage, "completion_tokens", 0)
            span.set_attribute("llm.prompt_tokens", int(prompt_tokens))
            span.set_attribute("llm.completion_tokens", int(completion_tokens))
            span.set_attribute("llm.total_tokens", int(prompt_tokens) + int(completion_tokens))
    except Exception:
        pass


def trace_audit(audit_type: str) -> Callable[[F], F]:
    """Decorator to create a span around an audit-specific operation.

    Args:
        audit_type: Audit operation identifier (e.g., "evidence.check",
            "report.generate", "context.query")

    Returns:
        Decorated function that creates an audit span when called

    Example:
        @trace_audit("evidence.check")
        async def verify_evidence(row):
            ...
    """
    from vds_agent_core.observability.tracer import AgentTracer

    tracer = AgentTracer()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return func(*args, **kwargs)
            attributes = {"gen_ai.agent.node.type": "audit", "audit.type": audit_type}
            with tracer._tracer.start_as_current_span(f"audit.{audit_type}", attributes=attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("error", str(e))
                    raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not tracer.is_enabled:
                return await func(*args, **kwargs)
            attributes = {"gen_ai.agent.node.type": "audit", "audit.type": audit_type}
            with tracer._tracer.start_as_current_span(f"audit.{audit_type}", attributes=attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_attribute("success", True)
                    return result
                except Exception as e:
                    if span:
                        span.set_attribute("success", False)
                        span.set_attribute("error", str(e))
                    raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator
