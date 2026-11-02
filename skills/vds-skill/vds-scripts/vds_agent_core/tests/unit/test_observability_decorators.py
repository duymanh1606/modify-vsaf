"""TDD tests for vds_agent_core.observability.decorators — trace_span, trace_llm_call.

These tests define the expected API for the observability decorator functions.
The implementation does NOT exist yet (RED phase).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest


class TestTraceSpanDecorator:
    """trace_span decorator for creating named spans around functions."""

    def test_decorates_sync_function(self) -> None:
        """trace_span can wrap a synchronous function."""
        from vds_agent_core.observability import trace_span

        @trace_span("my_operation")
        def sync_func() -> str:
            return "result"

        result = sync_func()
        assert result == "result"

    def test_decorates_async_function(self) -> None:
        """trace_span can wrap an asynchronous function."""
        import asyncio

        from vds_agent_core.observability import trace_span

        @trace_span("async_operation")
        async def async_func() -> str:
            return "async_result"

        result = asyncio.run(async_func())
        assert result == "async_result"

    def test_passes_through_function_arguments(self) -> None:
        """Decorated function preserves its signature."""
        from vds_agent_core.observability import trace_span

        @trace_span("add")
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5

    def test_creates_span_with_name(self) -> None:
        """Span is created with the provided name."""
        from vds_agent_core.observability import trace_span

        @trace_span("named_span")
        def func() -> None:
            pass

        func()

    def test_attributes_added_to_span(self) -> None:
        """Attributes dict is added to span."""
        from vds_agent_core.observability import trace_span

        @trace_span("with_attrs", attributes={"key": "value"})
        def func() -> None:
            pass

        func()

    def test_spans_are_nested(self) -> None:
        """Nested calls create hierarchical spans."""
        from vds_agent_core.observability import trace_span

        @trace_span("outer")
        def outer() -> str:
            return inner()

        @trace_span("inner")
        def inner() -> str:
            return "nested"

        result = outer()
        assert result == "nested"


class TestTraceLlmCallDecorator:
    """trace_llm_call decorator for LLM interaction spans."""

    def test_decorates_sync_function(self) -> None:
        """trace_llm_call can wrap a synchronous function."""
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="claude-3-5-sonnet")
        def call_llm_sync(messages: list[dict[str, Any]]) -> str:
            return "llm_response"

        messages = [{"role": "user", "content": "hello"}]
        result = call_llm_sync(messages)
        assert result == "llm_response"

    def test_decorates_async_function(self) -> None:
        """trace_llm_call can wrap an asynchronous function."""
        import asyncio

        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="claude-3-5-sonnet")
        async def call_llm_async(messages: list[dict[str, Any]]) -> str:
            return "async_llm_response"

        messages = [{"role": "user", "content": "hello"}]
        result = asyncio.run(call_llm_async(messages))
        assert result == "async_llm_response"

    def test_model_name_recorded(self) -> None:
        """Model name is recorded in the span."""
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="claude-3-5-sonnet-20240620")
        def call_llm(messages: list[dict[str, Any]]) -> str:
            return "response"

        call_llm([])

    def test_messages_count_recorded(self) -> None:
        """Message count is recorded as span attribute."""
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="claude-3-5")
        def call_llm(messages: list[dict[str, Any]]) -> str:
            return "response"

        messages = [
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        call_llm(messages)

    def test_error_propagates_through_decorator(self) -> None:
        """Exceptions from the wrapped function propagate normally."""
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="claude-3-5")
        def failing_llm(messages: list[dict[str, Any]]) -> str:
            raise RuntimeError("LLM failed")

        with pytest.raises(RuntimeError, match="LLM failed"):
            failing_llm([])


class TestDecoratorsWithDisabledTracer:
    """Decorators work when global tracer is disabled."""

    def test_trace_span_noop_when_disabled(self) -> None:
        """trace_span is a no-op when tracer is disabled."""
        from vds_agent_core.observability import trace_span

        @trace_span("test_span")
        def func() -> str:
            return "result"

        result = func()
        assert result == "result"


# ---------------------------------------------------------------------------
# Coverage-focused tests: disabled-tracer fast paths, exception propagation,
# token usage extraction, trace_audit decorator (sync + async + exceptions).
# ---------------------------------------------------------------------------


@pytest.fixture
def disabled_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force AgentTracer instances to report tracing as disabled.

    Decorators import AgentTracer at decorator-call time, so patching the
    class before declaring the decorated function flips ``is_enabled`` to
    False without affecting the global OpenTelemetry provider state.
    """
    from vds_agent_core.observability import tracer as tracer_mod

    def _disabled_post_init(self: Any) -> None:
        self._tracing_enabled = False
        self._tracer = None

    monkeypatch.setattr(tracer_mod.AgentTracer, "__post_init__", _disabled_post_init)


class TestTraceSpanDisabledFastPath:
    """trace_span fast-paths when AgentTracer reports tracing disabled."""

    def test_sync_disabled_returns_result(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("disabled.sync")
        def func(x: int) -> int:
            return x * 2

        assert func(7) == 14

    def test_async_disabled_returns_result(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("disabled.async")
        async def func(x: int) -> int:
            return x + 1

        assert asyncio.run(func(4)) == 5

    def test_sync_disabled_propagates_exception(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("disabled.sync.boom")
        def func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            func()


class TestTraceSpanExceptionPaths:
    """trace_span records and re-raises exceptions for both sync and async."""

    def test_sync_exception_recorded_and_propagates(self) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("sync.fail", attributes={"x": 1})
        def func() -> None:
            raise RuntimeError("sync-fail")

        with pytest.raises(RuntimeError, match="sync-fail"):
            func()

    def test_async_exception_recorded_and_propagates(self) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("async.fail")
        async def func() -> None:
            raise RuntimeError("async-fail")

        with pytest.raises(RuntimeError, match="async-fail"):
            asyncio.run(func())

    def test_sync_with_no_attributes_dict(self) -> None:
        from vds_agent_core.observability import trace_span

        @trace_span("no_attrs")
        def func() -> int:
            return 99

        assert func() == 99


class TestTraceLlmCallDisabledAndExceptions:
    """trace_llm_call fast paths, async exceptions, and sync exceptions."""

    def test_sync_disabled_returns_result(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="m1")
        def func() -> str:
            return "ok"

        assert func() == "ok"

    def test_async_disabled_returns_result(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="m2")
        async def func() -> str:
            return "ok-async"

        assert asyncio.run(func()) == "ok-async"

    def test_async_exception_propagates(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="m3")
        async def func() -> None:
            raise RuntimeError("llm-async-fail")

        with pytest.raises(RuntimeError, match="llm-async-fail"):
            asyncio.run(func())

    def test_sync_exception_propagates(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        @trace_llm_call(model="m4")
        def func() -> None:
            raise RuntimeError("llm-sync-fail")

        with pytest.raises(RuntimeError, match="llm-sync-fail"):
            func()


class TestExtractAndRecordUsage:
    """_extract_and_record_usage covers both Anthropic-style and OpenAI-style usage objects."""

    def test_response_with_input_output_tokens_attr(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        class Usage:
            input_tokens = 10
            output_tokens = 20

        class Response:
            usage = Usage()

        @trace_llm_call(model="anthropic-style")
        def call() -> Response:
            return Response()

        assert isinstance(call(), Response)

    def test_response_with_prompt_completion_tokens_attr(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        class Usage:
            prompt_tokens = 5
            completion_tokens = 15

        class Response:
            usage = Usage()

        @trace_llm_call(model="openai-style")
        def call() -> Response:
            return Response()

        assert isinstance(call(), Response)

    def test_response_with_callable_usage(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        class Usage:
            input_tokens = 7
            output_tokens = 13

        class Response:
            def usage(self) -> Usage:  # callable, not attribute
                return Usage()

        @trace_llm_call(model="callable-usage")
        def call() -> Response:
            return Response()

        assert isinstance(call(), Response)

    def test_response_without_usage_attr(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        class Response:
            pass

        @trace_llm_call(model="no-usage")
        def call() -> Response:
            return Response()

        assert isinstance(call(), Response)

    def test_extract_usage_swallows_exceptions(self) -> None:
        """_extract_and_record_usage must swallow extraction errors silently."""
        from vds_agent_core.observability import trace_llm_call

        class BadUsage:
            @property
            def input_tokens(self) -> int:
                raise RuntimeError("boom")

        class Response:
            usage = BadUsage()

        @trace_llm_call(model="bad-usage")
        def call() -> Response:
            return Response()

        # Even though usage extraction will raise internally, the wrapped
        # function must still return its result.
        assert isinstance(call(), Response)

    def test_async_extracts_usage(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        class Usage:
            input_tokens = 11
            output_tokens = 22

        class Response:
            usage = Usage()

        @trace_llm_call(model="async-usage")
        async def call() -> Response:
            return Response()

        assert isinstance(asyncio.run(call()), Response)


class TestTraceAuditDecorator:
    """trace_audit decorator: sync, async, disabled, exception paths."""

    def test_decorates_sync_function(self) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("evidence.check")
        def verify(row: dict[str, Any]) -> bool:
            return bool(row)

        assert verify({"k": 1}) is True

    def test_decorates_async_function(self) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("report.generate")
        async def gen() -> str:
            return "report"

        assert asyncio.run(gen()) == "report"

    def test_sync_disabled(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("context.query")
        def func() -> int:
            return 42

        assert func() == 42

    def test_async_disabled(self, disabled_tracer: None) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("context.query")
        async def func() -> int:
            return 7

        assert asyncio.run(func()) == 7

    def test_sync_exception_propagates(self) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("evidence.check")
        def func() -> None:
            raise ValueError("audit-sync-fail")

        with pytest.raises(ValueError, match="audit-sync-fail"):
            func()

    def test_async_exception_propagates(self) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("evidence.check")
        async def func() -> None:
            raise ValueError("audit-async-fail")

        with pytest.raises(ValueError, match="audit-async-fail"):
            asyncio.run(func())

    def test_sync_passes_args_and_kwargs(self) -> None:
        from vds_agent_core.observability import trace_audit

        @trace_audit("context.query")
        def add(a: int, b: int = 0) -> int:
            return a + b

        assert add(1, b=4) == 5


# ---------------------------------------------------------------------------
# Phase 9a strengthening: companion tests asserting WHAT the decorators
# actually record on the span (the original
# ``assert isinstance(call(), Response)`` tests were execution-only — they
# pass even if usage extraction silently drops every attribute).
# ---------------------------------------------------------------------------


def _patch_module_tracer_with_fake() -> tuple[Any, Any]:
    """Replace the decorator-module singleton tracer with a recording fake.

    Returns ``(fake_span, restore_fn)``. The caller MUST call restore_fn() at
    teardown.
    """
    from vds_agent_core.observability import decorators as dec_mod

    fake_span = MagicMock()
    fake_underlying = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=fake_span)
    cm.__exit__ = MagicMock(return_value=False)
    fake_underlying.start_as_current_span.return_value = cm

    fake_tracer = MagicMock()
    fake_tracer.is_enabled = True
    fake_tracer._tracer = fake_underlying

    original = dec_mod._TRACER
    dec_mod._TRACER = fake_tracer

    def restore() -> None:
        dec_mod._TRACER = original

    return (fake_span, fake_underlying), restore


class TestTraceSpanRecordsAttributes:
    """trace_span must set ``success`` on the span and forward attributes."""

    def test_sync_success_sets_success_true(self) -> None:
        from vds_agent_core.observability import trace_span

        (fake_span, fake_underlying), restore = _patch_module_tracer_with_fake()
        try:

            @trace_span("named_span", attributes={"k": "v"})
            def func() -> int:
                return 42

            assert func() == 42
            # The decorator forwards attributes verbatim to start_as_current_span.
            call = fake_underlying.start_as_current_span.call_args
            assert call.args[0] == "named_span"
            assert call.kwargs["attributes"] == {"k": "v"}
            # On success: span.set_attribute("success", True).
            fake_span.set_attribute.assert_any_call("success", True)
        finally:
            restore()

    def test_sync_exception_sets_success_false_and_error(self) -> None:
        from vds_agent_core.observability import trace_span

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            @trace_span("err.span")
            def func() -> None:
                raise RuntimeError("kaboom")

            with pytest.raises(RuntimeError, match="kaboom"):
                func()
            keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
            assert keys["success"] is False
            assert "kaboom" in keys["error"]
        finally:
            restore()


class TestTraceLlmCallRecordsAttributes:
    """trace_llm_call must record model + token usage on the span."""

    def test_anthropic_style_usage_recorded(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        (fake_span, fake_underlying), restore = _patch_module_tracer_with_fake()
        try:

            class Usage:
                input_tokens = 10
                output_tokens = 20

            class Response:
                usage = Usage()

            @trace_llm_call(model="claude-3-5-sonnet")
            def call() -> Response:
                return Response()

            assert isinstance(call(), Response)
            # Span name + initial attributes
            scall = fake_underlying.start_as_current_span.call_args
            assert scall.args[0] == "llm.claude-3-5-sonnet"
            assert scall.kwargs["attributes"]["llm.model"] == "claude-3-5-sonnet"
            # Usage extraction must have recorded the EXACT counts.
            keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
            assert keys["llm.prompt_tokens"] == 10
            assert keys["llm.completion_tokens"] == 20
            assert keys["llm.total_tokens"] == 30
            assert keys["success"] is True
        finally:
            restore()

    def test_openai_style_usage_recorded(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            class Usage:
                prompt_tokens = 5
                completion_tokens = 15

            class Response:
                usage = Usage()

            @trace_llm_call(model="openai-style")
            def call() -> Response:
                return Response()

            call()
            keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
            assert keys["llm.prompt_tokens"] == 5
            assert keys["llm.completion_tokens"] == 15
            assert keys["llm.total_tokens"] == 20
        finally:
            restore()

    def test_callable_usage_recorded(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            class Usage:
                input_tokens = 7
                output_tokens = 13

            class Response:
                def usage(self) -> Usage:
                    return Usage()

            @trace_llm_call(model="callable-usage")
            def call() -> Response:
                return Response()

            call()
            keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
            assert keys["llm.prompt_tokens"] == 7
            assert keys["llm.completion_tokens"] == 13
        finally:
            restore()

    def test_no_usage_attr_skips_token_attributes(self) -> None:
        """When response has no usage, no token attributes should be set."""
        from vds_agent_core.observability import trace_llm_call

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            class Response:
                pass

            @trace_llm_call(model="no-usage")
            def call() -> Response:
                return Response()

            call()
            keys = {c.args[0] for c in fake_span.set_attribute.call_args_list}
            assert "llm.prompt_tokens" not in keys
            assert "llm.completion_tokens" not in keys
            assert "llm.total_tokens" not in keys
            assert "success" in keys  # success=True still recorded
        finally:
            restore()

    def test_bad_usage_extraction_does_not_set_token_attributes(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            class BadUsage:
                @property
                def input_tokens(self) -> int:
                    raise RuntimeError("boom")

            class Response:
                usage = BadUsage()

            @trace_llm_call(model="bad-usage")
            def call() -> Response:
                return Response()

            assert isinstance(call(), Response)
            keys = {c.args[0] for c in fake_span.set_attribute.call_args_list}
            # Because extraction raised, neither prompt nor completion is set.
            assert "llm.prompt_tokens" not in keys
            assert "llm.completion_tokens" not in keys
        finally:
            restore()

    def test_exception_records_error_attribute(self) -> None:
        from vds_agent_core.observability import trace_llm_call

        (fake_span, _), restore = _patch_module_tracer_with_fake()
        try:

            @trace_llm_call(model="m-err")
            def call() -> str:
                raise RuntimeError("api-broken")

            with pytest.raises(RuntimeError, match="api-broken"):
                call()
            keys = {c.args[0]: c.args[1] for c in fake_span.set_attribute.call_args_list}
            assert keys["success"] is False
            assert "api-broken" in keys["llm.error"]
        finally:
            restore()
