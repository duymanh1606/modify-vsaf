"""Tests for vds_agent_core.llm.budget."""

from __future__ import annotations

from pathlib import Path

import pytest
from vds_agent_core.llm.budget import (
    BudgetEnforcer,
    BudgetExceededError,
    BudgetLimit,
    BudgetScope,
    BudgetStatus,
    BudgetUsage,
)


class TestBudgetScope:
    """BudgetScope enum has expected members."""

    def test_members(self) -> None:
        assert BudgetScope.REPOSITORY == "repository"
        assert BudgetScope.AUDIT == "audit"
        assert BudgetScope.DAILY == "daily"
        assert BudgetScope.MONTHLY == "monthly"

    def test_is_str_enum(self) -> None:
        assert isinstance(BudgetScope.REPOSITORY, str)


class TestBudgetEnforcerInit:
    """BudgetEnforcer instantiation with default and custom paths."""

    def test_default_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_CONFIG_DIR", raising=False)
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        enforcer = BudgetEnforcer()
        assert enforcer.storage_path == tmp_path / ".vds" / "agent" / "budget.json"

    def test_custom_path(self, tmp_path: Path) -> None:
        custom = tmp_path / "custom" / "budget.json"
        enforcer = BudgetEnforcer(storage_path=custom)
        assert enforcer.storage_path == custom

    def test_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_dir = tmp_path / "override"
        monkeypatch.setenv("VDS_CONFIG_DIR", str(config_dir))
        enforcer = BudgetEnforcer()
        assert enforcer.storage_path == config_dir / "agent" / "budget.json"

    def test_no_limits_by_default(self) -> None:
        enforcer = BudgetEnforcer(storage_path=Path("/dev/null"))
        assert enforcer.limits == {}


class TestRecordCostAndCheckBudget:
    """record_cost and check_budget basic flow."""

    @pytest.fixture()
    def enforcer(self, tmp_path: Path) -> BudgetEnforcer:
        return BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0)],
            storage_path=tmp_path / "budget.json",
            strict=False,
        )

    def test_record_cost_updates_usage(self, enforcer: BudgetEnforcer) -> None:
        updated = enforcer.record_cost(2.50)
        assert len(updated) == 1
        assert updated[0].used_dollars == pytest.approx(2.50)
        assert updated[0].status == BudgetStatus.OK

    def test_check_budget_returns_fresh_when_empty(self, enforcer: BudgetEnforcer) -> None:
        usage = enforcer.check_budget(BudgetScope.DAILY, "2099-01-01")
        assert usage.used_dollars == 0.0
        assert usage.limit_dollars == 10.0
        assert usage.status == BudgetStatus.OK

    def test_warning_threshold(self, enforcer: BudgetEnforcer) -> None:
        enforcer.record_cost(8.50)  # 85% of 10.0
        from datetime import date

        today = date.today().isoformat()
        usage = enforcer.check_budget(BudgetScope.DAILY, today)
        assert usage.status == BudgetStatus.WARNING

    def test_exceeded_strict_raises(self, tmp_path: Path) -> None:
        enforcer = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=1.0)],
            storage_path=tmp_path / "budget.json",
            strict=True,
        )
        with pytest.raises(BudgetExceededError):
            enforcer.record_cost(1.50)

    def test_persistence_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "budget.json"
        e1 = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0)],
            storage_path=path,
            strict=False,
        )
        e1.record_cost(3.0)

        # New enforcer loads from same file
        e2 = BudgetEnforcer(
            limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=10.0)],
            storage_path=path,
            strict=False,
        )
        from datetime import date

        today = date.today().isoformat()
        usage = e2.check_budget(BudgetScope.DAILY, today)
        assert usage.used_dollars == pytest.approx(3.0)


class TestBudgetUsageProperties:
    """BudgetUsage computed properties."""

    def test_remaining(self) -> None:
        usage = BudgetUsage(
            scope=BudgetScope.DAILY,
            scope_id="2026-01-01",
            used_dollars=3.0,
            limit_dollars=10.0,
        )
        assert usage.remaining == pytest.approx(7.0)

    def test_remaining_clamped_to_zero(self) -> None:
        usage = BudgetUsage(
            scope=BudgetScope.DAILY,
            scope_id="2026-01-01",
            used_dollars=15.0,
            limit_dollars=10.0,
        )
        assert usage.remaining == 0.0

    def test_percentage_used(self) -> None:
        usage = BudgetUsage(
            scope=BudgetScope.DAILY,
            scope_id="2026-01-01",
            used_dollars=5.0,
            limit_dollars=10.0,
        )
        assert usage.percentage_used == pytest.approx(50.0)

    def test_percentage_used_zero_limit(self) -> None:
        usage = BudgetUsage(
            scope=BudgetScope.DAILY,
            scope_id="2026-01-01",
            used_dollars=5.0,
            limit_dollars=0.0,
        )
        assert usage.percentage_used == 0.0
