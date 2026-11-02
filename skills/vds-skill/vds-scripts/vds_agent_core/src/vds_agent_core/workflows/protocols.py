"""WorkflowProvider Protocol — host-side contract for cron-driven workflows.

Defined by ADR-DCP-1 of the vds-scheduler spec
(v0.2.0). A `WorkflowProvider` is anything that can register workflow aliases
and cron schedules for a durable workflow framework (currently DBOS in the
VDS scheduler_orchestrator). Workflow-provider packages (e.g.,
audit_orchestrator) receive an instance of WorkflowProvider as the argument
to their entry-point `register(provider)` callable, and use it to register
aliases + schedules without importing scheduler internals directly.

Both methods are idempotent — implementations MUST silently ignore the
host's "duplicate alias" / "duplicate schedule" errors so that providers
can call `register()` from a lifespan that runs on every container start.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkflowProvider(Protocol):
    """Host-side contract that scheduler-like orchestrators expose to workflow
    providers (entry-points group `vds.workflows`).

    Stability: This Protocol is part of the v0.2.0 contract for entry-points
    group `vds.workflows`. Breaking changes (method signature changes,
    removals) require a major bump of the `vds_agent_core` package. Additive
    changes (new methods, or new keyword-only args with defaults) are
    non-breaking.
    """

    def register_workflow_alias(
        self,
        *,
        alias: str,
        workflow_fqn: str,
        owner: str,
    ) -> None:
        """Map a stable alias to a fully-qualified `@DBOS.workflow` function.

        Args:
            alias: Stable name used by `register_schedule(workflow_alias=...)`
                (e.g., "audit.drift.weekly").
            workflow_fqn: Dotted import path to the workflow function
                (e.g., "vds_audit_orchestrator.workflows.audit_drift_scan.audit_drift_scan").
            owner: Workflow-owner package name (e.g., "audit_orchestrator").

        Idempotent: implementations MUST silently swallow any
        "duplicate alias" error from the host registry.
        """
        ...

    def register_schedule(
        self,
        *,
        schedule_id: str,
        workflow_alias: str,
        cron: str,
        owner: str,
        queue_name: str = "agent-default",
        context_json: dict[str, Any] | None = None,
    ) -> None:
        """Register a cron-driven schedule that fires `workflow_alias`.

        Args:
            schedule_id: Stable identifier for the schedule
                (e.g., "audit-drift-weekly").
            workflow_alias: Alias previously registered via
                `register_workflow_alias` that points to the actual
                `@DBOS.workflow` function.
            cron: Cron expression (5-field standard form, e.g., "0 2 * * MON").
            owner: Workflow-owner package name (e.g., "audit_orchestrator").
            queue_name: Host-defined queue name. Defaults to "agent-default".
            context_json: JSON-serialisable keyword arguments passed to the
                workflow function on each tick. None when no kwargs needed.

        Idempotent: implementations MUST silently swallow any
        "duplicate schedule" error from the host registry.
        """
        ...
