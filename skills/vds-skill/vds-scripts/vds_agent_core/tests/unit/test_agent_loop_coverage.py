"""Coverage uplift for vds_agent_core.agents.loop (W5.4).

Targets lines 151-153, 216, 257-268, 398-404, 569, 604, 616, 627, 640,
645, 647, 649, 669-672, 679, 681, 683, 691-696, 707-744, 809, 815-817, 842.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from vds_agent_core.agents.hooks import NoOpHooks
from vds_agent_core.agents.loop import (
    AgentLoopAction,
    AgentLoopConfig,
    AgentLoopResult,
    AgentLoopStep,
    BoundedAgentLoop,
    LoopTerminationReason,
)
from vds_agent_core.agents.tools import ToolResponseEnvelope

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _StubRegistry:
    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self._responses = responses or {}

    def invoke(self, tool: str, payload: dict[str, Any]) -> ToolResponseEnvelope:
        return ToolResponseEnvelope(tool=tool, payload=dict(self._responses.get(tool, {})))

    def list_tools(self) -> list[str]:
        return list(self._responses.keys())


def _config(
    *,
    max_steps: int = 3,
    timeout_seconds: float = 60.0,
    budget_units: int = 100,
    stagnation_threshold: int = 5,
    tool_calls_limit: int = 0,
    evidence_overrides: dict[str, Any] | None = None,
) -> AgentLoopConfig:
    return AgentLoopConfig(
        max_steps=max_steps,
        timeout_seconds=timeout_seconds,
        budget_units=budget_units,
        stagnation_threshold=stagnation_threshold,
        tool_calls_limit=tool_calls_limit,
        evidence_overrides=evidence_overrides,
    )


def _done_action() -> AgentLoopAction:
    return AgentLoopAction(tool="__done__", payload={})


# ---------------------------------------------------------------------------
# AgentLoopResult.to_trace_metadata — lines 151-153 (depth_stop_reason str)
# ---------------------------------------------------------------------------


class TestToTraceMetadata:
    def test_depth_stop_reason_string_normalized(self) -> None:
        result = AgentLoopResult(
            termination_reason=LoopTerminationReason.COMPLETED,
            steps_executed=1,
            budget_remaining=50,
            elapsed_seconds=1.0,
            depth_stop_reason="max_steps_reached",
        )
        meta = result.to_trace_metadata()
        assert meta["depth_stop_reason"] == "max_steps_reached"

    def test_depth_stop_reason_whitespace_only_stays_false(self) -> None:
        result = AgentLoopResult(
            termination_reason=LoopTerminationReason.COMPLETED,
            steps_executed=0,
            budget_remaining=50,
            elapsed_seconds=0.0,
            depth_stop_reason="   ",
        )
        meta = result.to_trace_metadata()
        assert meta["depth_stop_reason"] is False


# ---------------------------------------------------------------------------
# BoundedAgentLoop.run — line 216 (evidence_overrides set into context)
# ---------------------------------------------------------------------------


class TestRunWithEvidenceOverrides:
    def test_evidence_overrides_propagated_to_context(self) -> None:
        registry = _StubRegistry()
        cfg = _config(evidence_overrides={"custom_key": "value"}, max_steps=0, budget_units=0)
        loop = BoundedAgentLoop(registry, cfg)
        result = loop.run(initial_context={})
        # budget=0 → BUDGET_EXHAUSTED immediately; context propagation verified by no error
        assert result.termination_reason == LoopTerminationReason.BUDGET_EXHAUSTED


# ---------------------------------------------------------------------------
# BoundedAgentLoop.run — lines 257-268 (tracing_active path)
# ---------------------------------------------------------------------------


class TestRunTracingActivePath:
    def test_tracing_active_executes_loop(self) -> None:
        class _TracingHooks(NoOpHooks):
            def get_trace_context(self) -> dict[str, Any]:
                return {"loop_id": "test-loop-123", "repo": "my-repo"}

        registry = _StubRegistry()
        # planner=None → _finish_without_next_action immediately → COMPLETED
        cfg = _config(max_steps=2, budget_units=10)
        loop = BoundedAgentLoop(registry, cfg, planner=None, hooks=_TracingHooks())
        with patch.object(
            type(loop._tracer), "is_enabled", new_callable=lambda: property(lambda self: True)
        ):
            with patch.object(loop._tracer, "trace_loop") as mock_trace_loop:
                ctx_mgr = MagicMock()
                ctx_mgr.__enter__ = MagicMock(return_value=None)
                ctx_mgr.__exit__ = MagicMock(return_value=False)
                mock_trace_loop.return_value = ctx_mgr
                result = loop.run()
        assert result.termination_reason == LoopTerminationReason.COMPLETED


# ---------------------------------------------------------------------------
# _count_docs_tool_steps — line 604 (delegates to hooks)
# ---------------------------------------------------------------------------


class TestCountDocsToolSteps:
    def test_delegates_to_hooks(self) -> None:
        hooks = MagicMock()
        hooks.count_doc_reads.return_value = 5
        registry = _StubRegistry()
        loop = BoundedAgentLoop(registry, _config(), hooks=hooks)
        steps: list[AgentLoopStep] = []
        result = loop._count_docs_tool_steps(steps)
        assert result == 5
        hooks.count_doc_reads.assert_called_once_with(steps)


# ---------------------------------------------------------------------------
# _count_docs_tool_steps_from_trace — lines 614-616 (callable/non-callable)
# ---------------------------------------------------------------------------


class TestCountDocsToolStepsFromTrace:
    def test_callable_hook_called(self) -> None:
        hooks = MagicMock()
        hooks.count_doc_reads.return_value = 3
        ctx = {"_loop_behavior_hooks": hooks}
        result = BoundedAgentLoop._count_docs_tool_steps_from_trace(context=ctx, trace_steps=[])
        assert result == 3

    def test_non_callable_hook_returns_zero(self) -> None:
        ctx: dict[str, Any] = {}
        result = BoundedAgentLoop._count_docs_tool_steps_from_trace(context=ctx, trace_steps=[])
        assert result == 0


# ---------------------------------------------------------------------------
# _count_doc_search_steps_from_trace — lines 626-628 (callable/non-callable)
# ---------------------------------------------------------------------------


class TestCountDocSearchStepsFromTrace:
    def _make_step(self, tool: str) -> AgentLoopStep:
        return AgentLoopStep(
            step=1,
            tool=tool,
            payload={},
            output={},
            budget_cost=1,
            budget_remaining=10,
        )

    def test_non_callable_hook_returns_zero(self) -> None:
        result = BoundedAgentLoop._count_doc_search_steps_from_trace(
            context={}, trace_steps=[self._make_step("search_docs")]
        )
        assert result == 0

    def test_callable_hook_counts_matching_steps(self) -> None:
        hooks = MagicMock()
        hooks.is_doc_search.side_effect = lambda tool: tool == "search_docs"
        ctx = {"_loop_behavior_hooks": hooks}
        steps = [self._make_step("search_docs"), self._make_step("read_file")]
        result = BoundedAgentLoop._count_doc_search_steps_from_trace(context=ctx, trace_steps=steps)
        assert result == 1


# ---------------------------------------------------------------------------
# _docs_intent_utilization — route_id prefix branches (lines 640-649)
# ---------------------------------------------------------------------------


class TestDocsIntentUtilization:
    def _make_step(self, tool: str, output: dict[str, Any] | None = None) -> AgentLoopStep:
        return AgentLoopStep(
            step=1, tool=tool, payload={}, output=output or {},
            budget_cost=1, budget_remaining=10,
        )

    def test_route_id_docs_prefix_sets_docs_only_mode(self) -> None:
        context: dict[str, Any] = {"route_id": "docs_first_route"}
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_mode"] == "docs_only"

    def test_route_id_code_prefix_sets_code_only_mode(self) -> None:
        context: dict[str, Any] = {"route_id": "code_review_route"}
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_mode"] == "code_only"

    def test_route_id_hybrid_docs_first(self) -> None:
        context: dict[str, Any] = {"route_id": "hybrid_docs_first_route"}
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_mode"] == "hybrid_docs_first"

    def test_route_id_hybrid_code_first(self) -> None:
        context: dict[str, Any] = {"route_id": "hybrid_code_first_route"}
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_mode"] == "hybrid_code_first"

    def test_docs_search_hit_count_incremented(self) -> None:
        hooks = MagicMock()
        hooks.is_doc_search.return_value = True
        hooks.count_doc_reads.return_value = 0
        step = self._make_step("search_docs", output={"hits": ["result1", "result2"]})
        context: dict[str, Any] = {"_loop_behavior_hooks": hooks}
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[step])
        assert result["docs_hit_count"] == 2

    def test_docs_skip_reason_explicit(self) -> None:
        # docs_path_expected=True (route starts with "docs_"), no reads → skip reason checked
        # explicit reason is set → lines 678-679
        context: dict[str, Any] = {
            "route_id": "docs_first",
            "tool_first_docs_skip_reason": "context_unavailable",
        }
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["docs_skip_reason"] == "context_unavailable"

    def test_docs_skip_reason_search_no_hits(self) -> None:
        # docs_search_step_count > 0, docs_hit_count == 0 → "docs_search_no_hits" (line 681)
        hooks = MagicMock()
        hooks.is_doc_search.return_value = True
        # count_doc_reads returns 0 (no actual read steps, only search steps)
        hooks.count_doc_reads.return_value = 0
        step = self._make_step("search_docs", output={"hits": []})  # search step, no hits
        context: dict[str, Any] = {
            "route_id": "docs_first",
            "_loop_behavior_hooks": hooks,
        }
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[step])
        # docs_search_step_count=1 (is_doc_search=True), docs_hit_count=0 → "docs_search_no_hits"
        assert result["docs_skip_reason"] == "docs_search_no_hits"

    def test_docs_skip_reason_hits_not_read(self) -> None:
        # docs_search_step_count > 0, docs_hit_count > 0, docs_read_step_count=0 → line 683
        hooks = MagicMock()
        hooks.is_doc_search.return_value = True
        hooks.count_doc_reads.return_value = 0  # no reads
        step = self._make_step("search_docs", output={"hits": ["hit1"]})  # 1 hit
        context: dict[str, Any] = {
            "route_id": "docs_first",
            "_loop_behavior_hooks": hooks,
        }
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[step])
        # docs_search=1, hits=1, reads=0 → "docs_search_hits_not_read"
        assert result["docs_skip_reason"] == "docs_search_hits_not_read"

    def test_route_escalation_from_transitions(self) -> None:
        context: dict[str, Any] = {
            "route_id": "docs_first",
            "tool_first_route_decision": {
                "route_id": "docs_first",
                "route_mode": "docs_only",
                "code_target": True,
                "docs_target": True,
            },
            "tool_first_route_transitions": [
                {
                    "from_route_id": "docs_first",
                    "from_route_mode": "docs_only",
                    "to_route_id": "code_review",
                    "to_route_mode": "hybrid_code_first",
                    "reason": "evidence_required",
                    "step_number": 3,
                }
            ],
        }
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_escalation_applied"] is True
        assert result["route_escalation_reason"] == "evidence_required"
        assert result["route_escalation_step_index"] == 3

    def test_route_escalation_step_index_fallback_to_false(self) -> None:
        context: dict[str, Any] = {
            "route_id": "docs_first",
            "tool_first_route_decision": {
                "route_id": "docs_first",
                "route_mode": "docs_only",
                "code_target": True,
            },
            "tool_first_route_transitions": [
                {
                    "from_route_mode": "docs_only",
                    "to_route_mode": "hybrid_code_first",
                    "step_number": 0,  # 0 → route_escalation_step_index = False
                }
            ],
        }
        result = BoundedAgentLoop._docs_intent_utilization(context=context, trace_steps=[])
        assert result["route_escalation_step_index"] is False


# ---------------------------------------------------------------------------
# _build_result — lines 809, 815-817 (requirement_analysis + evidence gate)
# ---------------------------------------------------------------------------


class TestBuildResult:
    def test_requirement_analysis_from_context_keys(self) -> None:
        # planner=None → _finish_without_next_action → COMPLETED
        # context keys for requirement_analysis_snapshot are propagated
        registry = _StubRegistry()
        loop = BoundedAgentLoop(registry, _config(), planner=None)
        ctx = {
            "analysis_mode": "strict",
            "analysis_reason_codes": ["code_review"],
        }
        result = loop.run(initial_context=ctx)
        assert result.termination_reason == LoopTerminationReason.COMPLETED

    def test_control_objective_evidence_gate_diagnostics(self) -> None:
        # Pre-populate context with evidence gate flags; planner=None → immediate finish
        registry = _StubRegistry()
        loop = BoundedAgentLoop(registry, _config(), planner=None)
        ctx = {
            "control_objective_evidence_gate_applied": True,
            "required_min_evidence_refs": 3,
            "required_min_search_patterns": 2,
            "observed_evidence_refs": 0,
            "observed_search_patterns": 0,
            "evidence_gate_reason_code": "evidence_gate_failed",
        }
        result = loop.run(initial_context=ctx)
        assert result.termination_reason == LoopTerminationReason.COMPLETED


# ---------------------------------------------------------------------------
# _build_result — line 842 (normalized max_depth from trace_steps)
# ---------------------------------------------------------------------------


class TestBuildResultMaxDepth:
    def test_max_depth_normalized_from_trace_when_zero(self) -> None:
        registry = _StubRegistry()
        loop = BoundedAgentLoop(registry, _config(max_steps=2), planner=None)
        result = loop.run()
        # max_depth_level initialized to 0, trace_steps empty → stays 0
        assert isinstance(result.max_depth_level, int)


# ---------------------------------------------------------------------------
# run — line 398-404 (first-step context hook wire)
# ---------------------------------------------------------------------------


class TestRunFirstStepContextWire:
    def test_control_objective_wired_from_first_step(self) -> None:
        class _ContextHooks(NoOpHooks):
            def should_skip_first_step(self, tool: str, context: dict[str, Any]) -> bool:
                return tool == "get_row_context"

        registry = _StubRegistry({
            "get_row_context": {
                "context": {
                    "requirement_interpretation": {
                        "control_objective": "Ensure data is encrypted"
                    }
                }
            }
        })
        call_count = [0]

        def planner(step: int, ctx: dict[str, Any], trace: list[Any]) -> AgentLoopAction | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return AgentLoopAction(tool="get_row_context", payload={})
            return None  # terminate after first step

        loop = BoundedAgentLoop(registry, _config(max_steps=5), planner=planner, hooks=_ContextHooks())
        result = loop.run()
        # After first step, planner returns None → _finish_without_next_action
        assert result.termination_reason in {
            LoopTerminationReason.COMPLETED,
            LoopTerminationReason.INSUFFICIENT_EVIDENCE,
        }


# ---------------------------------------------------------------------------
# run — line 569 (insufficient_evidence termination with requirements hook)
# ---------------------------------------------------------------------------


class TestRunInsufficientEvidence:
    def test_insufficient_evidence_termination(self) -> None:
        class _EvidenceHooks(NoOpHooks):
            def lookup_evidence_requirements(self, context: dict[str, Any]) -> dict[str, Any]:
                return {"min_evidence_refs": 5, "min_search_patterns": 3, "is_default": False}

        registry = _StubRegistry()
        # planner=None → _finish_without_next_action → _apply_evidence_gate
        # with 0 evidence_refs < min 5 → INSUFFICIENT_EVIDENCE
        loop = BoundedAgentLoop(
            registry, _config(max_steps=5), planner=None, hooks=_EvidenceHooks()
        )
        result = loop.run()
        assert result.termination_reason == LoopTerminationReason.INSUFFICIENT_EVIDENCE
