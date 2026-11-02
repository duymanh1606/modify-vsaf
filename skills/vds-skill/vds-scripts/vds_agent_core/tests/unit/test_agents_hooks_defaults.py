"""Tests for LoopBehaviorHooks + NoOpHooks default methods."""

from vds_agent_core.agents.hooks import NoOpHooks


class TestLoopBehaviorHooksDefaults:
    """Cover lines 64, 75, 82 — Protocol default implementations."""

    def test_get_trace_context_default_is_empty_dict(self) -> None:
        """When only Protocol defaults are used, get_trace_context returns {}."""
        hooks = NoOpHooks()
        assert hooks.get_trace_context() == {}

    def test_get_trace_span_name_default_format(self) -> None:
        """Default span name is step-N/tool."""
        hooks = NoOpHooks()
        assert hooks.get_trace_span_name(3, "bash") == "step-3/bash"

    def test_get_service_name_default_is_vds_agent_core(self) -> None:
        """Default service name is vds-agent-core."""
        hooks = NoOpHooks()
        assert hooks.get_service_name() == "vds-agent-core"
