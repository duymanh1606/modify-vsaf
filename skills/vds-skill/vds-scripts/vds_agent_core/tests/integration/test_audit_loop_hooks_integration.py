"""Cross-orchestrator integration tests for AuditLoopHooks ↔ LoopBehaviorHooks.

Phase 9d Contract 2: ``AuditLoopHooks`` from
``vds_audit_orchestrator.agents.audit_loop_hooks`` must structurally satisfy
the ``LoopBehaviorHooks`` Protocol from ``vds_agent_core.agents.hooks``.
The Protocol is ``@runtime_checkable``, so isinstance() must return True
and every Protocol method must return audit-specific values when invoked.

Skipped gracefully if ``vds_audit_orchestrator`` is not on PYTHONPATH.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "vds_audit_orchestrator",
    reason="audit integration tests require vds_audit_orchestrator on PYTHONPATH",
)


@pytest.fixture
def audit_hooks():
    """Construct a fresh AuditLoopHooks instance for each test."""
    from vds_audit_orchestrator.agents.audit_loop_hooks import AuditLoopHooks

    return AuditLoopHooks()


class TestProtocolSatisfaction:
    """AuditLoopHooks must satisfy LoopBehaviorHooks at runtime."""

    def test_isinstance_passes_for_audit_hooks(self, audit_hooks) -> None:
        """isinstance check against the runtime_checkable Protocol passes."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks

        assert isinstance(audit_hooks, LoopBehaviorHooks)

    def test_audit_hooks_does_not_subclass_noophooks(self, audit_hooks) -> None:
        """AuditLoopHooks is structurally compatible — not a subclass.

        This is the discipline guard: AuditLoopHooks must remain free of
        inheritance from NoOpHooks so the Protocol contract (and not class
        hierarchy) is what enforces compatibility.
        """
        from vds_agent_core.agents.hooks import NoOpHooks

        assert not isinstance(audit_hooks, NoOpHooks)

    def test_all_protocol_methods_are_callable(self, audit_hooks) -> None:
        """Every Protocol method exists on AuditLoopHooks and is callable."""
        protocol_methods = (
            "should_skip_first_step",
            "is_evidence_recording",
            "is_context_query",
            "has_read_activity",
            "count_doc_reads",
            "is_doc_search",
            "lookup_evidence_requirements",
            "get_trace_context",
            "get_trace_span_name",
            "get_service_name",
        )
        for name in protocol_methods:
            method = getattr(audit_hooks, name, None)
            assert method is not None, f"AuditLoopHooks missing {name}"
            assert callable(method), f"AuditLoopHooks.{name} not callable"


class TestAuditSpecificReturnValues:
    """Calling AuditLoopHooks methods returns audit-specific values."""

    def test_get_service_name_returns_audit_identifier(self, audit_hooks) -> None:
        """AuditLoopHooks must report the audit OTel service.name."""
        assert audit_hooks.get_service_name() == "vds-audit-orchestrator"

    def test_get_trace_span_name_uses_audit_prefix(self, audit_hooks) -> None:
        """Span name format is ``audit.loop.step{N}.{tool}``."""
        name = audit_hooks.get_trace_span_name(step=3, tool="search_docs")
        assert name == "audit.loop.step3.search_docs"

    def test_get_trace_context_returns_empty_dict(self, audit_hooks) -> None:
        """AuditLoopHooks delegates audit-context propagation to
        ``audit_otel_span`` in logging_config and returns {} from this hook."""
        ctx = audit_hooks.get_trace_context()
        assert ctx == {}
        assert isinstance(ctx, dict)

    def test_should_skip_first_step_for_get_row_context(self, audit_hooks) -> None:
        """should_skip_first_step returns True for GET_ROW_CONTEXT tool."""
        from vds_audit_orchestrator.agents.tool_registry import ToolName

        assert audit_hooks.should_skip_first_step(tool=ToolName.GET_ROW_CONTEXT, context={}) is True

    def test_is_evidence_recording_for_record_evidence_refs(self, audit_hooks) -> None:
        """is_evidence_recording returns True for RECORD_EVIDENCE_REFS."""
        from vds_audit_orchestrator.agents.tool_registry import ToolName

        assert audit_hooks.is_evidence_recording(ToolName.RECORD_EVIDENCE_REFS) is True
        # And False for an arbitrary other tool name.
        assert audit_hooks.is_evidence_recording("not_a_tool") is False

    def test_lookup_evidence_requirements_returns_dict(self, audit_hooks) -> None:
        """lookup_evidence_requirements always returns a dict (never None)."""
        result = audit_hooks.lookup_evidence_requirements({})
        assert isinstance(result, dict)
        # Defaults must include is_default flag per Protocol contract.
        if result:
            assert "is_default" in result


class TestProtocolSubstitutability:
    """AuditLoopHooks can be used wherever LoopBehaviorHooks is expected."""

    def test_audit_hooks_substitute_for_protocol_consumer(self, audit_hooks) -> None:
        """A function annotated with LoopBehaviorHooks accepts AuditLoopHooks."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks

        def consumer(hooks: LoopBehaviorHooks) -> str:
            # Exercise multiple Protocol methods to prove duck-typing works.
            assert isinstance(hooks, LoopBehaviorHooks)
            return hooks.get_service_name()

        result = consumer(audit_hooks)
        assert result == "vds-audit-orchestrator"

    def test_noop_and_audit_hooks_both_satisfy_protocol(self, audit_hooks) -> None:
        """Both built-in NoOpHooks and AuditLoopHooks satisfy the Protocol."""
        from vds_agent_core.agents.hooks import LoopBehaviorHooks, NoOpHooks

        noop = NoOpHooks()
        assert isinstance(noop, LoopBehaviorHooks)
        assert isinstance(audit_hooks, LoopBehaviorHooks)
        # Distinct service names verify they are genuinely different impls.
        assert noop.get_service_name() != audit_hooks.get_service_name()
