"""Public API stability tests for vds_agent_core (Phase 10 Contract update).

These tests pin the public surface that other orchestrators (most notably
``vds_audit_orchestrator``) depend on. Any backwards-incompatible change to
these contracts must explicitly update this file — the failing test makes
the breakage visible at the call site that ships first.

Contracts pinned:

1. ``AgentTracer.open_span(name, attributes)`` is callable and yields a
   ``Span | None`` (concrete object when OTel is available, None otherwise).

This file is integration-tier (it touches the public boundary across
multiple subpackages) but does NOT depend on ``vds_audit_orchestrator``.
"""

from __future__ import annotations

import inspect

# ---------------------------------------------------------------------------
# Contract 3.1 — AgentTracer.open_span signature & return type
# ---------------------------------------------------------------------------


class TestAgentTracerOpenSpanContract:
    """AgentTracer.open_span must remain backwards-compatible."""

    def test_open_span_signature_accepts_name_and_attributes(self) -> None:
        from vds_agent_core.observability import AgentTracer

        sig = inspect.signature(AgentTracer.open_span)
        params = list(sig.parameters.values())
        # self, name, attributes
        assert len(params) >= 3
        assert params[1].name == "name"
        assert params[2].name == "attributes"

    def test_open_span_attributes_is_optional(self) -> None:
        """``attributes`` must default to None so callers can omit it."""
        from vds_agent_core.observability import AgentTracer

        sig = inspect.signature(AgentTracer.open_span)
        attrs_param = sig.parameters["attributes"]
        assert attrs_param.default is None

    def test_open_span_yields_span_or_none(self) -> None:
        """Context manager yields either a Span-like object or None."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="api-stability", enabled=True)
        with tracer.open_span("api.test", attributes={"k": "v"}) as span:
            assert span is None or hasattr(span, "set_attribute")

    def test_open_span_yields_none_when_disabled(self) -> None:
        """Disabled tracer yields None — call site can branch on truthiness."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="api-stability", enabled=False)
        with tracer.open_span("disabled.test") as span:
            assert span is None

    def test_open_span_handles_no_attributes(self) -> None:
        """open_span(name) without attributes is the expected minimum call."""
        from vds_agent_core.observability import AgentTracer

        tracer = AgentTracer(service_name="api-stability", enabled=True)
        with tracer.open_span("minimal") as span:
            assert span is None or hasattr(span, "set_attribute")


# ---------------------------------------------------------------------------
# Public API surface — module-level exports must remain stable
# ---------------------------------------------------------------------------


class TestPublicApiSurface:
    """Re-exports from package __init__ files form the documented contract."""

    def test_observability_public_exports(self) -> None:
        import vds_agent_core.observability as obs

        assert "AgentTracer" in obs.__all__
        assert hasattr(obs, "AgentTracer")

    def test_agents_public_exports(self) -> None:
        import vds_agent_core.agents as ag

        for name in ("LoopBehaviorHooks", "NoOpHooks"):
            assert name in ag.__all__, f"{name} missing from agents.__all__"
            assert hasattr(ag, name), f"{name} not exported from agents"
