"""LangGraph-in-DBOS step wrapper — canonical home (relocated v0.2.0).

Implements the canonical ADR-2 / scheduler design.md §LangGraph-in-DBOS
Composition Pattern for executing a LangGraph CompiledStateGraph inside a
DBOS durable-execution step. Relocated from
`scheduler_orchestrator/.../workflows/agent_step.py` per ADR-DCP-1
(vds-scheduler v0.2.0) so audit workflow modules
depend on this generic library rather than on scheduler internals.

Two-checkpointer architecture (confirmed safe):
  - DBOS: checkpoints the step OUTPUT at the step boundary for step-level replay.
  - LangGraph (AsyncPostgresSaver): checkpoints intra-graph supernode state for
    graph-internal resume. Tables live under LangGraph's schema namespace —
    ZERO overlap with DBOS's dbos.* schema.
  - On DBOS retry of the step: LangGraph resumes from its LAST COMPLETED SUPERNODE
    (not from scratch), because AsyncPostgresSaver keyed on thread_id=workflow_id
    finds the existing checkpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dbos import DBOS

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


@DBOS.step(retries_allowed=True, max_attempts=3)
async def run_langgraph(
    graph: CompiledStateGraph,
    input_state: dict[str, Any],
) -> dict[str, Any]:
    """Execute a LangGraph CompiledStateGraph inside a DBOS durable step.

    The DBOS workflow_id is used directly as the LangGraph thread_id, binding
    both durable-execution timelines to a single identifier. This enables
    cross-tool observability: `vds-cli workflows show <id>` can show both the
    DBOS step list and the LangGraph supernode list linked by thread_id.

    Durability guarantee:
      - DBOS checkpoints the step OUTPUT when the step completes successfully.
      - If the process is killed during graph execution, DBOS retries the step.
      - On retry, LangGraph's AsyncPostgresSaver (keyed on thread_id) finds the
        existing supernode checkpoints and resumes from the last completed node,
        NOT from the start of the graph.

    Args:
        graph: A compiled LangGraph graph whose checkpointer is already
               configured (e.g., AsyncPostgresSaver wired to the scheduler DB).
               The graph builder must be called in the calling DBOS workflow so
               that its parameters (DSN, etc.) are the workflow's serialised
               inputs — on DBOS replay the workflow recreates the graph
               deterministically and passes it here.
        input_state: Initial state dict passed to graph.ainvoke(). Must be
                     JSON-serialisable (DBOS persists the step OUTPUT for replay).

    Returns:
        The graph's final state dict as returned by ainvoke().

    Note:
        graph is NOT serialised by DBOS (it's not a simple JSON value). This
        is safe because DBOS persists step OUTPUTS, not inputs. The calling
        workflow is responsible for recreating the graph deterministically from
        its own serialised arguments on replay.
    """
    thread_id = DBOS.workflow_id

    if thread_id is None:
        import uuid

        thread_id = str(uuid.uuid4())

    result: dict[str, Any] = await graph.ainvoke(
        input_state,
        config={"configurable": {"thread_id": thread_id}},
    )
    return result


def build_agent_workflow(
    graph_builder: Any,
    checkpointer_dsn: str,
) -> CompiledStateGraph:
    """Convenience helper: call a graph_builder callable with the provided DSN.

    Callers typically store graph_builder as a module-level reference and
    invoke it from within a @DBOS.workflow() function body, so the DSN (a
    serialisable string) is the only workflow-level argument needed.

    Example:

        @DBOS.workflow()
        async def run_audit_workflow(project_id: str, dsn: str) -> dict:
            graph = build_agent_workflow(build_audit_graph, dsn)
            return await run_langgraph(graph, {"project_id": project_id})

    This ensures DBOS can replay the workflow from its serialised
    (project_id, dsn) inputs and recreate the identical graph deterministically.
    """
    return graph_builder(checkpointer_dsn)
