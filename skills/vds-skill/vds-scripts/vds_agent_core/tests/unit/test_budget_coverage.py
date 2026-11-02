"""Coverage uplift for vds_agent_core.llm.budget (W5.4).

Targets the uncovered lines in BudgetEnforcer:
- set_limit (line 142)
- repository + audit scope in record_cost (lines 172-177, 181-186)
- monthly scope in record_cost (lines 200-206)
- reset_usage scope-only and key-specific paths (lines 256-267)
- on_critical / on_exceeded callbacks (lines 299, 303-305)
- on_warning callback (line 309)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from vds_agent_core.llm.budget import (
    BudgetEnforcer,
    BudgetExceededError,
    BudgetLimit,
    BudgetScope,
    BudgetStatus,
    BudgetUsage,
)


@pytest.fixture()
def budget_path(tmp_path: Path) -> Path:
    return tmp_path / "budget.json"


class TestSetLimit:
    """BudgetEnforcer.set_limit — line 142."""

    def test_set_limit_adds_scope(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(storage_path=budget_path)
        enforcer.set_limit(BudgetScope.DAILY, 5.0, warning_threshold=0.7, critical_threshold=0.9)
        assert BudgetScope.DAILY in enforcer.limits
        limit = enforcer.limits[BudgetScope.DAILY]
        assert limit.limit_dollars == pytest.approx(5.0)
        assert limit.warning_threshold == pytest.approx(0.7)
        assert limit.critical_threshold == pytest.approx(0.9)

    def test_set_limit_replaces_existing(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0)],
            storage_path=budget_path,
        )
        enforcer.set_limit(BudgetScope.DAILY, 20.0)
        assert enforcer.limits[BudgetScope.DAILY].limit_dollars == pytest.approx(20.0)


class TestRecordCostRepositoryAndAuditScopes:
    """record_cost repository + audit branches (lines 172-186)."""

    def test_repository_scope_recorded(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.REPOSITORY, limit_dollars=50.0)],
            storage_path=budget_path,
            strict=False,
        )
        updated = enforcer.record_cost(5.0, repository="my-repo")
        assert len(updated) == 1
        assert updated[0].scope == BudgetScope.REPOSITORY
        assert updated[0].scope_id == "my-repo"
        assert updated[0].used_dollars == pytest.approx(5.0)

    def test_audit_scope_recorded(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.AUDIT, limit_dollars=20.0)],
            storage_path=budget_path,
            strict=False,
        )
        updated = enforcer.record_cost(3.0, audit_id="audit-42")
        assert len(updated) == 1
        assert updated[0].scope == BudgetScope.AUDIT
        assert updated[0].scope_id == "audit-42"

    def test_repository_not_recorded_when_no_limit(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(storage_path=budget_path)
        updated = enforcer.record_cost(1.0, repository="repo-without-limit")
        assert updated == []

    def test_audit_not_recorded_when_no_limit(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(storage_path=budget_path)
        updated = enforcer.record_cost(1.0, audit_id="audit-without-limit")
        assert updated == []

    def test_all_four_scopes_recorded_together(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[
                BudgetLimit(scope=BudgetScope.REPOSITORY, limit_dollars=100.0),
                BudgetLimit(scope=BudgetScope.AUDIT, limit_dollars=50.0),
                BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=20.0),
                BudgetLimit(scope=BudgetScope.MONTHLY, limit_dollars=200.0),
            ],
            storage_path=budget_path,
            strict=False,
        )
        updated = enforcer.record_cost(2.0, repository="repo-x", audit_id="audit-y")
        scopes = {u.scope for u in updated}
        assert BudgetScope.REPOSITORY in scopes
        assert BudgetScope.AUDIT in scopes
        assert BudgetScope.DAILY in scopes
        assert BudgetScope.MONTHLY in scopes


class TestRecordCostMonthlyScope:
    """monthly scope in record_cost (lines 200-206)."""

    def test_monthly_scope_recorded(self, budget_path: Path) -> None:
        from datetime import date

        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.MONTHLY, limit_dollars=100.0)],
            storage_path=budget_path,
            strict=False,
        )
        updated = enforcer.record_cost(7.5)
        assert len(updated) == 1
        assert updated[0].scope == BudgetScope.MONTHLY
        month = date.today().strftime("%Y-%m")
        assert updated[0].scope_id == month


class TestResetUsage:
    """reset_usage scope-only and key-specific paths (lines 256-267)."""

    @pytest.fixture()
    def populated_enforcer(self, budget_path: Path) -> BudgetEnforcer:
        enforcer = BudgetEnforcer(
            limits=[
                BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0),
                BudgetLimit(scope=BudgetScope.REPOSITORY, limit_dollars=50.0),
            ],
            storage_path=budget_path,
            strict=False,
        )
        enforcer.record_cost(1.0, repository="repo-a")
        enforcer.record_cost(2.0, repository="repo-b")
        enforcer.record_cost(3.0)
        return enforcer

    def test_reset_all(self, populated_enforcer: BudgetEnforcer) -> None:
        assert len(populated_enforcer._usage) > 0
        populated_enforcer.reset_usage()
        assert populated_enforcer._usage == {}

    def test_reset_scope_only_clears_matching_keys(self, populated_enforcer: BudgetEnforcer) -> None:
        populated_enforcer.reset_usage(scope=BudgetScope.REPOSITORY)
        remaining_scopes = {u.scope for u in populated_enforcer._usage.values()}
        assert BudgetScope.REPOSITORY not in remaining_scopes
        assert BudgetScope.DAILY in remaining_scopes

    def test_reset_specific_scope_id(self, populated_enforcer: BudgetEnforcer) -> None:
        key_before = "repository:repo-a"
        assert key_before in populated_enforcer._usage
        populated_enforcer.reset_usage(scope=BudgetScope.REPOSITORY, scope_id="repo-a")
        assert key_before not in populated_enforcer._usage
        # repo-b should still be present
        assert "repository:repo-b" in populated_enforcer._usage

    def test_reset_nonexistent_key_is_noop(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(storage_path=budget_path)
        enforcer.reset_usage(scope=BudgetScope.DAILY, scope_id="2099-12-31")
        # Should not raise


class TestCallbacks:
    """on_warning, on_critical, on_exceeded callbacks (lines 299, 303-305, 309)."""

    def test_on_warning_called_at_warning_threshold(self, budget_path: Path) -> None:
        on_warning = MagicMock()
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0, warning_threshold=0.8)],
            storage_path=budget_path,
            on_warning=on_warning,
            strict=False,
        )
        enforcer.record_cost(8.5)  # 85% → warning
        on_warning.assert_called_once()
        call_arg = on_warning.call_args[0][0]
        assert isinstance(call_arg, BudgetUsage)
        assert call_arg.status == BudgetStatus.WARNING

    def test_on_critical_called_at_critical_threshold(self, budget_path: Path) -> None:
        on_critical = MagicMock()
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0, critical_threshold=0.9)],
            storage_path=budget_path,
            on_critical=on_critical,
            strict=False,
        )
        enforcer.record_cost(9.5)  # 95% → critical
        on_critical.assert_called_once()
        call_arg = on_critical.call_args[0][0]
        assert call_arg.status == BudgetStatus.CRITICAL

    def test_on_exceeded_called_before_raise(self, budget_path: Path) -> None:
        on_exceeded = MagicMock()
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=1.0)],
            storage_path=budget_path,
            on_exceeded=on_exceeded,
            strict=True,
        )
        with pytest.raises(BudgetExceededError):
            enforcer.record_cost(2.0)
        on_exceeded.assert_called_once()

    def test_on_exceeded_no_raise_when_not_strict(self, budget_path: Path) -> None:
        on_exceeded = MagicMock()
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=1.0)],
            storage_path=budget_path,
            on_exceeded=on_exceeded,
            strict=False,
        )
        enforcer.record_cost(2.0)  # should not raise
        on_exceeded.assert_called_once()


class TestGetSummary:
    """get_summary returns copy of usage dict (line 243)."""

    def test_get_summary_returns_all_usages(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[
                BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0),
                BudgetLimit(scope=BudgetScope.REPOSITORY, limit_dollars=50.0),
            ],
            storage_path=budget_path,
            strict=False,
        )
        enforcer.record_cost(2.0, repository="repo-z")
        summary = enforcer.get_summary()
        assert isinstance(summary, dict)
        assert len(summary) >= 2
        assert any(u.scope == BudgetScope.DAILY for u in summary.values())

    def test_get_summary_is_copy(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(storage_path=budget_path)
        summary = enforcer.get_summary()
        summary["fake-key"] = None  # mutating the copy should not affect internal state
        assert "fake-key" not in enforcer._usage


class TestCheckBudgetTrackingOnly:
    """check_budget tracking_only path (line 230-238)."""

    def test_tracking_only_returns_ok_status(self, budget_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=1.0)],
            storage_path=budget_path,
            tracking_only=True,
        )
        enforcer.record_cost(5.0)  # would be EXCEEDED normally
        from datetime import date

        today = date.today().isoformat()
        usage = enforcer.check_budget(BudgetScope.DAILY, today)
        assert usage.status == BudgetStatus.OK
        assert usage.used_dollars == pytest.approx(5.0)
