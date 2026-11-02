"""Tests for vds_agent_core.agents.loop — BoundedAgentLoop with injectable hooks."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from vds_agent_core.agents.hooks import LoopBehaviorHooks, NoOpHooks
from vds_agent_core.agents.loop import (
    AgentLoopAction,
    AgentLoopConfig,
    AgentLoopStep,
    BoundedAgentLoop,
    LoopTerminationReason,
)
from vds_agent_core.agents.tools import ToolResponseEnvelope

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _StubRegistry:
    """Minimal ToolRegistry implementation for testing."""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self._responses = responses or {}

    def get_tool(self, name: str) -> Any:
        return lambda **kw: self._responses.get(name, {})

    def list_tools(self) -> list[str]:
        return list(self._responses.keys())

    def invoke(self, tool: str, payload: dict[str, Any]) -> ToolResponseEnvelope:
        return ToolResponseEnvelope(tool=tool, payload=dict(self._responses.get(tool, {})))


class _CustomHooks:
    """Custom hooks implementation for testing hook injection."""

    def should_skip_first_step(self, tool: str, context: dict[str, Any]) -> bool:
        return tool == "get_row_context"

    def is_evidence_recording(self, tool: str) -> bool:
        return tool == "record_evidence_refs"

    def is_context_query(self, tool: str) -> bool:
        return tool == "get_row_context"

    def has_read_activity(self, trace: list[Any]) -> bool:
        return any(getattr(s, "tool", "") in {"read_doc_chunk", "read_code_file"} for s in trace)

    def count_doc_reads(self, trace: list[Any]) -> int:
        return sum(1 for s in trace if getattr(s, "tool", "") in {"search_docs", "read_doc_chunk"})

    def is_doc_search(self, tool: str) -> bool:
        return tool == "search_docs"

    def lookup_evidence_requirements(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"min_evidence_refs": 3, "min_search_patterns": 2, "is_default": False}

    def get_trace_context(self) -> dict[str, Any]:
        return {}

    def get_trace_span_name(self, step: int, tool: str) -> str:
        return f"step-{step}/{tool}"

    def get_service_name(self) -> str:
        return "vds-agent-core"


# ---------------------------------------------------------------------------
# NoOpHooks tests
# ---------------------------------------------------------------------------


class TestNoOpHooks:
    """Verify NoOpHooks returns neutral values for all methods."""

    def test_should_skip_first_step_returns_false(self) -> None:
        hooks = NoOpHooks()
        assert hooks.should_skip_first_step("any_tool", {}) is False

    def test_is_evidence_recording_returns_false(self) -> None:
        hooks = NoOpHooks()
        assert hooks.is_evidence_recording("record_evidence_refs") is False

    def test_is_context_query_returns_false(self) -> None:
        hooks = NoOpHooks()
        assert hooks.is_context_query("get_row_context") is False

    def test_has_read_activity_returns_false(self) -> None:
        hooks = NoOpHooks()
        assert hooks.has_read_activity([]) is False

    def test_count_doc_reads_returns_zero(self) -> None:
        hooks = NoOpHooks()
        assert hooks.count_doc_reads([]) == 0

    def test_lookup_evidence_requirements_returns_defaults(self) -> None:
        hooks = NoOpHooks()
        result = hooks.lookup_evidence_requirements({})
        assert result["min_evidence_refs"] == 1
        assert result["min_search_patterns"] == 1
        assert result["is_default"] is True


# ---------------------------------------------------------------------------
# LoopBehaviorHooks Protocol conformance
# ---------------------------------------------------------------------------


class TestLoopBehaviorHooksProtocol:
    """Verify Protocol structural conformance."""

    def test_noophooks_is_instance_of_protocol(self) -> None:
        assert isinstance(NoOpHooks(), LoopBehaviorHooks)

    def test_custom_hooks_is_instance_of_protocol(self) -> None:
        assert isinstance(_CustomHooks(), LoopBehaviorHooks)

    def test_non_conforming_class_is_not_instance(self) -> None:
        class _Incomplete:
            def should_skip_first_step(self, tool: str, context: dict[str, Any]) -> bool:
                return False

        assert not isinstance(_Incomplete(), LoopBehaviorHooks)


# ---------------------------------------------------------------------------
# BoundedAgentLoop instantiation
# ---------------------------------------------------------------------------


class TestBoundedAgentLoopInstantiation:
    """Verify loop construction with default and custom hooks."""

    def test_default_hooks(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        loop = BoundedAgentLoop(registry=registry, config=config)
        assert isinstance(loop._hooks, NoOpHooks)

    def test_custom_hooks(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        custom = _CustomHooks()
        loop = BoundedAgentLoop(registry=registry, config=config, hooks=custom)
        assert loop._hooks is custom

    def test_registry_and_config_stored(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig(max_steps=5, budget_units=10)
        loop = BoundedAgentLoop(registry=registry, config=config)
        assert loop.registry is registry
        assert loop.config is config
        assert loop.config.max_steps == 5
        assert loop.config.budget_units == 10


# ---------------------------------------------------------------------------
# BoundedAgentLoop.run — basic execution
# ---------------------------------------------------------------------------


class TestBoundedAgentLoopRun:
    """Verify loop execution with hooks."""

    def test_zero_timeout_returns_timeout(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig(timeout_seconds=0.0)
        loop = BoundedAgentLoop(registry=registry, config=config)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.TIMEOUT
        assert result.steps_executed == 0

    def test_zero_budget_returns_budget_exhausted(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig(budget_units=0)
        loop = BoundedAgentLoop(registry=registry, config=config)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.BUDGET_EXHAUSTED
        assert result.steps_executed == 0

    def test_no_planner_returns_completed(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        loop = BoundedAgentLoop(registry=registry, config=config, planner=None)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.COMPLETED
        assert result.steps_executed == 0

    def test_single_step_execution(self) -> None:
        registry = _StubRegistry({"search_code": {"results": ["file.py"]}})
        config = AgentLoopConfig(max_steps=5, budget_units=10)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentLoopAction(tool="search_code", payload={"query": "test"})
            return None

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.COMPLETED
        assert result.steps_executed == 1
        assert len(result.trace_steps) == 1
        assert result.trace_steps[0].tool == "search_code"

    def test_tool_error_terminates(self) -> None:
        registry = MagicMock(spec=["get_tool", "list_tools", "invoke"])
        registry.invoke.side_effect = RuntimeError("boom")
        config = AgentLoopConfig(max_steps=5, budget_units=10)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            return AgentLoopAction(tool="search_code", payload={})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.TOOL_ERROR
        assert "RuntimeError: boom" in (result.tool_error or "")

    def test_evidence_recording_with_custom_hooks(self) -> None:
        """Custom hooks.is_evidence_recording triggers evidence extraction."""
        registry = _StubRegistry(
            {
                "record_evidence_refs": {
                    "refs": [{"ref_value": "evidence_1"}, {"ref_value": "evidence_2"}],
                },
            }
        )
        config = AgentLoopConfig(max_steps=5, budget_units=10)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentLoopAction(tool="record_evidence_refs", payload={})
            return None

        loop = BoundedAgentLoop(
            registry=registry,
            config=config,
            planner=planner,
            hooks=_CustomHooks(),
        )
        # evidence_gate_retry_count >= 1 bypasses the gate (real-world retry pattern)
        result = loop.run(initial_context={"evidence_gate_retry_count": 1})
        assert result.termination_reason == LoopTerminationReason.COMPLETED
        assert "evidence_1" in result.evidence_refs
        assert "evidence_2" in result.evidence_refs

    def test_max_steps_reached(self) -> None:
        registry = _StubRegistry({"search_code": {"results": []}})
        config = AgentLoopConfig(max_steps=2, budget_units=10)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            return AgentLoopAction(tool="search_code", payload={"q": f"step_{step}"})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.MAX_STEPS
        assert result.steps_executed == 2


# ---------------------------------------------------------------------------
# ToolResponseEnvelope
# ---------------------------------------------------------------------------


class TestToolResponseEnvelope:
    """Verify the generic response envelope."""

    def test_default_payload(self) -> None:
        env = ToolResponseEnvelope(tool="test")
        assert env.tool == "test"
        assert env.payload == {}

    def test_custom_payload(self) -> None:
        env = ToolResponseEnvelope(tool="search", payload={"hits": 5})
        assert env.payload["hits"] == 5


# ---------------------------------------------------------------------------
# BoundedAgentLoop — budget cost exceeds remaining
# ---------------------------------------------------------------------------


class TestBudgetCostExceedsRemaining:
    def test_action_cost_exceeds_budget_terminates(self) -> None:
        registry = _StubRegistry({"search_code": {}})
        config = AgentLoopConfig(max_steps=5, budget_units=1)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            return AgentLoopAction(tool="search_code", payload={}, budget_cost=5)

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.BUDGET_EXHAUSTED
        assert result.steps_executed == 0


# ---------------------------------------------------------------------------
# BoundedAgentLoop — stagnation detection
# ---------------------------------------------------------------------------


class TestStagnationDetection:
    def test_repeated_calls_trigger_stagnation(self) -> None:
        registry = _StubRegistry({"search_code": {"results": []}})
        # stagnation_threshold=2 means 2 consecutive stagnant steps triggers it
        config = AgentLoopConfig(max_steps=20, budget_units=50, stagnation_threshold=2)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            # Always return the same action — triggers stagnation
            return AgentLoopAction(tool="search_code", payload={"q": "same"})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.STAGNATION

    def test_breadth_enforcement_resets_stagnation(self) -> None:
        registry = _StubRegistry({"search_code": {"results": []}})
        config = AgentLoopConfig(max_steps=5, budget_units=20, stagnation_threshold=2)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                # breadth_enforcement resets stagnation counter
                return AgentLoopAction(
                    tool="search_code",
                    payload={"q": "same"},
                    route_reason="breadth_enforcement",
                )
            return None

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        # Should complete (not stagnate) because breadth_enforcement resets counter
        assert result.termination_reason == LoopTerminationReason.COMPLETED


# ---------------------------------------------------------------------------
# BoundedAgentLoop — tool_calls_limit
# ---------------------------------------------------------------------------


class TestToolCallsLimit:
    def test_tool_calls_limit_triggers_budget_exhausted(self) -> None:
        registry = _StubRegistry({"search_code": {}})
        config = AgentLoopConfig(max_steps=20, budget_units=50, tool_calls_limit=2, stagnation_threshold=10)

        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            return AgentLoopAction(tool="search_code", payload={"q": f"step_{step}"})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.BUDGET_EXHAUSTED
        assert result.steps_executed == 2


# ---------------------------------------------------------------------------
# BoundedAgentLoop — require_evidence / insufficient evidence gate
# ---------------------------------------------------------------------------


class TestRequireEvidence:
    def test_require_evidence_with_no_refs_returns_insufficient(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig(require_evidence=True, min_evidence_refs=2)
        loop = BoundedAgentLoop(registry=registry, config=config, planner=None)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.INSUFFICIENT_EVIDENCE

    def test_require_evidence_satisfied_returns_completed(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig(require_evidence=True, min_evidence_refs=1)
        loop = BoundedAgentLoop(registry=registry, config=config, planner=None)
        result = loop.run(initial_context={"evidence_refs": ["ref_1"]})
        assert result.termination_reason == LoopTerminationReason.COMPLETED


# ---------------------------------------------------------------------------
# BoundedAgentLoop — evidence gate with custom hooks
# ---------------------------------------------------------------------------


class TestEvidenceGateWithHooks:
    def test_evidence_gate_applied_when_requirements_not_met(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()

        loop = BoundedAgentLoop(
            registry=registry,
            config=config,
            planner=None,
            hooks=_CustomHooks(),
        )
        # evidence_gate_retry_count=0 means gate is active
        result = loop.run(initial_context={"evidence_gate_retry_count": 0})
        # _CustomHooks returns is_default=False with min_evidence_refs=3
        assert result.termination_reason == LoopTerminationReason.INSUFFICIENT_EVIDENCE

    def test_evidence_gate_bypassed_on_retry(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        loop = BoundedAgentLoop(
            registry=registry,
            config=config,
            planner=None,
            hooks=_CustomHooks(),
        )
        result = loop.run(initial_context={"evidence_gate_retry_count": 1})
        assert result.termination_reason == LoopTerminationReason.COMPLETED


# ---------------------------------------------------------------------------
# BoundedAgentLoop — timeout mid-loop
# ---------------------------------------------------------------------------


class TestTimeoutMidLoop:
    def test_timeout_during_loop_terminates(self) -> None:
        registry = _StubRegistry({"search_code": {}})
        tick = [0.0]

        def fake_clock() -> float:
            tick[0] += 6.0  # each call advances 6s past the 5s timeout
            return tick[0]

        config = AgentLoopConfig(max_steps=10, budget_units=50, timeout_seconds=5.0, stagnation_threshold=20)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            return AgentLoopAction(tool="search_code", payload={"q": f"s{step}"})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner, clock=fake_clock)
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.TIMEOUT


# ---------------------------------------------------------------------------
# BoundedAgentLoop — route_id context propagation
# ---------------------------------------------------------------------------


class TestRouteIdPropagation:
    def test_route_id_stored_in_context(self) -> None:
        captured_ctx: dict[str, Any] = {}
        registry = _StubRegistry({"search_code": {}})
        config = AgentLoopConfig(max_steps=5, budget_units=10, stagnation_threshold=10)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentLoopAction(
                    tool="search_code",
                    payload={"q": "test"},
                    route_id="docs_primary",
                    route_reason="docs_route",
                    route_confidence=0.9,
                )
            captured_ctx.update(ctx)
            return None

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        loop.run()
        assert captured_ctx.get("route_id") == "docs_primary"
        assert captured_ctx.get("route_confidence") == 0.9


# ---------------------------------------------------------------------------
# AgentLoopResult.to_trace_metadata
# ---------------------------------------------------------------------------


class TestAgentLoopResultToTraceMetadata:
    def test_basic_serialization(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        loop = BoundedAgentLoop(registry=registry, config=config, planner=None)
        result = loop.run()
        meta = result.to_trace_metadata()
        assert meta["termination_reason"] == "completed"
        assert meta["steps_executed"] == 0
        assert meta["tool_error"] is False

    def test_tool_error_normalized(self) -> None:
        registry = MagicMock(spec=["get_tool", "list_tools", "invoke"])
        registry.invoke.side_effect = ValueError("bad value")
        config = AgentLoopConfig(max_steps=5, budget_units=10)

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            return AgentLoopAction(tool="search_code", payload={})

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        meta = result.to_trace_metadata()
        assert "ValueError" in meta["tool_error"]

    def test_empty_tool_error_normalized_to_false(self) -> None:
        from vds_agent_core.agents.loop import AgentLoopResult

        result = AgentLoopResult(
            termination_reason=LoopTerminationReason.COMPLETED,
            steps_executed=0,
            budget_remaining=10,
            elapsed_seconds=0.1,
            tool_error="   ",
        )
        meta = result.to_trace_metadata()
        assert meta["tool_error"] is False


# ---------------------------------------------------------------------------
# BoundedAgentLoop — _docs_intent_utilization
# ---------------------------------------------------------------------------


class TestDocsIntentUtilization:
    def test_no_route_decision_returns_empty_route(self) -> None:
        registry = _StubRegistry()
        config = AgentLoopConfig()
        loop = BoundedAgentLoop(registry=registry, config=config, planner=None)
        result = loop.run()
        util = result.docs_intent_utilization
        assert util["route_id"] == ""
        assert util["docs_path_expected"] is False
        assert util["docs_path_executed"] is False
        assert util["docs_search_step_count"] == 0
        assert util["docs_read_step_count"] == 0

    def test_docs_route_sets_path_expected(self) -> None:
        registry = _StubRegistry({"search_code": {}})
        config = AgentLoopConfig(max_steps=5, budget_units=10, stagnation_threshold=10)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentLoopAction(
                    tool="search_code",
                    payload={"q": "test"},
                    route_id="docs_primary",
                )
            return None

        loop = BoundedAgentLoop(registry=registry, config=config, planner=planner)
        result = loop.run()
        util = result.docs_intent_utilization
        assert util["docs_path_expected"] is True

    def test_has_read_activity_hook_triggers_extra_planner_call(self) -> None:
        """When has_read_activity returns True after max_steps, planner is called once more."""
        registry = _StubRegistry({"read_doc_chunk": {"content": "text"}})
        config = AgentLoopConfig(max_steps=1, budget_units=10, stagnation_threshold=10)
        call_count = 0

        def planner(step: int, ctx: dict[str, Any], trace: list[AgentLoopStep]) -> AgentLoopAction | None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return AgentLoopAction(tool="read_doc_chunk", payload={"ref": "doc_1"})
            return None  # second call returns None → COMPLETED

        loop = BoundedAgentLoop(
            registry=registry,
            config=config,
            planner=planner,
            hooks=_CustomHooks(),
        )
        result = loop.run(initial_context={"evidence_gate_retry_count": 1})
        assert result.termination_reason == LoopTerminationReason.COMPLETED
        assert call_count == 2  # extra planner call triggered by has_read_activity


# ---------------------------------------------------------------------------
# BoundedAgentLoop — _effective_stagnation_threshold cross-repo
# ---------------------------------------------------------------------------


class TestEffectiveStagnationThreshold:
    def test_cross_repo_scope_hint_doubles_threshold(self) -> None:
        threshold = BoundedAgentLoop._effective_stagnation_threshold(
            {"scope_hint": "all"}, base_threshold=3, current_step=5
        )
        assert threshold == 6

    def test_normal_scope_returns_base(self) -> None:
        threshold = BoundedAgentLoop._effective_stagnation_threshold({}, base_threshold=3, current_step=5)
        assert threshold == 3

    def test_cross_repo_beyond_grace_steps_returns_base(self) -> None:
        threshold = BoundedAgentLoop._effective_stagnation_threshold(
            {"scope_hint": "all"}, base_threshold=3, current_step=15
        )
        assert threshold == 3


# ---------------------------------------------------------------------------
# BoundedAgentLoop — _compute_call_hash
# ---------------------------------------------------------------------------


class TestComputeCallHash:
    def test_same_inputs_produce_same_hash(self) -> None:
        h1 = BoundedAgentLoop._compute_call_hash("search_code", {"q": "test"})
        h2 = BoundedAgentLoop._compute_call_hash("search_code", {"q": "test"})
        assert h1 == h2

    def test_different_tools_produce_different_hash(self) -> None:
        h1 = BoundedAgentLoop._compute_call_hash("search_code", {"q": "test"})
        h2 = BoundedAgentLoop._compute_call_hash("search_docs", {"q": "test"})
        assert h1 != h2

    def test_hash_is_16_chars(self) -> None:
        h = BoundedAgentLoop._compute_call_hash("tool", {})
        assert len(h) == 16


# ---------------------------------------------------------------------------
# BoundedAgentLoop — _resolve_depth_stop_reason
# ---------------------------------------------------------------------------


class TestResolveDepthStopReason:
    def test_depth_le_1_returns_none(self) -> None:
        reason = BoundedAgentLoop._resolve_depth_stop_reason(
            context={}, termination_reason=LoopTerminationReason.COMPLETED, max_depth_level=1
        )
        assert reason is None

    def test_explicit_context_reason_returned(self) -> None:
        reason = BoundedAgentLoop._resolve_depth_stop_reason(
            context={"tool_first_depth_stop_reason": "custom_reason"},
            termination_reason=LoopTerminationReason.COMPLETED,
            max_depth_level=2,
        )
        assert reason == "custom_reason"

    def test_termination_reason_mapped(self) -> None:
        reason = BoundedAgentLoop._resolve_depth_stop_reason(
            context={}, termination_reason=LoopTerminationReason.MAX_STEPS, max_depth_level=2
        )
        assert reason == "max_steps_reached"

    def test_stagnation_mapped(self) -> None:
        reason = BoundedAgentLoop._resolve_depth_stop_reason(
            context={}, termination_reason=LoopTerminationReason.STAGNATION, max_depth_level=2
        )
        assert reason == "stagnation_guardrail"
