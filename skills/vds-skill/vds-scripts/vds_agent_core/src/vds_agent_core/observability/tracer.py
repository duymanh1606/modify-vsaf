"""AgentTracer — OpenTelemetry spans for agent execution.

Traces agent loops, tool calls, and LLM calls using OpenTelemetry
semantic conventions.  Falls back to no-op when OpenTelemetry is unavailable.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = structlog.get_logger(__name__)

_UTC = UTC

#: Env var that opts the JSONL usage exporter in or out at AgentTracer
#: construction time. Default is **on** (truthy when unset) so production
#: agents emit JSONL records the moment they make an LLM call. Tests use
#: the conftest fixture to flip the default to off, ensuring no test ever
#: writes to ``~/.vds/cache/llm-usage/`` by accident.
ENV_JSONL_ENABLED = "VDS_LLM_USAGE_JSONL_ENABLED"

#: Truthy values for ``ENV_JSONL_ENABLED``. Anything else (including
#: empty string) disables auto-registration. Mirrors the convention used
#: by other VDS feature flags (`VDS_SCHEDULER_ENABLED` etc.).
_TRUTHY = {"1", "true", "yes", "on"}


def _jsonl_auto_register_enabled() -> bool:
    """Return True iff JSONL auto-registration should fire on this tracer.

    Default-on: an unset env var means production wants the exporter wired.
    Tests pin the env var to "false" via conftest so they never leak writes
    to the real cache directory.
    """
    raw = os.environ.get(ENV_JSONL_ENABLED)
    if raw is None:
        return True
    return raw.strip().lower() in _TRUTHY


def _iso8601_utc(ts: datetime) -> str:
    """Format a datetime as ISO-8601 with explicit ``Z`` suffix (UTC)."""
    ts = ts.replace(tzinfo=_UTC) if ts.tzinfo is None else ts.astimezone(_UTC)
    # Drop microseconds for consistency with the JSONL record shape, then
    # render with the canonical ``Z`` suffix instead of ``+00:00``.
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class BudgetEventType(StrEnum):
    """Budget event type taxonomy."""

    PROMPT_TOKEN_SPENT = "prompt_token_spent"
    COMPLETION_TOKEN_SPENT = "completion_token_spent"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_OK = "budget_ok"


class TraceSpanType(StrEnum):
    """Semantic convention span types for agent observability."""

    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    VECTOR_SEARCH = "vector_search"
    LOOP_ITERATION = "loop_iteration"


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token usage record for LLM calls (immutable NamedTuple-like)."""

    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None = None


@dataclass(frozen=True, slots=True)
class BudgetEvent:
    """Budget event record (immutable NamedTuple-like)."""

    event_type: BudgetEventType
    prompt_tokens: int = 0
    completion_tokens: int = 0
    budget_limit: int | None = None
    session_id: str | None = None
    timestamp: datetime | None = None


@dataclass
class AgentTracer:
    """OpenTelemetry-based agent tracer.

    Provides span context managers for agent execution phases.
    Is a no-op when OpenTelemetry is not installed.
    """

    service_name: str = field(default="vds-agent-core")
    enabled: bool = field(default=True)
    _tracer: Any = field(default=None, init=False, repr=False)
    _tracing_enabled: bool = field(default=False, init=False, repr=False)
    _service_name: str = field(default="vds-agent-core", init=False, repr=False)
    _get_span_context: Callable[[], dict[str, Any] | None] | None = field(default=None, init=False, repr=False)
    # TSK-P3-0.2 (ecosystem-daily-report Phase 3 Wave 0): minimal observer hook
    # so out-of-process exporters (e.g. JsonlUsageExporter) can subscribe to
    # LLM-call records without coupling tracer.py to a specific exporter.
    _usage_observers: list[Callable[[dict[str, Any]], None]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        # Bug C1 (Wave 8 audit): the constructor parameter `service_name` was
        # being silently dropped because `_try_initialize()` reads
        # `self._service_name` (init=False, hardcoded default). Propagate the
        # caller-supplied value before initializing OTel, so
        # `AgentTracer(service_name="my-svc")` actually registers "my-svc".
        self._service_name = self.service_name
        if not self.enabled:
            self._tracing_enabled = False
            self._tracer = None
        else:
            self._try_initialize()
        # Phase 3 wiring (TSK-P3-Theta): auto-register the JSONL usage exporter
        # so every LLM call goes to ``~/.vds/cache/llm-usage/<UTC-date>.jsonl``
        # without callers having to remember the bootstrap step. Runs even when
        # OTel is disabled because ``record_llm_call`` is independent of the
        # OTel span path. The env-var gate keeps tests from polluting the real
        # cache directory.
        self._maybe_register_jsonl_exporter()

    def _maybe_register_jsonl_exporter(self) -> None:
        """Auto-register a JsonlUsageExporter observer when the flag is on.

        Failures are logged at debug level and swallowed — observability must
        never block agent execution. Importing the exporter lazily keeps the
        `tracer` module free of circular imports during package init.
        """
        if not _jsonl_auto_register_enabled():
            return
        try:
            from vds_agent_core.observability.jsonl_exporter import JsonlUsageExporter

            exporter = JsonlUsageExporter()
            self.register_usage_observer(exporter)
            logger.debug(
                "JsonlUsageExporter auto-registered",
                base_dir=str(exporter.base_dir),
                service=self._service_name,
            )
        except Exception as exc:
            logger.debug(
                "JsonlUsageExporter auto-registration failed",
                error=str(exc),
                service=self._service_name,
            )

    def _try_initialize(self) -> None:
        """Attempt to initialize OpenTelemetry. Silently fails if not installed."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider

            resource = Resource.create({"service.name": self._service_name})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer("vds_agent_core.observability")
            self._tracing_enabled = True

            self._get_span_context = self._otel_get_span_context

            logger.debug("AgentTracer initialized with OpenTelemetry")
        except ImportError:
            logger.debug("OpenTelemetry not installed, tracing disabled")
            self._tracing_enabled = False
            self._tracer = None

    def _otel_get_span_context(self) -> dict[str, Any] | None:
        """Extract current span context for propagation."""
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            if span is None:
                return None
            sc = span.get_span_context()
            if sc is None or not sc.is_valid:
                return None
            return {
                "trace_id": format(sc.trace_id, "032x"),
                "span_id": format(sc.span_id, "016x"),
                "trace_flags": format(sc.trace_flags, "02x"),
            }
        except Exception:
            return None

    @property
    def is_enabled(self) -> bool:
        """Return True if tracing is active."""
        return self._tracing_enabled

    def get_trace_context(self) -> dict[str, Any] | None:
        """Return current trace context for propagation to child spans.

        Returns None when tracing is disabled or no active span exists.
        """
        if not self._tracing_enabled or self._get_span_context is None:
            return None
        return self._get_span_context()

    @contextmanager
    def open_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span | None]:
        """Public context manager to open a span on this tracer.

        Yields the span, or None when tracing is disabled. Attributes
        (if provided) are set on the span at creation time.

        This is the public, non-private alternative to reaching into
        ``tracer._tracer.start_as_current_span(...)``. External call sites
        (e.g. ``vds_audit_orchestrator.logging_config.audit_otel_span``)
        should call ``open_span`` instead of accessing ``_tracer`` directly.
        """
        if not self._tracing_enabled or self._tracer is None:
            yield None
            return
        try:
            with self._tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                yield span
        except Exception as e:
            logger.warning("Failed to open span", name=name, error=str(e))
            yield None

    @contextmanager
    def trace_loop(
        self,
        loop_id: str,
        config: dict[str, Any] | None = None,
    ) -> Generator[Span | None]:
        """Context manager for the entire agent loop span.

        Args:
            loop_id: Unique identifier for this loop execution
            config: Optional loop configuration attributes

        Yields:
            The active span or None if tracing is disabled
        """
        if not self._tracing_enabled or self._tracer is None:
            yield None
            return

        attributes: dict[str, Any] = {
            "gen_ai.agent.node.type": "agent_loop",
            "agent.loop_id": loop_id,
        }
        if config:
            if max_steps := config.get("max_steps"):
                attributes["agent.loop.max_steps"] = max_steps
            if timeout := config.get("timeout_seconds"):
                attributes["agent.loop.timeout_seconds"] = timeout
            if budget := config.get("budget_units"):
                attributes["agent.loop.budget_units"] = budget

        try:
            with self._tracer.start_as_current_span("agent.loop", attributes=attributes) as span:
                yield span
        except Exception as e:
            logger.warning("Failed to create loop span", error=str(e))
            yield None

    @contextmanager
    def trace_tool_call(
        self,
        tool_name: str,
        payload: dict[str, Any] | None = None,
    ) -> Generator[Span | None]:
        """Context manager for a single tool call span.

        Args:
            tool_name: Name of the tool being invoked
            payload: Optional tool payload for attributes

        Yields:
            The active span or None if tracing is disabled
        """
        if not self._tracing_enabled or self._tracer is None:
            yield None
            return

        attributes: dict[str, Any] = {
            "gen_ai.agent.node.type": "tool_call",
            "tool.name": tool_name,
        }
        if payload:
            payload_size = len(str(payload))
            attributes["tool.payload_size_bytes"] = payload_size
            if "query" in payload:
                attributes["tool.query_preview"] = str(payload["query"])[:200]
            if "path" in payload:
                attributes["tool.path"] = payload["path"]

        try:
            with self._tracer.start_as_current_span(f"tool.{tool_name}", attributes=attributes) as span:
                yield span
        except Exception as e:
            logger.warning("Failed to create tool call span", tool=tool_name, error=str(e))
            yield None

    @contextmanager
    def trace_llm_call(
        self,
        model: str,
        messages: list[dict[str, Any]] | None = None,
    ) -> Generator[Span | None]:
        """Context manager for an LLM API call span.

        Args:
            model: Model identifier (e.g., "claude-3-5-sonnet")
            messages: Optional message list for attribute extraction

        Yields:
            The active span or None if tracing is disabled
        """
        if not self._tracing_enabled or self._tracer is None:
            yield None
            return

        attributes: dict[str, Any] = {
            "gen_ai.agent.node.type": "llm_call",
            "llm.model": model,
        }
        if messages:
            attributes["llm.message_count"] = len(messages)
            try:
                total_chars = sum(len(str(m.get("content", ""))) for m in messages)
                attributes["llm.input_char_count"] = total_chars
            except Exception:
                pass

        try:
            with self._tracer.start_as_current_span("llm.call", attributes=attributes) as span:
                yield span
        except Exception as e:
            logger.warning("Failed to create LLM call span", model=model, error=str(e))
            yield None

    def record_token_usage(
        self,
        prompt: int,
        completion: int,
        model: str | None = None,
        cost_usd: float | None = None,
    ) -> TokenUsage:
        """Record token usage from an LLM response.

        Args:
            prompt: Number of prompt/input tokens
            completion: Number of completion/output tokens
            model: Optional model identifier (e.g., "claude-3-5-sonnet")
            cost_usd: Optional cost in USD

        Returns:
            TokenUsage record
        """
        total = prompt + completion
        usage = TokenUsage(
            model=model or "unknown",
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            cost_usd=cost_usd,
        )
        logger.debug(
            "Token usage recorded",
            model=model,
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=total,
            cost_usd=cost_usd,
        )
        return usage

    def register_usage_observer(
        self,
        callback: Callable[[dict[str, Any]], None],
    ) -> Callable[[], None]:
        """Register a callback that fires for every LLM-call usage event.

        Each callback receives a JSON-serializable ``dict`` payload with at
        least ``timestamp`` (ISO-8601, UTC), ``model``, ``prompt_tokens``,
        ``completion_tokens``, and ``total_tokens``. Optional keys:
        ``provider``, ``request_id``, ``cost_usd``.

        Callbacks MUST NOT raise — exceptions are caught and logged. This
        keeps the tracer write-path strictly non-blocking. Returns an
        unregister callable so tests can clean up.

        Added for TSK-P3-0.2 (ecosystem-daily-report Phase 3 Wave 0).
        """
        self._usage_observers.append(callback)

        def _unregister() -> None:
            with suppress(ValueError):
                self._usage_observers.remove(callback)

        return _unregister

    def record_llm_call(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        provider: str | None = None,
        request_id: str | None = None,
        cost_usd: float | None = None,
        timestamp: datetime | None = None,
    ) -> TokenUsage:
        """Record a complete LLM-call event and notify usage observers.

        Wraps :meth:`record_token_usage` (preserving existing behavior) and
        additionally emits a structured event payload to every registered
        usage observer. Observers receive a JSON-serializable dict; observer
        exceptions are swallowed so tracer callers are never slowed.
        """
        usage = self.record_token_usage(
            prompt=prompt_tokens,
            completion=completion_tokens,
            model=model,
            cost_usd=cost_usd,
        )
        if not self._usage_observers:
            return usage

        ts = timestamp if timestamp is not None else datetime.now(tz=_UTC)
        event: dict[str, Any] = {
            "timestamp": _iso8601_utc(ts),
            "provider": provider,
            "model": model,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "total_tokens": int(prompt_tokens) + int(completion_tokens),
            "request_id": request_id,
            "cost_usd": cost_usd,
        }
        for cb in list(self._usage_observers):
            try:
                cb(event)
            except Exception as exc:
                logger.warning(
                    "Usage observer raised; dropping event for that observer",
                    error=str(exc),
                    observer=getattr(cb, "__qualname__", repr(cb)),
                )
        return usage

    def record_budget_event(self, event: BudgetEvent) -> None:
        """Record a budget-related event.

        Args:
            event: BudgetEvent describing the event type and state
        """
        logger.debug(
            "Budget event recorded",
            event_type=event.event_type.value,
            prompt_tokens=event.prompt_tokens,
            completion_tokens=event.completion_tokens,
            budget_limit=event.budget_limit,
            session_id=event.session_id,
        )
        if self._tracing_enabled:
            try:
                from opentelemetry import trace

                span = trace.get_current_span()
                if span and span.is_recording():
                    span.set_attribute("agent.budget.event", event.event_type.value)
                    span.set_attribute("agent.budget.prompt_tokens", event.prompt_tokens)
                    span.set_attribute("agent.budget.completion_tokens", event.completion_tokens)
                    if event.budget_limit is not None:
                        span.set_attribute("agent.budget.limit", event.budget_limit)
            except Exception:
                pass
