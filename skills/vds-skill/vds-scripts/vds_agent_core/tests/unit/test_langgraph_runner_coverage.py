"""Coverage uplift for vds_agent_core.workflows.langgraph_runner (W5.4).

Exercises the run_langgraph body (lines 68-79) which requires:
- a mocked DBOS.workflow_id context variable
- an async fake graph with ainvoke()

Uses run_langgraph.__wrapped__ to call the underlying coroutine directly,
bypassing the DBOS step boundary while still covering the function body.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from vds_agent_core.workflows.langgraph_runner import build_agent_workflow, run_langgraph


def _make_graph(result: dict[str, Any]) -> MagicMock:
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value=result)
    return graph


class TestRunLangraphBody:
    """Tests that exercise the wrapped coroutine body at lines 68-79."""

    def test_run_langgraph_has_wrapped_coroutine(self) -> None:
        assert hasattr(run_langgraph, "__wrapped__"), "DBOS.step must preserve __wrapped__"
        assert inspect.iscoroutinefunction(run_langgraph.__wrapped__)

    def test_uses_dbos_workflow_id_as_thread_id(self) -> None:
        graph = _make_graph({"output": "done"})
        with patch("vds_agent_core.workflows.langgraph_runner.DBOS") as mock_dbos:
            mock_dbos.workflow_id = "wf-abc-123"
            result = asyncio.run(run_langgraph.__wrapped__(graph, {"input": "x"}))

        assert result == {"output": "done"}
        graph.ainvoke.assert_called_once_with(
            {"input": "x"},
            config={"configurable": {"thread_id": "wf-abc-123"}},
        )

    def test_generates_uuid_when_workflow_id_is_none(self) -> None:
        graph = _make_graph({"status": "ok"})
        with patch("vds_agent_core.workflows.langgraph_runner.DBOS") as mock_dbos:
            mock_dbos.workflow_id = None
            result = asyncio.run(run_langgraph.__wrapped__(graph, {}))

        assert result == {"status": "ok"}
        call_kwargs = graph.ainvoke.call_args
        thread_id = call_kwargs[1]["config"]["configurable"]["thread_id"]
        # UUID format: 8-4-4-4-12 hex chars separated by dashes
        import uuid
        parsed = uuid.UUID(thread_id)
        assert str(parsed) == thread_id

    def test_passes_input_state_to_graph(self) -> None:
        input_state = {"project_id": "proj-99", "depth": 3}
        graph = _make_graph({"result": "finished"})
        with patch("vds_agent_core.workflows.langgraph_runner.DBOS") as mock_dbos:
            mock_dbos.workflow_id = "wf-xyz"
            asyncio.run(run_langgraph.__wrapped__(graph, input_state))

        invoked_input = graph.ainvoke.call_args[0][0]
        assert invoked_input == input_state

    def test_returns_graph_output_unchanged(self) -> None:
        expected = {"nodes": ["A", "B"], "final": True}
        graph = _make_graph(expected)
        with patch("vds_agent_core.workflows.langgraph_runner.DBOS") as mock_dbos:
            mock_dbos.workflow_id = "wf-return-test"
            result = asyncio.run(run_langgraph.__wrapped__(graph, {}))

        assert result is expected


class TestBuildAgentWorkflow:
    """Tests for build_agent_workflow helper."""

    def test_calls_graph_builder_with_dsn(self) -> None:
        calls: list[str] = []

        def builder(dsn: str) -> str:
            calls.append(dsn)
            return "compiled-graph"

        result = build_agent_workflow(builder, "postgresql://host/db")
        assert result == "compiled-graph"
        assert calls == ["postgresql://host/db"]

    def test_returns_builder_result(self) -> None:
        sentinel = object()
        result = build_agent_workflow(lambda _dsn: sentinel, "dsn")
        assert result is sentinel
