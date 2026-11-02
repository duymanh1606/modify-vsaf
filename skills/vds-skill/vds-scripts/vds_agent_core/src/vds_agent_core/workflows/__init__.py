"""Workflow contracts for cross-orchestrator decoupling.

Provides:
  - WorkflowProvider (always available): Protocol that scheduler-like hosts
    implement to accept cron schedule + workflow alias registrations from
    workflow providers (entry-points group `vds.workflows`).
  - run_langgraph (requires `vds-agent-core[workflows]`): generic
    LangGraph-in-DBOS step relocated from scheduler_orchestrator per
    ADR-DCP-1, v0.2.0. Import explicitly:
        `from vds_agent_core.workflows.langgraph_runner import run_langgraph`

Audit and other workflow-provider packages depend on this module via the
`vds.workflows` Python entry-points group; scheduler-like consumers depend on
the Protocol type and discover providers through `importlib.metadata.entry_points`.
"""

from vds_agent_core.workflows.protocols import WorkflowProvider

__all__ = ["WorkflowProvider"]
