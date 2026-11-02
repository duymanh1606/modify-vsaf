"""Bounded autonomy loop for tool-first analysis (generic, extracted from audit).

The loop is intentionally conservative and deterministic:
- hard bounds on steps, timeout, and budget
- strict termination reason taxonomy for observability
- tool calls delegated through centralized ToolRegistry
- orchestrator-specific behavior injected via LoopBehaviorHooks
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from vds_agent_core.agents.hooks import LoopBehaviorHooks, NoOpHooks
from vds_agent_core.observability import AgentTracer

if TYPE_CHECKING:
    from vds_agent_core.agents.tools import ToolRegistry


@contextmanager
def _nullcontext():
    """No-op context manager for when tracing is disabled."""
    yield


_REQUIREMENT_ANALYSIS_DIAGNOSTIC_KEYS: tuple[str, ...] = (
    "analysis_mode",
    "analysis_reason_codes",
    "required_anchor_modalities",
    "project_scope_required",
    "generic_anchor_exemption",
    "minimum_substantive_code_anchors",
    "finalization_policy",
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LoopTerminationReason(StrEnum):
    """Canonical loop termination reasons."""

    COMPLETED = "completed"
    MAX_STEPS = "max_steps"
    TIMEOUT = "timeout"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    TOOL_ERROR = "tool_error"
    STAGNATION = "stagnation"


@dataclass(slots=True)
class AgentLoopConfig:
    """Execution bounds for the autonomy loop."""

    max_steps: int = 15
    timeout_seconds: float = 10.0
    budget_units: int = 15
    tool_calls_limit: int = 12
    require_evidence: bool = False
    min_evidence_refs: int = 1
    stagnation_threshold: int = 3
    """Number of consecutive steps without progress before stagnation termination."""
    checkpoint_key: str | None = None
    """Optional state checkpoint key for persistence/resume."""
    checkpoint_manager: Any | None = field(default=None, repr=False)
    """Optional CheckpointManager for state persistence (opt-in)."""
    evidence_overrides: dict[str, dict[str, int]] = field(default_factory=dict)


class AgentLoopAction(_StrictModel):
    """Planner-selected action for the next step."""

    tool: str
    payload: dict[str, Any] = Field(default_factory=dict)
    budget_cost: int = Field(default=1, ge=1)
    route_id: str | None = None
    route_reason: str | None = None
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ambiguity_reason_codes: list[str] = Field(default_factory=list)
    required_steps: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    override_source: str | None = None
    override_reason: str | None = None
    depth_level: int = Field(default=1, ge=1)
    depth_increase_reason: str | None = None


class AgentLoopStep(_StrictModel):
    """Per-step execution trace."""

    step: int = Field(ge=1)
    tool: str
    budget_cost: int = Field(ge=1)
    budget_remaining: int = Field(ge=0)
    output: dict[str, Any] = Field(default_factory=dict)
    route_id: str | None = None
    route_reason: str | None = None
    route_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ambiguity_reason_codes: list[str] = Field(default_factory=list)
    required_steps: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    override_source: str | None = None
    override_reason: str | None = None
    depth_level: int = Field(default=1, ge=1)
    depth_increase_reason: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentLoopResult(_StrictModel):
    """Bounded loop result with trace metadata hooks."""

    termination_reason: LoopTerminationReason
    steps_executed: int = Field(ge=0)
    budget_remaining: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0.0)
    evidence_refs: list[str] = Field(default_factory=list)
    trace_steps: list[AgentLoopStep] = Field(default_factory=list)
    tool_error: str | None = None
    docs_intent_utilization: dict[str, Any] = Field(default_factory=dict)
    code_ranking_diagnostics: dict[str, Any] = Field(default_factory=dict)
    project_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    cross_repo_evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    config_repo_companion_refs: list[dict[str, Any]] = Field(default_factory=list)
    prior_knowledge_refs: list[dict[str, Any]] = Field(default_factory=list)
    max_depth_level: int = Field(default=0, ge=0)
    depth_stop_reason: str | None = None

    def to_trace_metadata(self) -> dict[str, Any]:
        """Serialize stable metadata payload for row evaluator passthrough."""
        normalized_tool_error: str | bool = False
        raw_tool_error = self.tool_error
        if isinstance(raw_tool_error, str):
            normalized_text = raw_tool_error.strip()
            if normalized_text:
                normalized_tool_error = normalized_text
        normalized_depth_stop_reason: str | bool = False
        raw_depth_stop_reason = self.depth_stop_reason
        if isinstance(raw_depth_stop_reason, str):
            normalized_depth_text = raw_depth_stop_reason.strip()
            if normalized_depth_text:
                normalized_depth_stop_reason = normalized_depth_text
        return {
            "termination_reason": self.termination_reason.value,
            "steps_executed": self.steps_executed,
            "budget_remaining": self.budget_remaining,
            "elapsed_seconds": self.elapsed_seconds,
            "evidence_refs": list(self.evidence_refs),
            "trace_steps": [step.model_dump() for step in self.trace_steps],
            "tool_error": normalized_tool_error,
            "docs_intent_utilization": dict(self.docs_intent_utilization),
            "code_ranking_diagnostics": dict(self.code_ranking_diagnostics),
            "project_artifact_refs": list(self.project_artifact_refs),
            "cross_repo_evidence_refs": list(self.cross_repo_evidence_refs),
            "config_repo_companion_refs": list(self.config_repo_companion_refs),
            "prior_knowledge_refs": list(self.prior_knowledge_refs),
            "max_depth_level": int(self.max_depth_level or 0),
            "depth_stop_reason": normalized_depth_stop_reason,
        }


PlannerFn = Callable[[int, dict[str, Any], list[AgentLoopStep]], AgentLoopAction | None]


class BoundedAgentLoop:
    """Deterministic, bounded autonomy loop over typed tool calls.

    Orchestrator-specific behavior is injected via ``hooks``.  The default
    ``NoOpHooks`` makes the loop fully generic (no audit coupling).
    """

    def __init__(
        self,
        registry: ToolRegistry,
        config: AgentLoopConfig,
        *,
        planner: PlannerFn | None = None,
        clock: Callable[[], float] | None = None,
        hooks: LoopBehaviorHooks | None = None,
    ) -> None:
        self.registry = registry
        self.config = config
        self._planner = planner
        self._clock = clock or time.monotonic
        self._hooks = hooks or NoOpHooks()
        self._call_history: set[str] = set()
        self._stagnation_counter: int = 0
        self._tracer = AgentTracer()

    def run(
        self,
        *,
        initial_context: dict[str, Any] | None = None,
        reset_stagnation_counter: bool = False,
    ) -> AgentLoopResult:
        self._call_history.clear()
        self._stagnation_counter = 0

        context = dict(initial_context or {})
        context["_loop_behavior_hooks"] = self._hooks
        evidence_refs = list(context.get("evidence_refs") or [])
        if "seed_evidence_refs" not in context:
            context["seed_evidence_refs"] = list(evidence_refs)
        if self.config.evidence_overrides:
            context.setdefault("_evidence_overrides", self.config.evidence_overrides)

        budget_remaining = max(0, int(self.config.budget_units))
        _max_steps = max(0, int(self.config.max_steps))
        timeout_seconds = max(0.0, float(self.config.timeout_seconds))
        _tool_calls_limit = max(0, int(self.config.tool_calls_limit))
        tool_calls_used = 0
        trace: list[AgentLoopStep] = []
        step_count = 0
        max_depth_level = 0

        started = self._clock()

        if timeout_seconds == 0.0:
            return self._build_result(
                termination_reason=LoopTerminationReason.TIMEOUT,
                steps_executed=0,
                budget_remaining=budget_remaining,
                elapsed_seconds=0.0,
                evidence_refs=evidence_refs,
                trace_steps=trace,
                context=context,
                max_depth_level=max_depth_level,
            )

        if budget_remaining <= 0:
            return self._build_result(
                termination_reason=LoopTerminationReason.BUDGET_EXHAUSTED,
                steps_executed=0,
                budget_remaining=0,
                elapsed_seconds=max(0.0, self._clock() - started),
                evidence_refs=evidence_refs,
                trace_steps=trace,
                context=context,
                max_depth_level=max_depth_level,
            )

        trace_context = self._hooks.get_trace_context()
        tracing_active = bool(trace_context) and self._tracer.is_enabled

        if tracing_active:
            config_for_tracer = {
                "max_steps": self.config.max_steps,
                "timeout_seconds": self.config.timeout_seconds,
                "budget_units": self.config.budget_units,
            }
            loop_id = trace_context.get("loop_id", "unknown")
            with self._tracer.trace_loop(loop_id, config_for_tracer) as loop_span:
                if loop_span:
                    for key, value in trace_context.items():
                        if key != "loop_id" and value is not None:
                            loop_span.set_attribute(f"trace.context.{key}", str(value))
                result = self._run_loop(
                    context=context,
                    started=started,
                    trace=trace,
                    step_count=step_count,
                    max_depth_level=max_depth_level,
                    budget_remaining=budget_remaining,
                    tool_calls_used=tool_calls_used,
                    tracing_active=tracing_active,
                    evidence_refs=evidence_refs,
                )
        else:
            result = self._run_loop(
                context=context,
                started=started,
                trace=trace,
                step_count=step_count,
                max_depth_level=max_depth_level,
                budget_remaining=budget_remaining,
                tool_calls_used=tool_calls_used,
                tracing_active=tracing_active,
                evidence_refs=evidence_refs,
            )
        return result

    def _run_loop(
        self,
        *,
        context: dict[str, Any],
        started: float,
        trace: list[AgentLoopStep],
        step_count: int,
        max_depth_level: int,
        budget_remaining: int,
        tool_calls_used: int,
        tracing_active: bool,
        evidence_refs: list[str],
    ) -> AgentLoopResult:
        """Inner loop implementation (extracted for tracing integration)."""
        max_steps = max(0, int(self.config.max_steps))
        timeout_seconds = max(0.0, float(self.config.timeout_seconds))
        tool_calls_limit = max(0, int(self.config.tool_calls_limit))

        while step_count < max_steps:
            elapsed = max(0.0, self._clock() - started)
            if elapsed >= timeout_seconds:
                return self._build_result(
                    termination_reason=LoopTerminationReason.TIMEOUT,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    elapsed_seconds=elapsed,
                    evidence_refs=evidence_refs,
                    trace_steps=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

            action = self._next_action(step_count + 1, context, trace)
            if action is None:
                return self._finish_without_next_action(
                    started=started,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    evidence_refs=evidence_refs,
                    trace=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

            if action.budget_cost > budget_remaining:
                return self._build_result(
                    termination_reason=LoopTerminationReason.BUDGET_EXHAUSTED,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    elapsed_seconds=max(0.0, self._clock() - started),
                    evidence_refs=evidence_refs,
                    trace_steps=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

            with self._tracer.trace_tool_call(action.tool, dict(action.payload)) if tracing_active else _nullcontext():
                try:
                    response = self.registry.invoke(action.tool, action.payload)
                except Exception as exc:
                    return self._build_result(
                        termination_reason=LoopTerminationReason.TOOL_ERROR,
                        steps_executed=step_count,
                        budget_remaining=budget_remaining,
                        elapsed_seconds=max(0.0, self._clock() - started),
                        evidence_refs=evidence_refs,
                        trace_steps=trace,
                        tool_error=f"{type(exc).__name__}: {exc}",
                        context=context,
                        max_depth_level=max_depth_level,
                    )

            step_count += 1
            tool_calls_used += 1
            budget_remaining = max(0, budget_remaining - action.budget_cost)
            output_payload = response.payload
            trace.append(
                AgentLoopStep(
                    step=step_count,
                    tool=action.tool,
                    budget_cost=action.budget_cost,
                    budget_remaining=budget_remaining,
                    output=output_payload,
                    route_id=action.route_id,
                    route_reason=action.route_reason,
                    route_confidence=float(action.route_confidence or 0.0),
                    ambiguity_reason_codes=list(action.ambiguity_reason_codes),
                    required_steps=list(action.required_steps),
                    required_tools=list(action.required_tools),
                    override_source=action.override_source,
                    override_reason=action.override_reason,
                    depth_level=int(action.depth_level or 1),
                    depth_increase_reason=action.depth_increase_reason,
                    payload=dict(action.payload),
                )
            )
            max_depth_level = max(max_depth_level, int(action.depth_level or 1))
            context[f"tool_{action.tool}_output"] = output_payload

            # Hook: wire context from first-step context query output
            if (
                self._hooks.should_skip_first_step(action.tool, context)
                and step_count == 1
                and "control_objective" not in context
            ):
                _grc_ctx = output_payload.get("context", {}) if isinstance(output_payload, dict) else {}
                _interp = _grc_ctx.get("requirement_interpretation", {}) if isinstance(_grc_ctx, dict) else {}
                _control_obj = (
                    str(_interp.get("control_objective") or "").strip() if isinstance(_interp, dict) else ""
                ) or (str(_grc_ctx.get("requirement_category") or "").strip() if isinstance(_grc_ctx, dict) else "")
                if _control_obj:
                    context["control_objective"] = _control_obj

            if action.route_id:
                context["route_id"] = action.route_id
                context["route_reason"] = action.route_reason
                context["route_confidence"] = float(action.route_confidence or 0.0)
                context["ambiguity_reason_codes"] = list(action.ambiguity_reason_codes)
                context["required_steps"] = list(action.required_steps)
                context["required_tools"] = list(action.required_tools)
                context["override_source"] = action.override_source
                context["override_reason"] = action.override_reason

            prev_evidence_count = len(evidence_refs)

            # Hook: check if this tool records evidence
            if self._hooks.is_evidence_recording(action.tool):
                rows = output_payload.get("refs") or []
                evidence_refs = [str(row.get("ref_value", "")) for row in rows if row.get("ref_value")]
                context["evidence_refs"] = evidence_refs

            # Stagnation detection
            _is_breadth_enforcement = action.route_reason == "breadth_enforcement"
            call_hash = self._compute_call_hash(action.tool, action.payload)
            if _is_breadth_enforcement:
                self._call_history.add(call_hash)
                self._stagnation_counter = 0
            elif call_hash in self._call_history:
                self._stagnation_counter += 1
            else:
                self._call_history.add(call_hash)
                self._stagnation_counter = 0

            # Hook: use is_context_query instead of hardcoded ToolName.GET_ROW_CONTEXT
            if (
                not _is_breadth_enforcement
                and len(evidence_refs) == prev_evidence_count
                and not self._hooks.is_context_query(action.tool)
            ):
                self._stagnation_counter += 1

            effective_stagnation_threshold = self._effective_stagnation_threshold(
                context,
                self.config.stagnation_threshold,
                step_count,
            )

            if self._stagnation_counter >= effective_stagnation_threshold:
                return self._build_result(
                    termination_reason=LoopTerminationReason.STAGNATION,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    elapsed_seconds=max(0.0, self._clock() - started),
                    evidence_refs=evidence_refs,
                    trace_steps=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

            if tool_calls_limit > 0 and tool_calls_used >= tool_calls_limit:
                return self._build_result(
                    termination_reason=LoopTerminationReason.BUDGET_EXHAUSTED,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    elapsed_seconds=max(0.0, self._clock() - started),
                    evidence_refs=evidence_refs,
                    trace_steps=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

        # Hook: use has_read_activity instead of hardcoded ToolName check
        if self._hooks.has_read_activity(trace):
            next_action = self._next_action(step_count + 1, context, trace)
            if next_action is None:
                return self._finish_without_next_action(
                    started=started,
                    steps_executed=step_count,
                    budget_remaining=budget_remaining,
                    evidence_refs=evidence_refs,
                    trace=trace,
                    context=context,
                    max_depth_level=max_depth_level,
                )

        return self._build_result(
            termination_reason=LoopTerminationReason.MAX_STEPS,
            steps_executed=step_count,
            budget_remaining=budget_remaining,
            elapsed_seconds=max(0.0, self._clock() - started),
            evidence_refs=evidence_refs,
            trace_steps=trace,
            context=context,
            max_depth_level=max_depth_level,
        )

    def _next_action(
        self,
        step_number: int,
        context: dict[str, Any],
        trace: list[AgentLoopStep],
    ) -> AgentLoopAction | None:
        if self._planner is None:
            return None
        return self._planner(step_number, context, trace)

    def _finish_without_next_action(
        self,
        *,
        started: float,
        steps_executed: int,
        budget_remaining: int,
        evidence_refs: list[str],
        trace: list[AgentLoopStep],
        context: dict[str, Any],
        max_depth_level: int,
    ) -> AgentLoopResult:
        if self.config.require_evidence and len(evidence_refs) < max(1, self.config.min_evidence_refs):
            reason = LoopTerminationReason.INSUFFICIENT_EVIDENCE
        else:
            reason = self._apply_evidence_gate(evidence_refs=evidence_refs, trace=trace, context=context)

        return self._build_result(
            termination_reason=reason,
            steps_executed=steps_executed,
            budget_remaining=budget_remaining,
            elapsed_seconds=max(0.0, self._clock() - started),
            evidence_refs=evidence_refs,
            trace_steps=trace,
            context=context,
            max_depth_level=max_depth_level,
        )

    def _apply_evidence_gate(
        self,
        *,
        evidence_refs: list[str],
        trace: list[AgentLoopStep],
        context: dict[str, Any],
    ) -> LoopTerminationReason:
        """Control-objective evidence gate — delegates to hooks for requirements lookup."""
        if int(context.get("evidence_gate_retry_count") or 0) >= 1:
            return LoopTerminationReason.COMPLETED

        requirements = self._hooks.lookup_evidence_requirements(context)

        # Only orchestrator-specific rows have stricter requirements.
        # If requirements dict is empty or explicitly marked as default, skip the gate.
        # Non-default requirements (e.g., architecture rows) must have min_evidence_refs.
        if not requirements or requirements.get("is_default", False):
            return LoopTerminationReason.COMPLETED

        search_pattern_count = sum(1 for step in trace if step.tool == "search_code")
        evidence_count = len(evidence_refs)
        min_refs: int = requirements.get("min_evidence_refs", 1)
        min_searches: int = requirements.get("min_search_patterns", 1)

        if evidence_count < min_refs or search_pattern_count < min_searches:
            context["control_objective_evidence_gate_applied"] = True
            context["required_min_evidence_refs"] = min_refs
            context["required_min_search_patterns"] = min_searches
            context["observed_evidence_refs"] = evidence_count
            context["observed_search_patterns"] = search_pattern_count
            context["evidence_gate_reason_code"] = "evidence_gate_failed"
            return LoopTerminationReason.INSUFFICIENT_EVIDENCE

        return LoopTerminationReason.COMPLETED

    @staticmethod
    def _effective_stagnation_threshold(
        context: dict[str, Any],
        base_threshold: int,
        current_step: int,
    ) -> int:
        """Raise stagnation threshold for cross-repo exploration rows."""
        _CROSS_REPO_GRACE_STEPS = 10
        _CROSS_REPO_TAGS = {"shared_library", "config_pattern", "architecture"}

        scope_hint = str(context.get("scope_hint") or "").strip().lower()
        requirement_type_tag = str(context.get("requirement_type_tag") or "").strip().lower()

        is_cross_repo = (
            scope_hint in {"all", "lib", "config"}
            or requirement_type_tag in _CROSS_REPO_TAGS
            or bool(context.get("shared_library_routing_activated"))
            or bool(context.get("config_repo_companion_applied"))
        )

        if is_cross_repo and current_step <= _CROSS_REPO_GRACE_STEPS:
            return max(base_threshold, base_threshold * 2)

        return base_threshold

    @staticmethod
    def _compute_call_hash(tool_name: str, payload: dict[str, Any]) -> str:
        """Compute a deterministic hash for a tool call to detect repetition."""
        normalized = json.dumps({"tool": tool_name, "args": payload}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _count_docs_tool_steps(self, trace_steps: list[AgentLoopStep]) -> int:
        """Count doc-related tool steps using hooks."""
        return self._hooks.count_doc_reads(trace_steps)

    @staticmethod
    def _count_docs_tool_steps_from_trace(
        *,
        context: dict[str, Any],
        trace_steps: list[AgentLoopStep],
    ) -> int:
        hooks = context.get("_loop_behavior_hooks")
        count_doc_reads = getattr(hooks, "count_doc_reads", None)
        if callable(count_doc_reads):
            return int(count_doc_reads(trace_steps))
        return 0

    @staticmethod
    def _count_doc_search_steps_from_trace(
        *,
        context: dict[str, Any],
        trace_steps: list[AgentLoopStep],
    ) -> int:
        hooks = context.get("_loop_behavior_hooks")
        is_doc_search = getattr(hooks, "is_doc_search", None)
        if not callable(is_doc_search):
            return 0
        return sum(1 for step in trace_steps if is_doc_search(str(step.tool)))

    @classmethod
    def _docs_intent_utilization(
        cls,
        *,
        context: dict[str, Any],
        trace_steps: list[AgentLoopStep],
    ) -> dict[str, Any]:
        def _route_mode(value: Any, *, route_id_value: str) -> str:
            mode = str(value or "").strip()
            if mode:
                return mode
            normalized_route_id = str(route_id_value or "").strip().lower()
            if normalized_route_id.startswith("docs_"):
                return "docs_only"
            if normalized_route_id.startswith("code_"):
                return "code_only"
            if normalized_route_id.startswith("hybrid_docs_first"):
                return "hybrid_docs_first"
            if normalized_route_id.startswith("hybrid_code_first"):
                return "hybrid_code_first"
            return ""

        route_decision = context.get("tool_first_route_decision")
        route_payload = route_decision if isinstance(route_decision, dict) else {}
        route_id = str(route_payload.get("route_id") or context.get("route_id") or "").strip()
        route_mode = _route_mode(route_payload.get("route_mode"), route_id_value=route_id)
        docs_target = bool(route_payload.get("docs_target"))
        code_target = bool(route_payload.get("code_target"))
        is_hybrid_route = route_id.startswith("hybrid_")
        docs_path_expected = bool(route_id.startswith("docs_") or is_hybrid_route or docs_target)
        docs_step_count = cls._count_docs_tool_steps_from_trace(context=context, trace_steps=trace_steps)
        docs_search_step_count = cls._count_doc_search_steps_from_trace(context=context, trace_steps=trace_steps)
        docs_read_step_count = max(0, docs_step_count - docs_search_step_count)
        docs_hit_count = 0
        hooks = context.get("_loop_behavior_hooks")
        is_doc_search = getattr(hooks, "is_doc_search", None)
        for step in trace_steps:
            if not callable(is_doc_search) or not is_doc_search(str(step.tool)):
                continue
            output_payload = step.output if isinstance(step.output, dict) else {}
            hits = output_payload.get("hits")
            if isinstance(hits, list):
                docs_hit_count += len(hits)
        docs_path_executed = docs_step_count > 0
        docs_path_effective = docs_read_step_count > 0
        docs_skip_reason: str | bool = False
        if docs_path_expected and not docs_path_effective:
            explicit_reason = str(context.get("tool_first_docs_skip_reason") or "").strip()
            if explicit_reason:
                docs_skip_reason = explicit_reason
            elif docs_search_step_count > 0 and docs_hit_count == 0:
                docs_skip_reason = "docs_search_no_hits"
            elif docs_search_step_count > 0 and docs_hit_count > 0 and docs_read_step_count == 0:
                docs_skip_reason = "docs_search_hits_not_read"
            else:
                runtime_context = (
                    context.get("tool_get_row_context_output", {}).get("context", {}).get("runtime_context", {})
                )
                state_ready = bool(runtime_context.get("state_dsn")) and bool(runtime_context.get("project_key"))
                if not state_ready:
                    docs_skip_reason = "docs_state_unavailable"
                elif is_hybrid_route and code_target:
                    docs_skip_reason = "hybrid_route_prioritized_code_path"
                elif docs_path_executed and docs_read_step_count == 0:
                    docs_skip_reason = "docs_path_executed_without_read"
                else:
                    docs_skip_reason = "docs_path_not_executed"

        db_family_payload = context.get("tool_first_db_family_coverage")
        db_family_requirement = bool(
            db_family_payload.get("db_requirement") if isinstance(db_family_payload, dict) else False
        )
        route_escalation_required = bool(route_mode == "docs_only" and (code_target or db_family_requirement))
        route_escalation_applied = False
        route_escalation_reason: str | bool = False
        route_escalation_step_index: int | bool = False
        if route_escalation_required:
            transitions = context.get("tool_first_route_transitions")
            if isinstance(transitions, list):
                for entry in transitions:
                    if not isinstance(entry, dict):
                        continue
                    from_mode = _route_mode(
                        entry.get("from_route_mode"),
                        route_id_value=str(entry.get("from_route_id") or ""),
                    )
                    to_mode = _route_mode(
                        entry.get("to_route_mode"),
                        route_id_value=str(entry.get("to_route_id") or ""),
                    )
                    if from_mode != "docs_only" or to_mode not in {"hybrid_code_first", "code_only"}:
                        continue
                    route_escalation_applied = True
                    transition_reason = str(entry.get("reason") or "").strip()
                    route_escalation_reason = transition_reason or "docs_only_route_code_fallback"
                    try:
                        step_index = int(entry.get("step_number") or 0)
                    except (TypeError, ValueError):
                        step_index = 0
                    route_escalation_step_index = step_index if step_index > 0 else False
                    break
            if not route_escalation_applied:
                explicit_reason = str(context.get("tool_first_docs_skip_reason") or "").strip()
                if explicit_reason:
                    route_escalation_reason = explicit_reason
                elif docs_path_effective:
                    route_escalation_reason = "docs_path_effective"
                elif docs_search_step_count > 0 and docs_hit_count == 0:
                    route_escalation_reason = "docs_search_no_hits"
                elif docs_search_step_count > 0 and docs_hit_count > 0 and docs_read_step_count == 0:
                    route_escalation_reason = "docs_search_hits_not_read"
                elif not docs_path_executed:
                    route_escalation_reason = "docs_path_not_executed"
                else:
                    route_escalation_reason = "route_escalation_not_applied"
        return {
            "route_id": route_id,
            "route_mode": route_mode or False,
            "docs_target": docs_target,
            "code_target": code_target,
            "is_hybrid_route": is_hybrid_route,
            "docs_path_expected": docs_path_expected,
            "docs_path_executed": docs_path_executed,
            "docs_path_effective": docs_path_effective,
            "docs_step_count": docs_step_count,
            "docs_search_step_count": docs_search_step_count,
            "docs_read_step_count": docs_read_step_count,
            "docs_hit_count": docs_hit_count,
            "docs_skip_reason": docs_skip_reason,
            "docs_path_skip_reason": docs_skip_reason,
            "db_family_requirement": db_family_requirement,
            "route_escalation_required": route_escalation_required,
            "route_escalation_applied": route_escalation_applied,
            "route_escalation_reason": route_escalation_reason,
            "route_escalation_step_index": route_escalation_step_index,
        }

    @staticmethod
    def _resolve_depth_stop_reason(
        *,
        context: dict[str, Any],
        termination_reason: LoopTerminationReason,
        max_depth_level: int,
    ) -> str | None:
        if max_depth_level <= 1:
            return None
        explicit = str(context.get("tool_first_depth_stop_reason") or "").strip()
        if explicit:
            return explicit
        reason_map: dict[LoopTerminationReason, str] = {
            LoopTerminationReason.COMPLETED: "planner_converged",
            LoopTerminationReason.INSUFFICIENT_EVIDENCE: "planner_converged",
            LoopTerminationReason.MAX_STEPS: "max_steps_reached",
            LoopTerminationReason.TIMEOUT: "timeout_reached",
            LoopTerminationReason.BUDGET_EXHAUSTED: "budget_exhausted",
            LoopTerminationReason.STAGNATION: "stagnation_guardrail",
            LoopTerminationReason.TOOL_ERROR: "tool_error",
        }
        return reason_map.get(termination_reason)

    def _build_result(
        self,
        *,
        termination_reason: LoopTerminationReason,
        steps_executed: int,
        budget_remaining: int,
        elapsed_seconds: float,
        evidence_refs: list[str],
        trace_steps: list[AgentLoopStep],
        context: dict[str, Any],
        max_depth_level: int,
        tool_error: str | None = None,
    ) -> AgentLoopResult:
        docs_intent_utilization = self._docs_intent_utilization(context=context, trace_steps=trace_steps)
        raw_code_ranking = context.get("tool_first_code_ranking_diagnostics")
        code_ranking_diagnostics = dict(raw_code_ranking) if isinstance(raw_code_ranking, dict) else {}
        requirement_analysis_snapshot: dict[str, Any] = {}
        raw_requirement_analysis = context.get("requirement_analysis")
        if isinstance(raw_requirement_analysis, dict):
            requirement_analysis_snapshot = dict(raw_requirement_analysis)
        else:
            requirement_analysis_snapshot = {
                key: context.get(key) for key in _REQUIREMENT_ANALYSIS_DIAGNOSTIC_KEYS if key in context
            }
        if requirement_analysis_snapshot:
            existing_snapshot = code_ranking_diagnostics.get("requirement_analysis")
            if not isinstance(existing_snapshot, dict) or not existing_snapshot:
                code_ranking_diagnostics["requirement_analysis"] = requirement_analysis_snapshot
        if context.get("control_objective_evidence_gate_applied"):
            code_ranking_diagnostics["evidence_gate"] = {
                "applied": True,
                "control_objective": context.get("control_objective"),
                "required_min_evidence_refs": context.get("required_min_evidence_refs"),
                "required_min_search_patterns": context.get("required_min_search_patterns"),
                "observed_evidence_refs": context.get("observed_evidence_refs"),
                "observed_search_patterns": context.get("observed_search_patterns"),
                "reason_code": context.get("evidence_gate_reason_code"),
            }
        for _p172_key in (
            "skill_first_loaded_at_step",
            "search_pattern_diversity_count",
            "breadth_enforcement_applied",
            "control_objective_evidence_gate_applied",
            "required_min_evidence_refs",
            "required_min_search_patterns",
            "diversity_gate_waived",
            "skill_content_hash",
        ):
            if _p172_key in context:
                code_ranking_diagnostics[_p172_key] = context[_p172_key]
        normalized_max_depth = max_depth_level
        if normalized_max_depth <= 0 and trace_steps:
            normalized_max_depth = max(int(step.depth_level or 1) for step in trace_steps)
        depth_stop_reason = self._resolve_depth_stop_reason(
            context=context,
            termination_reason=termination_reason,
            max_depth_level=normalized_max_depth,
        )
        return AgentLoopResult(
            termination_reason=termination_reason,
            steps_executed=steps_executed,
            budget_remaining=budget_remaining,
            elapsed_seconds=elapsed_seconds,
            evidence_refs=evidence_refs,
            trace_steps=trace_steps,
            tool_error=tool_error,
            docs_intent_utilization=docs_intent_utilization,
            code_ranking_diagnostics=code_ranking_diagnostics,
            project_artifact_refs=list(context.get("project_artifact_refs") or []),
            cross_repo_evidence_refs=list(context.get("cross_repo_evidence_refs") or []),
            config_repo_companion_refs=list(context.get("config_repo_companion_refs") or []),
            prior_knowledge_refs=list(context.get("prior_knowledge_refs") or []),
            max_depth_level=normalized_max_depth,
            depth_stop_reason=depth_stop_reason,
        )
