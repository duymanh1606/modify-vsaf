"""Budget enforcement for LLM API costs.

Tracks and enforces spending limits with:
- Per-repository limits
- Per-audit limits
- Daily/monthly limits
- Alerts when approaching limits
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def _default_config_root() -> Path:
    """Return VDS config root, matching vds_cli_common.paths.get_vds_config_root logic."""
    raw = (os.getenv("VDS_CONFIG_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".vds"


class BudgetScope(StrEnum):
    """Scope for budget limits."""

    REPOSITORY = "repository"
    AUDIT = "audit"
    DAILY = "daily"
    MONTHLY = "monthly"


class BudgetStatus(StrEnum):
    """Current budget status."""

    OK = "ok"
    WARNING = "warning"  # >80% used
    CRITICAL = "critical"  # >95% used
    EXCEEDED = "exceeded"  # >100% used


@dataclass
class BudgetLimit:
    """A budget limit configuration."""

    scope: BudgetScope
    limit_dollars: float
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%


@dataclass
class BudgetUsage:
    """Current budget usage."""

    scope: BudgetScope
    scope_id: str  # repo name, audit id, date, etc.
    used_dollars: float = 0.0
    limit_dollars: float = 0.0
    status: BudgetStatus = BudgetStatus.OK

    @property
    def remaining(self) -> float:
        return max(0, self.limit_dollars - self.used_dollars)

    @property
    def percentage_used(self) -> float:
        if self.limit_dollars == 0:
            return 0.0
        return (self.used_dollars / self.limit_dollars) * 100


class BudgetExceededError(Exception):
    """Raised when budget is exceeded."""

    def __init__(self, usage: BudgetUsage):
        self.usage = usage
        super().__init__(
            f"Budget exceeded for {usage.scope.value} '{usage.scope_id}': "
            f"${usage.used_dollars:.4f} / ${usage.limit_dollars:.4f}"
        )


class BudgetEnforcer:
    """Enforces budget limits on LLM spending.

    Features:
    - Multiple scope levels (repo, audit, daily, monthly)
    - Configurable thresholds
    - Alert callbacks
    - Persistent tracking

    Args:
        limits: Budget limits to enforce.
        storage_path: Path to the JSON file for persistent tracking.
            Defaults to ``~/.vds/agent/budget.json`` (or ``$VDS_CONFIG_DIR/agent/budget.json``).
        on_warning: Callback when usage exceeds warning threshold.
        on_critical: Callback when usage exceeds critical threshold.
        on_exceeded: Callback when usage exceeds limit.
        strict: If True, raise BudgetExceededError when limit is exceeded.
    """

    def __init__(
        self,
        limits: list[BudgetLimit] | None = None,
        storage_path: Path | None = None,
        on_warning: Callable[[BudgetUsage], None] | None = None,
        on_critical: Callable[[BudgetUsage], None] | None = None,
        on_exceeded: Callable[[BudgetUsage], None] | None = None,
        strict: bool = True,
        tracking_only: bool = False,
    ):
        self.limits = {limit.scope: limit for limit in (limits or [])}
        self.storage_path = storage_path or (_default_config_root() / "agent" / "budget.json")
        self.on_warning = on_warning
        self.on_critical = on_critical
        self.on_exceeded = on_exceeded
        self._tracking_only = tracking_only
        self.strict = False if tracking_only else strict

        # Usage tracking
        self._usage: dict[str, BudgetUsage] = {}
        self._load_usage()

    def set_limit(
        self,
        scope: BudgetScope,
        limit_dollars: float,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95,
    ) -> None:
        """Set a budget limit."""
        self.limits[scope] = BudgetLimit(
            scope=scope,
            limit_dollars=limit_dollars,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
        )

    def record_cost(
        self,
        cost_dollars: float,
        repository: str | None = None,
        audit_id: str | None = None,
    ) -> list[BudgetUsage]:
        """Record a cost and check against limits.

        Args:
            cost_dollars: Cost to record
            repository: Repository name (for repo scope)
            audit_id: Audit ID (for audit scope)

        Returns:
            List of budget usages that were updated

        Raises:
            BudgetExceededError: If strict mode and budget exceeded
        """
        updated = []

        # Update repository budget
        if repository and BudgetScope.REPOSITORY in self.limits:
            usage = self._update_usage(
                BudgetScope.REPOSITORY,
                repository,
                cost_dollars,
            )
            updated.append(usage)

        # Update audit budget
        if audit_id and BudgetScope.AUDIT in self.limits:
            usage = self._update_usage(
                BudgetScope.AUDIT,
                audit_id,
                cost_dollars,
            )
            updated.append(usage)

        # Update daily budget
        if BudgetScope.DAILY in self.limits:
            today = date.today().isoformat()
            usage = self._update_usage(
                BudgetScope.DAILY,
                today,
                cost_dollars,
            )
            updated.append(usage)

        # Update monthly budget
        if BudgetScope.MONTHLY in self.limits:
            month = date.today().strftime("%Y-%m")
            usage = self._update_usage(
                BudgetScope.MONTHLY,
                month,
                cost_dollars,
            )
            updated.append(usage)

        # Save usage
        self._save_usage()

        return updated

    def check_budget(
        self,
        scope: BudgetScope,
        scope_id: str,
    ) -> BudgetUsage:
        """Check current budget status."""
        key = f"{scope.value}:{scope_id}"
        if key not in self._usage:
            limit = self.limits.get(scope)
            return BudgetUsage(
                scope=scope,
                scope_id=scope_id,
                used_dollars=0.0,
                limit_dollars=limit.limit_dollars if limit else 0.0,
                status=BudgetStatus.OK,
            )
        usage = self._usage[key]
        if self._tracking_only:
            # Return a copy with OK status to avoid leaking internal state
            return BudgetUsage(
                scope=usage.scope,
                scope_id=usage.scope_id,
                used_dollars=usage.used_dollars,
                limit_dollars=usage.limit_dollars,
                status=BudgetStatus.OK,
            )
        return usage

    def get_summary(self) -> dict[str, BudgetUsage]:
        """Get summary of all budget usages."""
        return self._usage.copy()

    def reset_usage(
        self,
        scope: BudgetScope | None = None,
        scope_id: str | None = None,
    ) -> None:
        """Reset usage for a scope or all scopes.

        Args:
            scope: Specific scope to reset (None = all)
            scope_id: Specific scope_id to reset (None = all in scope)
        """
        if scope is None:
            self._usage.clear()
        elif scope_id is None:
            keys_to_remove = [k for k in self._usage if k.startswith(f"{scope.value}:")]
            for key in keys_to_remove:
                del self._usage[key]
        else:
            key = f"{scope.value}:{scope_id}"
            if key in self._usage:
                del self._usage[key]

        self._save_usage()

    def _update_usage(
        self,
        scope: BudgetScope,
        scope_id: str,
        cost_dollars: float,
    ) -> BudgetUsage:
        """Update usage for a scope."""
        key = f"{scope.value}:{scope_id}"
        limit = self.limits[scope]

        if key not in self._usage:
            self._usage[key] = BudgetUsage(
                scope=scope,
                scope_id=scope_id,
                used_dollars=0.0,
                limit_dollars=limit.limit_dollars,
            )

        usage = self._usage[key]
        usage.used_dollars += cost_dollars

        # Update status
        pct = usage.used_dollars / limit.limit_dollars if limit.limit_dollars > 0 else 0

        if self._tracking_only:
            # Tracking-only: update counters but skip callbacks and exceptions
            usage.status = BudgetStatus.OK
        elif pct >= 1.0:
            usage.status = BudgetStatus.EXCEEDED
            if self.on_exceeded:
                self.on_exceeded(usage)
            if self.strict:
                raise BudgetExceededError(usage)
        elif pct >= limit.critical_threshold:
            usage.status = BudgetStatus.CRITICAL
            if self.on_critical:
                self.on_critical(usage)
        elif pct >= limit.warning_threshold:
            usage.status = BudgetStatus.WARNING
            if self.on_warning:
                self.on_warning(usage)
        else:
            usage.status = BudgetStatus.OK

        logger.info(
            "Budget updated",
            scope=scope.value,
            scope_id=scope_id,
            used=f"${usage.used_dollars:.4f}",
            limit=f"${limit.limit_dollars:.4f}",
            status=usage.status.value,
        )

        return usage

    def _load_usage(self) -> None:
        """Load usage from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                for key, usage_data in data.items():
                    self._usage[key] = BudgetUsage(
                        scope=BudgetScope(usage_data["scope"]),
                        scope_id=usage_data["scope_id"],
                        used_dollars=usage_data["used_dollars"],
                        limit_dollars=usage_data["limit_dollars"],
                        status=BudgetStatus(usage_data["status"]),
                    )
            except Exception as e:
                logger.warning("Failed to load budget data", error=str(e))

    def _save_usage(self) -> None:
        """Save usage to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            key: {
                "scope": usage.scope.value,
                "scope_id": usage.scope_id,
                "used_dollars": usage.used_dollars,
                "limit_dollars": usage.limit_dollars,
                "status": usage.status.value,
            }
            for key, usage in self._usage.items()
        }
        self.storage_path.write_text(json.dumps(data, indent=2))
