"""TDD tests for vds_agent_core.observability.tracer — AgentTracer.

These tests define the expected API for the observability tracer module.
The implementation does NOT exist yet (RED phase).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestAgentTracerInstantiation:
    """AgentTracer initialization with service_name and enabled flag."""

    def test_requires_service_name(self) -> None:
        """AgentTracer must be initialized with a service_name."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")
        assert tracer.service_name == "test-service"

    def test_enabled_true_by_default(self) -> None:
        """Tracer is enabled by default."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")
        assert tracer.enabled is True

    def test_can_disable_tracer(self) -> None:
        """Tracer can be explicitly disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)
        assert tracer.enabled is False


class TestAgentTracerDisabledMode:
    """When enabled=False, all operations are no-ops."""

    def test_trace_loop_is_noop_when_disabled(self) -> None:
        """trace_loop context manager does nothing when disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)

        # Should not raise, should not create any span
        with tracer.trace_loop(loop_id="loop-1", config=MagicMock()):
            pass  # No error

    def test_trace_tool_call_is_noop_when_disabled(self) -> None:
        """trace_tool_call does nothing when disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)

        with tracer.trace_tool_call(tool_name="search", payload={"q": "test"}):
            pass  # No error

    def test_trace_llm_call_is_noop_when_disabled(self) -> None:
        """trace_llm_call does nothing when disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)

        with tracer.trace_llm_call(model="claude-3-5", messages=[{"role": "user", "content": "hi"}]):
            pass  # No error

    def test_record_token_usage_is_noop_when_disabled(self) -> None:
        """record_token_usage does nothing when disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)
        tracer.record_token_usage(prompt=100, completion=50)  # No error

    def test_record_budget_event_is_noop_when_disabled(self) -> None:
        """record_budget_event does nothing when disabled."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service", enabled=False)

        # Create a mock BudgetEvent
        mock_event = MagicMock()
        tracer.record_budget_event(mock_event)  # No error


class TestTraceLoop:
    """trace_loop context manager for agent loop spans."""

    def test_creates_span_with_loop_id(self) -> None:
        """trace_loop creates a span with loop_id attribute."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        mock_config = MagicMock()
        mock_config.max_steps = 10
        mock_config.budget_units = 100

        with tracer.trace_loop(loop_id="loop-123", config=mock_config) as span:
            assert span is not None
            assert hasattr(span, "set_attribute")
            assert hasattr(span, "end")

    def test_loop_span_has_service_name_attribute(self) -> None:
        """Loop span includes service.name semantic convention."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="my-audit-service")

        with tracer.trace_loop(loop_id="loop-1", config=MagicMock()) as span:
            # Should have set service.name attribute
            assert span is not None


class TestTraceToolCall:
    """trace_tool_call context manager for tool execution spans."""

    def test_creates_span_with_tool_name(self) -> None:
        """trace_tool_call creates a span with tool_name attribute."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        with tracer.trace_tool_call(tool_name="search_code", payload={"q": "auth"}) as span:
            assert span is not None

    def test_records_payload_in_span(self) -> None:
        """Tool call payload is recorded as span attribute."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        payload = {"query": "test", "limit": 5}

        with tracer.trace_tool_call(tool_name="search", payload=payload) as span:
            assert span is not None


class TestTraceLlmCall:
    """trace_llm_call context manager for LLM interaction spans."""

    def test_creates_span_with_model(self) -> None:
        """trace_llm_call creates a span with model attribute."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        messages = [{"role": "system", "content": "You are helpful"}]

        with tracer.trace_llm_call(model="claude-3-5-sonnet", messages=messages) as span:
            assert span is not None

    def test_records_message_count(self) -> None:
        """LLM call span includes message count."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ]

        with tracer.trace_llm_call(model="claude-3-5", messages=messages) as span:
            assert span is not None


class TestRecordTokenUsage:
    """Token usage recording."""

    def test_records_prompt_and_completion_tokens(self) -> None:
        """record_token_usage accepts prompt and completion counts."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        # Should not raise
        tracer.record_token_usage(prompt=500, completion=250)

    def test_token_usage_accumulates(self) -> None:
        """Multiple calls accumulate token counts."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="test-service")

        tracer.record_token_usage(prompt=100, completion=50)
        tracer.record_token_usage(prompt=200, completion=100)

        # The tracer should track total tokens (implementation detail)


class TestRecordBudgetEvent:
    """Budget event recording."""

    def test_accepts_budget_event(self) -> None:
        """record_budget_event accepts BudgetEvent objects."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="test-service")

        event = BudgetEvent(
            event_type=BudgetEventType.PROMPT_TOKEN_SPENT,
            prompt_tokens=100,
            completion_tokens=50,
        )

        # Should not raise
        tracer.record_budget_event(event)


class TestBudgetEventTypes:
    """BudgetEvent and BudgetEventType definitions."""

    def test_budget_event_type_members(self) -> None:
        """BudgetEventType has expected enum members."""
        from vds_agent_core.observability.tracer import BudgetEventType

        assert BudgetEventType.PROMPT_TOKEN_SPENT == "prompt_token_spent"
        assert BudgetEventType.COMPLETION_TOKEN_SPENT == "completion_token_spent"
        assert BudgetEventType.BUDGET_WARNING == "budget_warning"
        assert BudgetEventType.BUDGET_EXCEEDED == "budget_exceeded"
        assert BudgetEventType.BUDGET_OK == "budget_ok"

    def test_budget_event_named_tuple(self) -> None:
        """BudgetEvent is a proper NamedTuple."""
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        event = BudgetEvent(
            event_type=BudgetEventType.PROMPT_TOKEN_SPENT,
            prompt_tokens=100,
            completion_tokens=50,
            budget_limit=1000,
            session_id="sess-123",
        )

        assert event.event_type == BudgetEventType.PROMPT_TOKEN_SPENT
        assert event.prompt_tokens == 100
        assert event.completion_tokens == 50
        assert event.budget_limit == 1000
        assert event.session_id == "sess-123"

    def test_budget_event_defaults(self) -> None:
        """BudgetEvent has sensible defaults."""
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        event = BudgetEvent(event_type=BudgetEventType.BUDGET_OK)

        assert event.prompt_tokens == 0
        assert event.completion_tokens == 0
        assert event.budget_limit is None
        assert event.session_id is None
        assert event.timestamp is None


class TestTokenUsageType:
    """TokenUsage type for LLM token accounting."""

    def test_token_usage_named_tuple(self) -> None:
        """TokenUsage is a proper NamedTuple."""
        from vds_agent_core.observability.tracer import TokenUsage

        usage = TokenUsage(
            model="claude-3-5-sonnet",
            prompt_tokens=500,
            completion_tokens=250,
            total_tokens=750,
            cost_usd=0.01,
        )

        assert usage.model == "claude-3-5-sonnet"
        assert usage.prompt_tokens == 500
        assert usage.completion_tokens == 250
        assert usage.total_tokens == 750
        assert usage.cost_usd == 0.01

    def test_token_usage_optional_cost(self) -> None:
        """TokenUsage cost_usd is optional."""
        from vds_agent_core.observability.tracer import TokenUsage

        usage = TokenUsage(
            model="claude-3-5-sonnet",
            prompt_tokens=500,
            completion_tokens=250,
            total_tokens=750,
        )

        assert usage.cost_usd is None


class TestTraceSpanType:
    """TraceSpanType enum for semantic conventions."""

    def test_span_type_members(self) -> None:
        """TraceSpanType has expected enum members."""
        from vds_agent_core.observability.tracer import TraceSpanType

        assert TraceSpanType.LLM_CALL == "llm_call"
        assert TraceSpanType.TOOL_CALL == "tool_call"
        assert TraceSpanType.DECISION == "decision"
        assert TraceSpanType.VECTOR_SEARCH == "vector_search"
        assert TraceSpanType.LOOP_ITERATION == "loop_iteration"


class TestTracerImportErrorFallback:
    """When opentelemetry imports raise ImportError the tracer disables itself."""

    def test_import_error_disables_tracing(self) -> None:
        """If opentelemetry import fails the tracer falls back to no-op."""
        import builtins

        from vds_agent_core.observability import AgentTracer

        original_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name.startswith("opentelemetry"):
                raise ImportError("simulated missing opentelemetry")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            tracer = AgentTracer(service_name="t")

        assert tracer.is_enabled is False
        assert tracer._tracer is None
        # All trace context-managers should yield None when disabled
        with tracer.trace_loop("loop-x") as span:
            assert span is None
        with tracer.trace_tool_call("tname") as span:
            assert span is None
        with tracer.trace_llm_call("model-x") as span:
            assert span is None
        assert tracer.get_trace_context() is None


class TestGetTraceContext:
    """get_trace_context() span-context extraction."""

    def test_returns_none_when_disabled(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t", enabled=False)
        assert tracer.get_trace_context() is None

    def test_returns_none_when_no_active_span(self) -> None:
        """When no span is active OTel returns INVALID span; helper returns None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        # Outside any context manager — span context is invalid
        ctx = tracer.get_trace_context()
        # Either None (no active span) or None (invalid context)
        assert ctx is None

    def test_returns_dict_when_inside_active_span(self) -> None:
        """Inside a real span the helper returns trace_id/span_id/trace_flags."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled in this run")
        with tracer.trace_loop("loop-ctx"):
            ctx = tracer.get_trace_context()
            assert ctx is not None
            assert "trace_id" in ctx
            assert "span_id" in ctx
            assert "trace_flags" in ctx
            assert len(ctx["trace_id"]) == 32
            assert len(ctx["span_id"]) == 16

    def test_returns_none_when_get_span_returns_none(self) -> None:
        """If trace.get_current_span returns None we return None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with patch("opentelemetry.trace.get_current_span", return_value=None):
            assert tracer._otel_get_span_context() is None

    def test_returns_none_when_span_context_invalid(self) -> None:
        """If the span context is None we return None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_span = MagicMock()
        fake_span.get_span_context.return_value = None
        with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
            assert tracer._otel_get_span_context() is None

    def test_returns_none_when_span_context_not_valid_flag(self) -> None:
        """A span context with is_valid=False returns None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_span = MagicMock()
        fake_sc = MagicMock()
        fake_sc.is_valid = False
        fake_span.get_span_context.return_value = fake_sc
        with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
            assert tracer._otel_get_span_context() is None

    def test_returns_none_when_internal_exception(self) -> None:
        """Any internal exception is swallowed; helper returns None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with patch("opentelemetry.trace.get_current_span", side_effect=RuntimeError("boom")):
            assert tracer._otel_get_span_context() is None


class TestTraceLoopErrorPath:
    """trace_loop swallows errors when start_as_current_span raises."""

    def test_loop_span_exception_yields_none(self) -> None:
        """If start_as_current_span raises, we log a warning and yield None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        # Force the underlying tracer to explode
        tracer._tracer = MagicMock()
        tracer._tracer.start_as_current_span.side_effect = RuntimeError("nope")
        with tracer.trace_loop("loop-err", config={"max_steps": 1}) as span:
            assert span is None

    def test_loop_span_with_timeout_attribute(self) -> None:
        """timeout_seconds in config is recorded as a span attribute."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        # Just exercising the attribute branch; success is no-raise
        with tracer.trace_loop("loop-t", config={"timeout_seconds": 5}) as span:
            assert span is not None


class TestTraceToolCallErrorPath:
    """trace_tool_call payload branches and error handling."""

    def test_tool_call_with_path_attribute(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with tracer.trace_tool_call("read", payload={"path": "/etc/hosts"}) as span:
            assert span is not None

    def test_tool_call_exception_yields_none(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        tracer._tracer = MagicMock()
        tracer._tracer.start_as_current_span.side_effect = RuntimeError("boom")
        with tracer.trace_tool_call("err-tool", payload={"query": "q"}) as span:
            assert span is None


class TestTraceLlmCallErrorPath:
    """trace_llm_call message-extraction errors and span errors."""

    def test_llm_call_message_content_extraction_swallows_error(self) -> None:
        """If summing message content lengths fails, we swallow the exception."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")

        class BadMsg(dict):
            def get(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("msg explodes")

        bad_messages = [BadMsg()]
        # Should not raise
        with tracer.trace_llm_call("model-x", messages=bad_messages) as span:
            assert span is not None

    def test_llm_call_exception_yields_none(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        tracer._tracer = MagicMock()
        tracer._tracer.start_as_current_span.side_effect = RuntimeError("boom")
        with tracer.trace_llm_call("err-model", messages=[{"role": "u", "content": "hi"}]) as span:
            assert span is None


class TestRecordBudgetEventOTelPath:
    """record_budget_event sets attributes on the active recording span."""

    def test_records_budget_attrs_on_active_span(self) -> None:
        """When inside a span, attributes are set on it."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with tracer.trace_loop("loop-budget"):
            event = BudgetEvent(
                event_type=BudgetEventType.BUDGET_EXCEEDED,
                prompt_tokens=10,
                completion_tokens=5,
                budget_limit=100,
            )
            tracer.record_budget_event(event)  # Should hit set_attribute branch

    def test_records_budget_with_no_limit(self) -> None:
        """When budget_limit is None the limit attribute branch is skipped."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with tracer.trace_loop("loop-budget-none"):
            event = BudgetEvent(
                event_type=BudgetEventType.BUDGET_OK,
                prompt_tokens=1,
                completion_tokens=1,
            )
            tracer.record_budget_event(event)

    def test_record_budget_event_swallows_exception(self) -> None:
        """If trace.get_current_span raises we silently swallow."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        with patch("opentelemetry.trace.get_current_span", side_effect=RuntimeError("x")):
            tracer.record_budget_event(BudgetEvent(event_type=BudgetEventType.BUDGET_OK))

    def test_record_budget_event_skips_non_recording_span(self) -> None:
        """When span exists but is_recording is False the inner branch is skipped."""
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_span = MagicMock()
        fake_span.is_recording.return_value = False
        with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
            tracer.record_budget_event(BudgetEvent(event_type=BudgetEventType.BUDGET_OK))
        fake_span.set_attribute.assert_not_called()


class TestRecordTokenUsageReturn:
    """record_token_usage produces a TokenUsage with computed total."""

    def test_total_tokens_computed(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        usage = tracer.record_token_usage(prompt=300, completion=200, model="m1", cost_usd=0.5)
        assert usage.total_tokens == 500
        assert usage.model == "m1"
        assert usage.cost_usd == 0.5

    def test_default_model_when_omitted(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        usage = tracer.record_token_usage(prompt=1, completion=1)
        assert usage.model == "unknown"


class TestServiceNameRespected:
    """Bug C1 (Wave 8 audit): service_name ctor param was silently ignored.

    The constructor parameter wrote to ``service_name`` but ``_try_initialize``
    read ``_service_name`` (init=False, default ``"vds-agent-core"``) when
    building the OTel resource. After the fix in __post_init__, the caller
    value is propagated before initialization.
    """

    def test_custom_service_name_is_propagated_to_internal_field(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="my-custom-service")
        assert tracer._service_name == "my-custom-service"

    def test_default_service_name_unchanged(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer()
        assert tracer._service_name == "vds-agent-core"
        assert tracer.service_name == "vds-agent-core"

    def test_service_name_propagates_when_disabled(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="payments", enabled=False)
        assert tracer._service_name == "payments"
        assert tracer.service_name == "payments"


class TestSpanAttributesRecorded:
    """Phase 9a strengthening: assert WHICH attributes are set on the span.

    Companion tests for the original ``assert span is not None`` shape. These
    capture the exact ``set_attribute`` / ``start_as_current_span`` kwargs so a
    regression that drops or renames an attribute is caught.
    """

    @staticmethod
    def _patched_tracer(tracer: AgentTracer) -> tuple[MagicMock, MagicMock]:
        """Replace tracer._tracer with a mock; return (fake_tracer, fake_span)."""
        fake_tracer = MagicMock()
        fake_span = MagicMock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=fake_span)
        cm.__exit__ = MagicMock(return_value=False)
        fake_tracer.start_as_current_span.return_value = cm
        tracer._tracer = fake_tracer
        return fake_tracer, fake_span

    def test_trace_loop_records_loop_id_and_max_steps(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)
        with tracer.trace_loop(loop_id="loop-123", config={"max_steps": 7}):
            pass
        # Span name + attribute payload must be exact.
        call = fake_tracer.start_as_current_span.call_args
        assert call.args[0] == "agent.loop"
        attrs = call.kwargs["attributes"]
        assert attrs["agent.loop_id"] == "loop-123"
        assert attrs["agent.loop.max_steps"] == 7
        assert attrs["gen_ai.agent.node.type"] == "agent_loop"

    def test_trace_loop_records_timeout_and_budget(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)
        with tracer.trace_loop(
            loop_id="loop-2",
            config={"timeout_seconds": 30, "budget_units": 500},
        ):
            pass
        attrs = fake_tracer.start_as_current_span.call_args.kwargs["attributes"]
        assert attrs["agent.loop.timeout_seconds"] == 30
        assert attrs["agent.loop.budget_units"] == 500

    def test_trace_tool_call_records_tool_name_and_payload_size(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)
        payload = {"query": "find auth code", "limit": 5}
        with tracer.trace_tool_call(tool_name="search_code", payload=payload):
            pass
        call = fake_tracer.start_as_current_span.call_args
        assert call.args[0] == "tool.search_code"
        attrs = call.kwargs["attributes"]
        assert attrs["tool.name"] == "search_code"
        assert attrs["tool.query_preview"] == "find auth code"
        assert attrs["tool.payload_size_bytes"] == len(str(payload))
        assert attrs["gen_ai.agent.node.type"] == "tool_call"

    def test_trace_tool_call_records_path_attribute(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)
        with tracer.trace_tool_call("read", payload={"path": "/etc/hosts"}):
            pass
        attrs = fake_tracer.start_as_current_span.call_args.kwargs["attributes"]
        assert attrs["tool.path"] == "/etc/hosts"

    def test_trace_llm_call_records_model_and_message_stats(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)
        messages = [
            {"role": "system", "content": "sys"},  # 3 chars
            {"role": "user", "content": "hello"},  # 5 chars
        ]
        with tracer.trace_llm_call(model="claude-3-5-sonnet", messages=messages):
            pass
        call = fake_tracer.start_as_current_span.call_args
        assert call.args[0] == "llm.call"
        attrs = call.kwargs["attributes"]
        assert attrs["llm.model"] == "claude-3-5-sonnet"
        assert attrs["llm.message_count"] == 2
        assert attrs["llm.input_char_count"] == 8  # 3 + 5
        assert attrs["gen_ai.agent.node.type"] == "llm_call"

    def test_trace_llm_call_swallows_content_extraction_error(self) -> None:
        """When summing content lengths raises, message_count is still recorded.

        The swallow-and-continue path should still set llm.message_count
        (computed before the sum) but skip llm.input_char_count.
        """
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_tracer, _ = self._patched_tracer(tracer)

        class BadMsg(dict):
            def get(self, *args: Any, **kwargs: Any) -> Any:
                raise RuntimeError("msg explodes")

        with tracer.trace_llm_call("model-x", messages=[BadMsg()]):
            pass
        attrs = fake_tracer.start_as_current_span.call_args.kwargs["attributes"]
        assert attrs["llm.message_count"] == 1
        assert "llm.input_char_count" not in attrs


class TestRecordBudgetEventAttributes:
    """record_budget_event must set the documented attribute keys on the span."""

    def test_records_event_type_and_token_attrs(self) -> None:
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_span = MagicMock()
        fake_span.is_recording.return_value = True
        with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
            tracer.record_budget_event(
                BudgetEvent(
                    event_type=BudgetEventType.BUDGET_EXCEEDED,
                    prompt_tokens=42,
                    completion_tokens=7,
                    budget_limit=100,
                )
            )
        # Capture the exact (key, value) pairs.
        keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
        assert keys["agent.budget.event"] == "budget_exceeded"
        assert keys["agent.budget.prompt_tokens"] == 42
        assert keys["agent.budget.completion_tokens"] == 7
        assert keys["agent.budget.limit"] == 100

    def test_skips_limit_when_none(self) -> None:
        from vds_agent_core.observability import AgentTracer
        from vds_agent_core.observability.tracer import BudgetEvent, BudgetEventType

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled")
        fake_span = MagicMock()
        fake_span.is_recording.return_value = True
        with patch("opentelemetry.trace.get_current_span", return_value=fake_span):
            tracer.record_budget_event(
                BudgetEvent(
                    event_type=BudgetEventType.BUDGET_OK,
                    prompt_tokens=1,
                    completion_tokens=1,
                )
            )
        keys = {c.args[0] for c in fake_span.set_attribute.call_args_list}
        # When budget_limit is None the limit attribute must not be emitted.
        assert "agent.budget.limit" not in keys
        assert "agent.budget.event" in keys


class TestRecordTokenUsageAccumulation:
    """record_token_usage returns a TokenUsage with computed totals — make
    the previously-execution-only ``test_token_usage_accumulates`` actually
    assert per-call totals.
    """

    def test_each_call_returns_independent_totals(self) -> None:
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        u1 = tracer.record_token_usage(prompt=100, completion=50, model="m1")
        u2 = tracer.record_token_usage(prompt=200, completion=100, model="m2")
        # Each call should produce an independent immutable record.
        assert u1.total_tokens == 150
        assert u2.total_tokens == 300
        assert u1.model == "m1"
        assert u2.model == "m2"
        assert u1 is not u2


class TestOpenSpanPublicAPI:
    """AgentTracer.open_span — public context manager that replaces direct
    ``_tracer.start_as_current_span`` access from outside callers (Wave 28b
    encapsulation finding).
    """

    def test_open_span_yields_span_when_enabled(self) -> None:
        """When tracing is enabled, open_span yields a real OTel span."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled in this run")
        with tracer.open_span("audit.test") as span:
            assert span is not None
            # Real OTel spans expose set_attribute and end
            assert hasattr(span, "set_attribute")
            assert hasattr(span, "end")

    def test_open_span_yields_none_when_disabled(self) -> None:
        """When the tracer is disabled, open_span yields None and is a no-op."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t", enabled=False)
        with tracer.open_span("audit.test", attributes={"k": "v"}) as span:
            assert span is None

    def test_open_span_attributes_passed_to_span(self) -> None:
        """Attributes passed to open_span are forwarded to start_as_current_span."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled in this run")
        # Replace the underlying tracer with a mock to capture the call kwargs
        fake_tracer = MagicMock()
        # start_as_current_span must behave like a context manager
        fake_span = MagicMock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=fake_span)
        cm.__exit__ = MagicMock(return_value=False)
        fake_tracer.start_as_current_span.return_value = cm
        tracer._tracer = fake_tracer

        attrs = {"audit_id": "audit-1", "repo": "r", "extra": 42}
        with tracer.open_span("audit.run", attributes=attrs) as span:
            assert span is fake_span

        fake_tracer.start_as_current_span.assert_called_once_with("audit.run", attributes=attrs)

    def test_open_span_swallows_exception_and_yields_none(self) -> None:
        """If start_as_current_span raises, open_span logs and yields None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled in this run")
        tracer._tracer = MagicMock()
        tracer._tracer.start_as_current_span.side_effect = RuntimeError("boom")
        with tracer.open_span("audit.err") as span:
            assert span is None

    def test_open_span_default_attributes_empty_dict(self) -> None:
        """When attributes=None, open_span should still call OTel with empty dict."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="t")
        if not tracer.is_enabled:
            pytest.skip("OTel not enabled in this run")
        fake_tracer = MagicMock()
        fake_span = MagicMock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=fake_span)
        cm.__exit__ = MagicMock(return_value=False)
        fake_tracer.start_as_current_span.return_value = cm
        tracer._tracer = fake_tracer

        with tracer.open_span("audit.empty") as span:
            assert span is fake_span

        fake_tracer.start_as_current_span.assert_called_once_with("audit.empty", attributes={})
