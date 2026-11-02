"""Tests for vds_agent_core.skills.policy — extracted skill policy enforcement."""

from __future__ import annotations

from vds_agent_core.skills.policy import (
    FallbackCandidate,
    FallbackResult,
    SkillExecutionTarget,
    SkillPolicyEnforcer,
    SkillPolicyMode,
    SkillPolicyTelemetryEvent,
    SkillRankingEntry,
    resolve_skill_policy_mode,
)


class TestSkillPolicyEnforcerInstantiation:
    """SkillPolicyEnforcer can be created with various configurations."""

    def test_default_instantiation(self) -> None:
        enforcer = SkillPolicyEnforcer()
        assert enforcer.mode == SkillPolicyMode.STANDARD
        assert enforcer.skills_needed is True

    def test_disabled_when_skills_not_needed(self) -> None:
        enforcer = SkillPolicyEnforcer(skills_needed=False)
        assert enforcer.mode == SkillPolicyMode.DISABLED

    def test_string_mode_coercion(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="permissive")
        assert enforcer.mode == SkillPolicyMode.PERMISSIVE

    def test_invalid_string_mode_falls_back_to_standard(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="bogus")
        assert enforcer.mode == SkillPolicyMode.STANDARD


class TestSkillPolicyModeEnum:
    """SkillPolicyMode enum has the expected canonical members."""

    def test_has_all_canonical_members(self) -> None:
        expected = {"DISABLED", "MINIMAL", "STANDARD", "PERMISSIVE"}
        actual = {m.name for m in SkillPolicyMode}
        assert actual == expected

    def test_values_are_lowercase(self) -> None:
        for member in SkillPolicyMode:
            assert member.value == member.name.lower()

    def test_is_str_enum(self) -> None:
        assert isinstance(SkillPolicyMode.STANDARD, str)
        assert SkillPolicyMode.STANDARD == "standard"


class TestResolveSkillPolicyMode:
    """resolve_skill_policy_mode resolves from multiple input sources."""

    def test_default_returns_minimal(self) -> None:
        result = resolve_skill_policy_mode()
        assert result == SkillPolicyMode.MINIMAL

    def test_skills_needed_false_returns_disabled(self) -> None:
        result = resolve_skill_policy_mode(skills_needed=False)
        assert result == SkillPolicyMode.DISABLED

    def test_mode_override_takes_precedence(self) -> None:
        result = resolve_skill_policy_mode(mode_override="permissive")
        assert result == SkillPolicyMode.PERMISSIVE

    def test_interpretation_skills_needed_false(self) -> None:
        result = resolve_skill_policy_mode(
            interpretation={"skills_needed": False},
        )
        assert result == SkillPolicyMode.DISABLED

    def test_invalid_override_falls_through_to_default(self) -> None:
        result = resolve_skill_policy_mode(mode_override="nonexistent")
        assert result == SkillPolicyMode.MINIMAL


class TestSkillPolicyEnforcerEvaluate:
    """SkillPolicyEnforcer.evaluate() gate decisions for all modes."""

    def test_non_skill_tool_always_allowed(self) -> None:
        enforcer = SkillPolicyEnforcer()
        decision = enforcer.evaluate("search_code")
        assert decision.allowed is True
        assert decision.reason == "not_skill_tool"

    def test_disabled_mode_blocks_all_skill_tools(self) -> None:
        enforcer = SkillPolicyEnforcer(skills_needed=False)
        for tool in ("list_skills", "load_skill", "read_skill_resource", "run_skill_script"):
            decision = enforcer.evaluate(tool)
            assert decision.allowed is False
            assert decision.reason == "skills_disabled_hard_gate"
            assert decision.fallback_message is not None

    def test_permissive_mode_allows_all_skill_tools(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="permissive")
        for tool in ("list_skills", "load_skill", "read_skill_resource", "run_skill_script"):
            decision = enforcer.evaluate(tool)
            assert decision.allowed is True
            assert decision.reason == "permissive_mode"

    def test_standard_mode_allows_all_skill_tools(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="standard")
        for tool in ("list_skills", "load_skill", "read_skill_resource", "run_skill_script"):
            decision = enforcer.evaluate(tool)
            assert decision.allowed is True
            assert decision.reason == "standard_mode_allowed"

    def test_minimal_mode_allows_first_list_skills(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="minimal")
        decision = enforcer.evaluate("list_skills")
        assert decision.allowed is True
        assert decision.reason == "minimal_mode_discovery_allowed"

    def test_minimal_mode_blocks_second_list_skills(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="minimal", max_list_skills_in_minimal=1)
        enforcer.evaluate("list_skills")  # first — allowed
        decision = enforcer.evaluate("list_skills")  # second — blocked
        assert decision.allowed is False
        assert decision.reason == "minimal_mode_discovery_limit"

    def test_minimal_mode_allows_load_skill(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="minimal")
        decision = enforcer.evaluate("load_skill")
        assert decision.allowed is True
        assert "bootstrap" in decision.reason

    def test_minimal_mode_allows_execution_tools(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="minimal")
        for tool in ("read_skill_resource", "run_skill_script"):
            decision = enforcer.evaluate(tool)
            assert decision.allowed is True
            assert "execution" in decision.reason

    def test_state_tracks_blocked_calls(self) -> None:
        enforcer = SkillPolicyEnforcer(skills_needed=False)
        enforcer.evaluate("list_skills")
        enforcer.evaluate("load_skill")
        assert enforcer.state.blocked_calls == 2
        assert enforcer.state.total_skill_calls == 2

    def test_state_tracks_execution_count(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="standard")
        enforcer.evaluate("read_skill_resource")
        enforcer.evaluate("run_skill_script")
        assert enforcer.state.execution_count == 2

    def test_reset_state_clears_counters(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="standard")
        enforcer.evaluate("load_skill")
        enforcer.evaluate("read_skill_resource")
        enforcer.reset_state()
        assert enforcer.state.total_skill_calls == 0
        assert enforcer.state.execution_count == 0


class TestAttemptFallback:
    """SkillPolicyEnforcer.attempt_fallback() bounded expansion."""

    def _make_entry(self, name: str, score: float) -> SkillRankingEntry:
        return SkillRankingEntry(
            skill_name=name,
            execution_count=1,
            success_count=1,
            effectiveness_score=score,
            rationale="high_effectiveness",
        )

    def test_no_candidates_returns_triggered_failure(self) -> None:
        enforcer = SkillPolicyEnforcer()
        result = enforcer.attempt_fallback("skill_a", [])
        assert result.triggered is True
        assert result.success is False
        assert result.candidate_count == 0

    def test_dry_run_returns_candidates_without_executing(self) -> None:
        enforcer = SkillPolicyEnforcer()
        candidates = [self._make_entry("skill_b", 0.9), self._make_entry("skill_c", 0.7)]
        result = enforcer.attempt_fallback("skill_a", candidates, execute_fn=None)
        assert result.triggered is True
        assert result.candidate_count == 2
        assert result.success is False
        assert all(not c.success for c in result.candidates_tried)

    def test_execute_fn_called_and_success_stops_early(self) -> None:
        enforcer = SkillPolicyEnforcer()
        calls: list[str] = []

        def execute(name: str) -> bool:
            calls.append(name)
            return name == "skill_b"

        candidates = [self._make_entry("skill_b", 0.9), self._make_entry("skill_c", 0.7)]
        result = enforcer.attempt_fallback("skill_a", candidates, execute_fn=execute)
        assert result.success is True
        assert len(calls) == 1  # stopped after first success
        assert calls[0] == "skill_b"

    def test_primary_skill_excluded_from_candidates(self) -> None:
        enforcer = SkillPolicyEnforcer()
        candidates = [self._make_entry("skill_a", 0.9), self._make_entry("skill_b", 0.8)]
        result = enforcer.attempt_fallback("skill_a", candidates, execute_fn=None)
        assert all(c.skill_name != "skill_a" for c in result.candidates_tried)

    def test_max_fallback_candidates_respected(self) -> None:
        enforcer = SkillPolicyEnforcer()
        candidates = [self._make_entry(f"skill_{i}", float(i) / 10) for i in range(5, 0, -1)]
        result = enforcer.attempt_fallback("skill_x", candidates, execute_fn=None, max_fallback_candidates=2)
        assert result.candidate_count == 2

    def test_candidate_names_property(self) -> None:
        enforcer = SkillPolicyEnforcer()
        candidates = [self._make_entry("skill_b", 0.9)]
        result = enforcer.attempt_fallback("skill_a", candidates, execute_fn=None)
        assert result.candidate_names == ["skill_b"]


class TestCheckExecutionCompliance:
    """SkillPolicyEnforcer.check_execution_compliance() FR-199."""

    def test_empty_targets_is_compliant(self) -> None:
        result = SkillPolicyEnforcer.check_execution_compliance([])
        assert result.compliant is True
        assert result.total_targets == 0

    def test_all_executed_is_compliant(self) -> None:
        targets = [
            SkillExecutionTarget("docs", "ref_1", executed=True),
            SkillExecutionTarget("code", "ref_2", executed=True),
        ]
        result = SkillPolicyEnforcer.check_execution_compliance(targets)
        assert result.compliant is True
        assert result.executed_targets == 2
        assert result.skipped_targets == 0

    def test_skipped_with_reason_is_compliant(self) -> None:
        targets = [
            SkillExecutionTarget("docs", "ref_1", executed=False, skip_reason="not_applicable"),
        ]
        result = SkillPolicyEnforcer.check_execution_compliance(targets)
        assert result.compliant is True
        assert result.skipped_without_reason == 0

    def test_skipped_without_reason_is_noncompliant(self) -> None:
        targets = [
            SkillExecutionTarget("docs", "ref_1", executed=False),
        ]
        result = SkillPolicyEnforcer.check_execution_compliance(targets)
        assert result.compliant is False
        assert result.skipped_without_reason == 1

    def test_details_populated(self) -> None:
        targets = [
            SkillExecutionTarget("docs", "ref_1", executed=True),
            SkillExecutionTarget("code", "ref_2", executed=False, skip_reason="irrelevant"),
        ]
        result = SkillPolicyEnforcer.check_execution_compliance(targets)
        assert len(result.details) == 2
        assert result.details[0]["executed"] is True
        assert result.details[1]["skip_reason"] == "irrelevant"


class TestRankSkillEffectiveness:
    """SkillPolicyEnforcer.rank_skill_effectiveness() FR-200."""

    def test_empty_log_returns_empty(self) -> None:
        assert SkillPolicyEnforcer.rank_skill_effectiveness([]) == []

    def test_entries_without_skill_name_skipped(self) -> None:
        log = [{"success": True}, {"skill_name": "", "success": True}]
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result == []

    def test_high_effectiveness(self) -> None:
        log = [{"skill_name": "skill_a", "success": True}] * 5
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result[0].rationale == "high_effectiveness"
        assert result[0].effectiveness_score == 1.0

    def test_moderate_effectiveness(self) -> None:
        log = [
            {"skill_name": "skill_a", "success": True},
            {"skill_name": "skill_a", "success": False},
        ]
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result[0].rationale == "moderate_effectiveness"
        assert result[0].effectiveness_score == 0.5

    def test_low_effectiveness(self) -> None:
        log = [
            {"skill_name": "skill_a", "success": True},
            {"skill_name": "skill_a", "success": False},
            {"skill_name": "skill_a", "success": False},
            {"skill_name": "skill_a", "success": False},
        ]
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result[0].rationale == "low_effectiveness"

    def test_no_successful_executions(self) -> None:
        log = [{"skill_name": "skill_a", "success": False}] * 3
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result[0].rationale == "no_successful_executions"
        assert result[0].effectiveness_score == 0.0

    def test_sorted_by_score_descending(self) -> None:
        log = [
            {"skill_name": "skill_low", "success": False},
            {"skill_name": "skill_high", "success": True},
        ]
        result = SkillPolicyEnforcer.rank_skill_effectiveness(log)
        assert result[0].skill_name == "skill_high"
        assert result[1].skill_name == "skill_low"


class TestBuildTelemetryEvent:
    """SkillPolicyEnforcer.build_telemetry_event() FR-198, FR-226."""

    def test_basic_event_fields(self) -> None:
        enforcer = SkillPolicyEnforcer(mode="standard")
        enforcer.evaluate("load_skill")
        event = enforcer.build_telemetry_event(row_index=3, check_id="CL-001")
        assert event.row_index == 3
        assert event.check_id == "CL-001"
        assert event.mode == "standard"
        assert event.load_skill_count == 1

    def test_fallback_fields_when_triggered(self) -> None:
        enforcer = SkillPolicyEnforcer()
        fb = FallbackResult(
            triggered=True,
            candidates_tried=[
                FallbackCandidate("skill_b", 0.9, success=True),
            ],
            success=True,
            primary_skill="skill_a",
        )
        event = enforcer.build_telemetry_event(fallback_result=fb)
        assert event.fallback_triggered is True
        assert event.fallback_success is True
        assert event.fallback_candidate_count == 1
        assert "skill_b" in event.fallback_candidates

    def test_fallback_not_triggered_omits_fields(self) -> None:
        enforcer = SkillPolicyEnforcer()
        event = enforcer.build_telemetry_event()
        assert event.fallback_triggered is False

    def test_to_dict_includes_fallback_when_triggered(self) -> None:
        enforcer = SkillPolicyEnforcer()
        fb = FallbackResult(triggered=True, success=False, primary_skill="skill_a")
        event = enforcer.build_telemetry_event(fallback_result=fb)
        d = event.to_dict()
        assert d["fallback_triggered"] is True

    def test_to_dict_excludes_fallback_when_not_triggered(self) -> None:
        enforcer = SkillPolicyEnforcer()
        event = enforcer.build_telemetry_event()
        d = event.to_dict()
        assert "fallback_triggered" not in d

    def test_effectiveness_rankings_serialized(self) -> None:
        enforcer = SkillPolicyEnforcer()
        rankings = [
            SkillRankingEntry("skill_a", 5, 4, 0.8, "high_effectiveness"),
        ]
        event = enforcer.build_telemetry_event(effectiveness_rankings=rankings)
        assert len(event.effectiveness_rankings) == 1
        assert event.effectiveness_rankings[0]["skill_name"] == "skill_a"

    def test_degraded_fields(self) -> None:
        enforcer = SkillPolicyEnforcer()
        event = enforcer.build_telemetry_event(is_degraded=True, degraded_reason="timeout")
        assert event.is_degraded is True
        assert event.degraded_reason == "timeout"


class TestSkillPolicyTelemetryEventToDict:
    """SkillPolicyTelemetryEvent.to_dict() serialization."""

    def test_optional_fields_omitted_when_none(self) -> None:
        event = SkillPolicyTelemetryEvent()
        d = event.to_dict()
        assert "row_index" not in d
        assert "check_id" not in d
        assert "first_execution_at_call" not in d
        assert "degraded_reason" not in d

    def test_optional_fields_included_when_set(self) -> None:
        event = SkillPolicyTelemetryEvent(
            row_index=1,
            check_id="CL-002",
            first_execution_at_call=3,
            degraded_reason="stale_cache",
        )
        d = event.to_dict()
        assert d["row_index"] == 1
        assert d["check_id"] == "CL-002"
        assert d["first_execution_at_call"] == 3
        assert d["degraded_reason"] == "stale_cache"
