"""TDD tests for vds_agent_core.observability.hooks — LoopBehaviorHooks extensions.

These tests define the expected API for observability-related hook methods.
The implementation does NOT exist yet (RED phase).
"""

from __future__ import annotations

from typing import Any


class TestObservabilityHooksProtocol:
    """Extended LoopBehaviorHooks with observability trace methods."""

    def test_get_trace_context_method_exists(self) -> None:
        """LoopBehaviorHooks has get_trace_context method."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks

        # Protocol should include get_trace_context
        assert hasattr(LoopBehaviorHooks, "get_trace_context")

    def test_get_trace_span_name_method_exists(self) -> None:
        """LoopBehaviorHooks has get_trace_span_name method."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks

        assert hasattr(LoopBehaviorHooks, "get_trace_span_name")

    def test_get_service_name_method_exists(self) -> None:
        """LoopBehaviorHooks has get_service_name method."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks

        assert hasattr(LoopBehaviorHooks, "get_service_name")


class TestNoOpHooksTraceMethods:
    """NoOpHooks returns neutral values for trace methods."""

    def test_get_trace_context_returns_empty_dict(self) -> None:
        """get_trace_context returns empty dict by default."""
        from vds_agent_core.agents.hooks import NoOpHooks

        hooks = NoOpHooks()
        ctx = hooks.get_trace_context()
        assert ctx == {}

    def test_get_trace_span_name_returns_default_format(self) -> None:
        """get_trace_span_name returns formatted span name (exact format)."""
        from vds_agent_core.agents.hooks import NoOpHooks

        hooks = NoOpHooks()
        name = hooks.get_trace_span_name(step=1, tool="search_code")
        # Phase 9a strengthening: assert exact format, not just substring presence.
        # The original test passed if EITHER "1" OR "search_code" appeared, which
        # would silently accept malformed outputs like "step1" or "/search_code".
        assert name == "step-1/search_code"

    def test_get_service_name_returns_default(self) -> None:
        """get_service_name returns default service name (exact value)."""
        from vds_agent_core.agents.hooks import NoOpHooks

        hooks = NoOpHooks()
        name = hooks.get_service_name()
        # Phase 9a strengthening: assert the contract value, not just type.
        assert name == "vds-agent-core"


class TestCustomHooksTraceIntegration:
    """Custom hooks can provide real observability context."""

    def test_custom_get_trace_context_returns_non_empty(self) -> None:
        """Custom hooks can return non-empty trace context."""

        class CustomHooks:
            def get_trace_context(self) -> dict[str, Any]:
                return {
                    "trace_id": "abc123",
                    "span_id": "def456",
                    "session_id": "sess-789",
                }

            # Required Protocol methods
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

        hooks = CustomHooks()
        ctx = hooks.get_trace_context()
        assert ctx["trace_id"] == "abc123"
        assert ctx["session_id"] == "sess-789"

    def test_custom_get_trace_span_name_format(self) -> None:
        """Custom hooks can control span naming."""

        class CustomHooks:
            def get_trace_span_name(self, step: int, tool: str) -> str:
                return f"agent.loop.step.{step}.{tool}"

            # Required Protocol methods
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

            def get_service_name(self) -> str:
                return "custom-service"

        hooks = CustomHooks()
        name = hooks.get_trace_span_name(step=5, tool="search_docs")
        assert name == "agent.loop.step.5.search_docs"

    def test_custom_get_service_name(self) -> None:
        """Custom hooks can specify service name for tracing."""

        class CustomHooks:
            def get_service_name(self) -> str:
                return "audit-orchestrator-v2"

            # Required Protocol methods
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
                return f"{step}-{tool}"

        hooks = CustomHooks()
        assert hooks.get_service_name() == "audit-orchestrator-v2"


class TestObservabilityIntegration:
    """Integration tests for observability with agent loop."""

    def test_agent_tracer_uses_hooks_trace_context(self) -> None:
        """AgentTracer can be initialized with hook-provided context."""
        from vds_agent_core.agents.hooks import NoOpHooks
        from vds_agent_core.observability import AgentTracer

        hooks = NoOpHooks()
        hooks.get_trace_context()
        service_name = hooks.get_service_name()

        tracer = AgentTracer(service_name=service_name)

        # When context is empty, tracer should still work
        assert tracer.service_name == service_name

    def test_span_name_uses_hook_format(self) -> None:
        """Span names follow hook-provided format with the step embedded."""
        from vds_agent_core.agents.hooks import NoOpHooks

        hooks = NoOpHooks()

        # Phase 9a strengthening: assert exact per-step values, not just type.
        # The original loop body was effectively a no-op (str is the declared
        # return type), so a regression to an empty string would have passed.
        names = [hooks.get_trace_span_name(step=s, tool="search_code") for s in range(1, 4)]
        assert names == [
            "step-1/search_code",
            "step-2/search_code",
            "step-3/search_code",
        ]
