"""Skill policy enforcement and telemetry for agentic analysis (FR-194..FR-200, FR-226).

Provides:
- SkillPolicyMode: canonical modes (disabled/minimal/standard/permissive)
- SkillPolicyEnforcer: per-row gate enforcement engine
- SkillPolicyTelemetryEvent: per-row structured telemetry emission
- ExecutionComplianceResult: docs/code target compliance gate (FR-199)
- SkillRankingEntry: effectiveness-driven ranking diagnostics (FR-200)
- FallbackResult: bounded fallback expansion result (FR-226)
- resolve_skill_policy_mode: mode resolution from interpretation/overrides
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class SkillPolicyMode(StrEnum):
    """Canonical skill policy modes (FR-195).

    - disabled: All skill tool calls blocked (skills_needed=false hard-gate).
    - minimal: Execution-first — list_skills suppressed after first call,
               load_skill + read_skill_resource/run_skill_script allowed.
    - standard: Normal skill access with policy enforcement.
    - permissive: All skill tools enabled without restriction.
    """

    DISABLED = "disabled"
    MINIMAL = "minimal"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


# Tool name sets for gate decisions
_SKILL_DISCOVERY_TOOLS: frozenset[str] = frozenset({"list_skills"})
_SKILL_BOOTSTRAP_TOOLS: frozenset[str] = frozenset({"load_skill"})
_SKILL_EXECUTION_TOOLS: frozenset[str] = frozenset({"read_skill_resource", "run_skill_script"})
_ALL_SKILL_TOOLS: frozenset[str] = _SKILL_DISCOVERY_TOOLS | _SKILL_BOOTSTRAP_TOOLS | _SKILL_EXECUTION_TOOLS


@dataclass(frozen=True)
class SkillGateDecision:
    """Result of applying skill policy gate to a tool call."""

    allowed: bool
    reason: str
    mode: SkillPolicyMode
    tool_name: str
    fallback_message: str | None = None


@dataclass
class SkillPolicyState:
    """Mutable per-row state tracking for skill policy enforcement."""

    mode: SkillPolicyMode = SkillPolicyMode.STANDARD
    skills_needed: bool = True
    list_skills_count: int = 0
    load_skill_count: int = 0
    execution_count: int = 0
    total_skill_calls: int = 0
    blocked_calls: int = 0
    first_execution_at_call: int | None = None

    def record_call(self, tool_name: str, *, allowed: bool) -> None:
        """Record a skill tool call for state tracking."""
        self.total_skill_calls += 1
        if not allowed:
            self.blocked_calls += 1
            return
        if tool_name in _SKILL_DISCOVERY_TOOLS:
            self.list_skills_count += 1
        elif tool_name in _SKILL_BOOTSTRAP_TOOLS:
            self.load_skill_count += 1
        elif tool_name in _SKILL_EXECUTION_TOOLS:
            self.execution_count += 1
            if self.first_execution_at_call is None:
                self.first_execution_at_call = self.total_skill_calls


@dataclass(frozen=True)
class SkillExecutionTarget:
    """A docs or code target that requires skill execution (FR-199)."""

    target_type: Literal["docs", "code"]
    target_ref: str
    executed: bool = False
    skip_reason: str | None = None


@dataclass
class ExecutionComplianceResult:
    """Result of docs/code target execution compliance check (FR-199)."""

    compliant: bool
    total_targets: int = 0
    executed_targets: int = 0
    skipped_targets: int = 0
    skipped_without_reason: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class SkillRankingEntry:
    """Effectiveness-driven skill ranking entry (FR-200)."""

    skill_name: str
    execution_count: int
    success_count: int
    effectiveness_score: float
    rationale: str


@dataclass(frozen=True)
class FallbackCandidate:
    """A single fallback candidate and its execution outcome (FR-226)."""

    skill_name: str
    objective_fit_score: float
    success: bool


@dataclass
class FallbackResult:
    """Result of bounded fallback skill expansion (FR-226).

    Tracks which candidates were tried, whether any succeeded, and
    provides structured data for telemetry emission.
    """

    triggered: bool = False
    candidates_tried: list[FallbackCandidate] = field(default_factory=list)
    success: bool = False
    primary_skill: str | None = None

    @property
    def candidate_count(self) -> int:
        return len(self.candidates_tried)

    @property
    def candidate_names(self) -> list[str]:
        return [c.skill_name for c in self.candidates_tried]


@dataclass
class SkillPolicyTelemetryEvent:
    """Per-row skill policy telemetry event (FR-198, FR-226)."""

    row_index: int | None = None
    check_id: str | None = None
    mode: str = "standard"
    skills_needed: bool = True
    total_skill_calls: int = 0
    blocked_calls: int = 0
    list_skills_count: int = 0
    load_skill_count: int = 0
    execution_count: int = 0
    first_execution_at_call: int | None = None
    is_timeout: bool = False
    is_degraded: bool = False
    degraded_reason: str | None = None
    effectiveness_rankings: list[dict[str, Any]] = field(default_factory=list)
    # FR-226: Fallback telemetry fields
    fallback_triggered: bool = False
    fallback_candidate_count: int = 0
    fallback_success: bool = False
    fallback_candidates: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to structured log payload."""
        result: dict[str, Any] = {
            "event": "skill_policy_row_telemetry",
            "mode": self.mode,
            "skills_needed": self.skills_needed,
            "total_skill_calls": self.total_skill_calls,
            "blocked_calls": self.blocked_calls,
            "list_skills_count": self.list_skills_count,
            "load_skill_count": self.load_skill_count,
            "execution_count": self.execution_count,
            "is_timeout": self.is_timeout,
            "is_degraded": self.is_degraded,
            "timestamp": self.timestamp,
        }
        if self.row_index is not None:
            result["row_index"] = self.row_index
        if self.check_id is not None:
            result["check_id"] = self.check_id
        if self.first_execution_at_call is not None:
            result["first_execution_at_call"] = self.first_execution_at_call
        if self.degraded_reason:
            result["degraded_reason"] = self.degraded_reason
        if self.effectiveness_rankings:
            result["effectiveness_rankings"] = self.effectiveness_rankings
        # FR-226: Include fallback fields when triggered
        if self.fallback_triggered:
            result["fallback_triggered"] = self.fallback_triggered
            result["fallback_candidate_count"] = self.fallback_candidate_count
            result["fallback_success"] = self.fallback_success
            result["fallback_candidates"] = self.fallback_candidates
        return result


class SkillPolicyEnforcer:
    """Central skill policy enforcement engine (FR-194..FR-200).

    Created per-row (or per-workflow) and tracks skill tool call state to
    enforce the active policy mode.  The ``evaluate()`` method is the
    single entry-point for every skill tool call gate decision.
    """

    def __init__(
        self,
        *,
        mode: SkillPolicyMode | str = SkillPolicyMode.STANDARD,
        skills_needed: bool = True,
        max_list_skills_in_minimal: int = 1,
    ) -> None:
        if isinstance(mode, str):
            try:
                mode = SkillPolicyMode(mode.lower())
            except ValueError:
                mode = SkillPolicyMode.STANDARD

        # FR-194: skills_needed=false forces disabled mode
        if not skills_needed:
            mode = SkillPolicyMode.DISABLED

        self._mode = mode
        self._skills_needed = skills_needed
        self._max_list_skills_in_minimal = max(0, max_list_skills_in_minimal)
        self._state = SkillPolicyState(mode=mode, skills_needed=skills_needed)

    @property
    def mode(self) -> SkillPolicyMode:
        return self._mode

    @property
    def skills_needed(self) -> bool:
        return self._skills_needed

    @property
    def state(self) -> SkillPolicyState:
        return self._state

    def reset_state(self) -> None:
        """Reset per-row state for a new row evaluation."""
        self._state = SkillPolicyState(mode=self._mode, skills_needed=self._skills_needed)

    def evaluate(self, tool_name: str) -> SkillGateDecision:
        """Evaluate whether a skill tool call is allowed under current policy."""
        if tool_name not in _ALL_SKILL_TOOLS:
            return SkillGateDecision(
                allowed=True,
                reason="not_skill_tool",
                mode=self._mode,
                tool_name=tool_name,
            )

        if self._mode == SkillPolicyMode.DISABLED:
            decision = SkillGateDecision(
                allowed=False,
                reason="skills_disabled_hard_gate",
                mode=self._mode,
                tool_name=tool_name,
                fallback_message=(
                    "[skill-policy-blocked] Skills are disabled for this row "
                    "(skills_needed=false). Use search_docs, search_code, "
                    "read_doc_chunk, or read_code_file instead."
                ),
            )
            self._state.record_call(tool_name, allowed=False)
            return decision

        if self._mode == SkillPolicyMode.PERMISSIVE:
            self._state.record_call(tool_name, allowed=True)
            return SkillGateDecision(
                allowed=True,
                reason="permissive_mode",
                mode=self._mode,
                tool_name=tool_name,
            )

        if self._mode == SkillPolicyMode.MINIMAL:
            return self._evaluate_minimal(tool_name)

        # STANDARD mode
        self._state.record_call(tool_name, allowed=True)
        return SkillGateDecision(
            allowed=True,
            reason="standard_mode_allowed",
            mode=self._mode,
            tool_name=tool_name,
        )

    def _evaluate_minimal(self, tool_name: str) -> SkillGateDecision:
        """Minimal mode: execution-first policy (FR-195)."""
        if tool_name in _SKILL_DISCOVERY_TOOLS:
            if self._state.list_skills_count >= self._max_list_skills_in_minimal:
                decision = SkillGateDecision(
                    allowed=False,
                    reason="minimal_mode_discovery_limit",
                    mode=self._mode,
                    tool_name=tool_name,
                    fallback_message=(
                        "[skill-policy-blocked] Discovery call limit reached "
                        "in minimal mode. Proceed directly to load_skill "
                        "with a known skill name."
                    ),
                )
                self._state.record_call(tool_name, allowed=False)
                return decision
            self._state.record_call(tool_name, allowed=True)
            return SkillGateDecision(
                allowed=True,
                reason="minimal_mode_discovery_allowed",
                mode=self._mode,
                tool_name=tool_name,
            )

        # Bootstrap and execution tools always allowed in minimal mode
        self._state.record_call(tool_name, allowed=True)
        category = "bootstrap" if tool_name in _SKILL_BOOTSTRAP_TOOLS else "execution"
        return SkillGateDecision(
            allowed=True,
            reason=f"minimal_mode_{category}_allowed",
            mode=self._mode,
            tool_name=tool_name,
        )

    def attempt_fallback(
        self,
        primary_skill: str,
        available_skills: list[SkillRankingEntry],
        execute_fn: Any | None = None,
        *,
        max_fallback_candidates: int = 2,
    ) -> FallbackResult:
        """Attempt bounded fallback expansion when primary skill fails (FR-226).

        Selects up to ``max_fallback_candidates`` from ``available_skills``
        ranked by ``effectiveness_score``, excluding the already-attempted
        primary skill.  If ``execute_fn`` is provided, it is called with
        each candidate's ``skill_name`` and must return a bool indicating
        success.  On first success the expansion stops early.

        When ``execute_fn`` is ``None`` the method returns candidates that
        *would* be tried without executing them (dry-run mode).
        """
        # Filter out primary skill and sort by effectiveness descending
        candidates = [s for s in available_skills if s.skill_name != primary_skill]
        candidates.sort(key=lambda s: (-s.effectiveness_score, s.skill_name))
        candidates = candidates[: max(0, max_fallback_candidates)]

        if not candidates:
            return FallbackResult(
                triggered=True,
                success=False,
                primary_skill=primary_skill,
            )

        tried: list[FallbackCandidate] = []
        overall_success = False

        for candidate in candidates:
            if execute_fn is not None:
                success = bool(execute_fn(candidate.skill_name))
            else:
                # Dry-run: mark as not-executed
                success = False

            tried.append(
                FallbackCandidate(
                    skill_name=candidate.skill_name,
                    objective_fit_score=candidate.effectiveness_score,
                    success=success,
                )
            )

            if success:
                overall_success = True
                break

        return FallbackResult(
            triggered=True,
            candidates_tried=tried,
            success=overall_success,
            primary_skill=primary_skill,
        )

    def build_telemetry_event(
        self,
        *,
        row_index: int | None = None,
        check_id: str | None = None,
        is_timeout: bool = False,
        is_degraded: bool = False,
        degraded_reason: str | None = None,
        effectiveness_rankings: list[SkillRankingEntry] | None = None,
        fallback_result: FallbackResult | None = None,
    ) -> SkillPolicyTelemetryEvent:
        """Build per-row telemetry event from current state (FR-198, FR-226)."""
        rankings_dicts: list[dict[str, Any]] = []
        if effectiveness_rankings:
            for entry in effectiveness_rankings:
                rankings_dicts.append(
                    {
                        "skill_name": entry.skill_name,
                        "execution_count": entry.execution_count,
                        "success_count": entry.success_count,
                        "effectiveness_score": round(entry.effectiveness_score, 4),
                        "rationale": entry.rationale,
                    }
                )

        # FR-226: Wire fallback telemetry from FallbackResult
        fb_triggered = False
        fb_candidate_count = 0
        fb_success = False
        fb_candidates: list[str] = []
        if fallback_result is not None and fallback_result.triggered:
            fb_triggered = True
            fb_candidate_count = fallback_result.candidate_count
            fb_success = fallback_result.success
            fb_candidates = fallback_result.candidate_names

        return SkillPolicyTelemetryEvent(
            row_index=row_index,
            check_id=check_id,
            mode=self._mode.value,
            skills_needed=self._skills_needed,
            total_skill_calls=self._state.total_skill_calls,
            blocked_calls=self._state.blocked_calls,
            list_skills_count=self._state.list_skills_count,
            load_skill_count=self._state.load_skill_count,
            execution_count=self._state.execution_count,
            first_execution_at_call=self._state.first_execution_at_call,
            is_timeout=is_timeout,
            is_degraded=is_degraded,
            degraded_reason=degraded_reason,
            effectiveness_rankings=rankings_dicts,
            fallback_triggered=fb_triggered,
            fallback_candidate_count=fb_candidate_count,
            fallback_success=fb_success,
            fallback_candidates=fb_candidates,
        )

    @staticmethod
    def check_execution_compliance(
        targets: list[SkillExecutionTarget],
    ) -> ExecutionComplianceResult:
        """Check docs/code target execution compliance (FR-199).

        Every skipped target MUST have an explicit ``skip_reason``.
        Returns ``compliant=False`` when any skipped target lacks a reason.
        """
        if not targets:
            return ExecutionComplianceResult(compliant=True)

        total = len(targets)
        executed = sum(1 for t in targets if t.executed)
        skipped = total - executed
        skipped_without_reason = sum(1 for t in targets if not t.executed and not t.skip_reason)

        details: list[dict[str, Any]] = []
        for t in targets:
            entry: dict[str, Any] = {
                "target_type": t.target_type,
                "target_ref": t.target_ref,
                "executed": t.executed,
            }
            if not t.executed:
                entry["skip_reason"] = t.skip_reason or None
            details.append(entry)

        return ExecutionComplianceResult(
            compliant=skipped_without_reason == 0,
            total_targets=total,
            executed_targets=executed,
            skipped_targets=skipped,
            skipped_without_reason=skipped_without_reason,
            details=details,
        )

    @staticmethod
    def rank_skill_effectiveness(
        skill_execution_log: list[dict[str, Any]],
    ) -> list[SkillRankingEntry]:
        """Rank skills by effectiveness from execution log (FR-200).

        Aggregates execution results by skill name and computes an
        effectiveness score (success_count / execution_count).
        """
        if not skill_execution_log:
            return []

        stats: dict[str, dict[str, int]] = {}
        for entry in skill_execution_log:
            name = str(entry.get("skill_name", "") or "").strip()
            if not name:
                continue
            if name not in stats:
                stats[name] = {"executions": 0, "successes": 0}
            stats[name]["executions"] += 1
            if entry.get("success", False):
                stats[name]["successes"] += 1

        rankings: list[SkillRankingEntry] = []
        for skill_name, counts in sorted(stats.items()):
            executions = counts["executions"]
            successes = counts["successes"]
            score = successes / executions if executions > 0 else 0.0

            if score >= 0.8:
                rationale = "high_effectiveness"
            elif score >= 0.5:
                rationale = "moderate_effectiveness"
            elif score > 0.0:
                rationale = "low_effectiveness"
            else:
                rationale = "no_successful_executions"

            rankings.append(
                SkillRankingEntry(
                    skill_name=skill_name,
                    execution_count=executions,
                    success_count=successes,
                    effectiveness_score=score,
                    rationale=rationale,
                )
            )

        rankings.sort(key=lambda r: (-r.effectiveness_score, r.skill_name))
        return rankings


def resolve_skill_policy_mode(
    *,
    skills_needed: bool | None = None,
    mode_override: str | None = None,
    interpretation: dict[str, Any] | None = None,
) -> SkillPolicyMode:
    """Resolve the effective skill policy mode from inputs.

    Priority:
    1. skills_needed is explicitly False → DISABLED
    2. mode_override is set → use that mode
    3. interpretation has skills_needed=false → DISABLED
    4. Default → MINIMAL (canonical default per FR-195)
    """
    if skills_needed is False:
        return SkillPolicyMode.DISABLED

    if mode_override:
        try:
            return SkillPolicyMode(mode_override.lower())
        except ValueError:
            pass

    if isinstance(interpretation, dict):
        interp_skills_needed = interpretation.get("skills_needed")
        if interp_skills_needed is False:
            return SkillPolicyMode.DISABLED

    return SkillPolicyMode.MINIMAL
