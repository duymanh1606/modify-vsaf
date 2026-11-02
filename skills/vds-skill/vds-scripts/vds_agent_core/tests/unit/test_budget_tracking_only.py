"""Tests for BudgetEnforcer tracking_only mode (FR-A3)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from vds_agent_core.llm.budget import (
    BudgetEnforcer,
    BudgetLimit,
    BudgetScope,
    BudgetStatus,
)


@pytest.fixture()
def tracking_enforcer(tmp_path: Path) -> BudgetEnforcer:
    """BudgetEnforcer in tracking_only mode with a low daily limit."""
    return BudgetEnforcer(
        limits=[BudgetLimit(scope=BudgetScope.DAILY, limit_dollars=1.00)],
        storage_path=tmp_path / "budget.json",
        on_warning=MagicMock(),
        on_critical=MagicMock(),
        on_exceeded=MagicMock(),
        tracking_only=True,
    )


class TestBudgetTrackingOnly:
    """FR-A3: tracking_only mode records spend without enforcement."""

    def test_exceeding_limit_no_exception_no_callbacks(self, tracking_enforcer: BudgetEnforcer) -> None:
        """Cost exceeding limit raises no exception and invokes no callbacks."""
        # Record cost well above the $1.00 daily limit
        updated = tracking_enforcer.record_cost(cost_dollars=5.00)

        # No exception raised (we got here)
        assert len(updated) >= 1
        assert updated[0].used_dollars == 5.00

        # Callbacks were never invoked
        assert tracking_enforcer.on_warning is not None
        tracking_enforcer.on_warning.assert_not_called()  # type: ignore[union-attr]
        tracking_enforcer.on_critical.assert_not_called()  # type: ignore[union-attr]
        tracking_enforcer.on_exceeded.assert_not_called()  # type: ignore[union-attr]

    def test_get_summary_reflects_accurate_spend(self, tracking_enforcer: BudgetEnforcer) -> None:
        """get_summary() returns accurate usage even in tracking_only mode."""
        tracking_enforcer.record_cost(cost_dollars=0.50)
        tracking_enforcer.record_cost(cost_dollars=0.75)

        summary = tracking_enforcer.get_summary()
        assert len(summary) >= 1

        # Find the daily usage entry
        daily_usages = [u for u in summary.values() if u.scope == BudgetScope.DAILY]
        assert len(daily_usages) == 1
        assert daily_usages[0].used_dollars == pytest.approx(1.25)

    def test_check_budget_returns_ok_regardless(self, tracking_enforcer: BudgetEnforcer) -> None:
        """check_budget() always returns OK status in tracking_only mode."""
        from datetime import date

        # Exceed the limit first
        tracking_enforcer.record_cost(cost_dollars=10.00)

        today = date.today().isoformat()
        usage = tracking_enforcer.check_budget(BudgetScope.DAILY, today)

        assert usage.status == BudgetStatus.OK
