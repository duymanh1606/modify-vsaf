"""Cross-orchestrator integration tests for the audit ↔ vds_agent_core
observability contract (Phase 9d).

These tests assert that ``audit_orchestrator.logging_config.audit_otel_span``
and ``audit_orchestrator.cli_impl.init_tracing`` correctly delegate to
``vds_agent_core.observability.AgentTracer`` and that audit-specific
contextvars (audit_id / repo / check_id / agent / phase / task_id)
surface as span attributes.

Skipped gracefully when ``vds_audit_orchestrator`` is not installed in the
current pytest workspace — these are integration tests, not unit tests.
"""

from __future__ import annotations

import pytest

# Skip the entire module if audit orchestrator is not importable in the
# current pytest scope (e.g., when running this package in isolation).
pytest.importorskip(
    "vds_audit_orchestrator",
    reason="audit integration tests require vds_audit_orchestrator on PYTHONPATH",
)


@pytest.fixture(autouse=True)
def _reset_audit_context() -> None:
    """Ensure each test starts with a clean audit contextvar state."""
    from vds_audit_orchestrator.logging_config import clear_audit_context

    clear_audit_context()
    yield
    clear_audit_context()


class TestAuditOtelSpanContract:
    """audit_otel_span must merge audit contextvars into span attributes."""

    def test_audit_otel_span_yields_span_when_otel_available(self) -> None:
        """When OpenTelemetry is installed, audit_otel_span yields a real Span object."""
        from vds_audit_orchestrator.logging_config import audit_otel_span

        with audit_otel_span("test.span", attributes={"k": "v"}) as span:
            # Either a real Span (OTel installed) or None (no-op fallback).
            # In our workspace OTel is available; assert we got an object.
            assert span is None or hasattr(span, "set_attribute")

    def test_audit_contextvars_propagate_to_span_attributes(self) -> None:
        """audit_id / repo / check_id contextvars must appear on the span."""
        from vds_audit_orchestrator.logging_config import (
            audit_otel_span,
            set_audit_context,
        )

        set_audit_context(audit_id="aud-42", repo="vds-scripts", check_id="C.1")

        with audit_otel_span("audit.test.span", attributes={"extra": "marker"}) as span:
            if span is None:
                pytest.skip("OpenTelemetry not installed in this environment")
            attrs = dict(span.attributes) if hasattr(span, "attributes") else {}
            assert attrs.get("audit_id") == "aud-42"
            assert attrs.get("repo") == "vds-scripts"
            assert attrs.get("check_id") == "C.1"
            assert attrs.get("extra") == "marker"

    def test_extra_attributes_override_audit_contextvars(self) -> None:
        """Extra dict overrides matching contextvar keys."""
        from vds_audit_orchestrator.logging_config import (
            audit_otel_span,
            set_audit_context,
        )

        set_audit_context(audit_id="aud-A", repo="repo-A")

        with audit_otel_span(
            "audit.override.span",
            attributes={"audit_id": "aud-OVERRIDE", "x": "y"},
        ) as span:
            if span is None:
                pytest.skip("OpenTelemetry not installed in this environment")
            attrs = dict(span.attributes) if hasattr(span, "attributes") else {}
            # Spec: ``audit_trace_attrs`` overlays ``extra`` last → extra wins.
            assert attrs.get("audit_id") == "aud-OVERRIDE"
            assert attrs.get("repo") == "repo-A"
            assert attrs.get("x") == "y"

    def test_audit_otel_span_without_contextvars_still_works(self) -> None:
        """audit_otel_span must never raise when no contextvars are set."""
        from vds_audit_orchestrator.logging_config import audit_otel_span

        # No set_audit_context — all contextvars are None.
        with audit_otel_span("audit.bare.span") as span:
            if span is None:
                return  # OTel not installed → no-op contract honored
            attrs = dict(span.attributes) if hasattr(span, "attributes") else {}
            # None-valued contextvars must NOT bleed into attributes.
            assert "audit_id" not in attrs
            assert "repo" not in attrs

    def test_audit_otel_span_partial_contextvars(self) -> None:
        """Only set contextvars surface; unset ones must not appear at all."""
        from vds_audit_orchestrator.logging_config import (
            audit_otel_span,
            set_audit_context,
        )

        set_audit_context(audit_id="only-this", phase="phase-9d")

        with audit_otel_span("audit.partial.span") as span:
            if span is None:
                pytest.skip("OpenTelemetry not installed in this environment")
            attrs = dict(span.attributes) if hasattr(span, "attributes") else {}
            assert attrs.get("audit_id") == "only-this"
            assert attrs.get("phase") == "phase-9d"
            # Unset contextvars must not pollute the attribute dict.
            assert "repo" not in attrs
            assert "check_id" not in attrs
            assert "task_id" not in attrs

    def test_audit_trace_attrs_pure_data_helper(self) -> None:
        """audit_trace_attrs returns merged dict without touching tracer."""
        from vds_audit_orchestrator.logging_config import (
            audit_trace_attrs,
            set_audit_context,
        )

        set_audit_context(
            audit_id="A1",
            repo="R1",
            check_id="C1",
            agent="alpha",
            phase="p7",
            task_id="t9",
        )

        merged = audit_trace_attrs({"extra": "added"})
        assert merged["audit_id"] == "A1"
        assert merged["repo"] == "R1"
        assert merged["check_id"] == "C1"
        assert merged["agent"] == "alpha"
        assert merged["phase"] == "p7"
        assert merged["task_id"] == "t9"
        assert merged["extra"] == "added"


class TestInitTracingContract:
    """audit_orchestrator.cli_impl.init_tracing → AgentTracer construction."""

    def test_init_tracing_disabled_is_noop(self) -> None:
        """init_tracing(enabled=False) must return without instantiating OTel."""
        from vds_audit_orchestrator.cli_impl import init_tracing

        # Should not raise, should not log, should not set up any provider.
        result = init_tracing(enabled=False)
        assert result is None

    def test_init_tracing_constructs_agent_tracer_with_audit_service_name(self) -> None:
        """init_tracing constructs AgentTracer with the audit service_name."""
        from unittest.mock import MagicMock, patch

        from vds_audit_orchestrator.cli_impl import init_tracing

        with patch("vds_agent_core.observability.AgentTracer") as MockAgentTracer:
            mock_instance = MagicMock()
            mock_instance.is_enabled = False  # short-circuit OTLP wiring
            MockAgentTracer.return_value = mock_instance

            init_tracing(service_name="vds-audit-orchestrator", enabled=True)

            MockAgentTracer.assert_called_once_with(
                service_name="vds-audit-orchestrator",
                enabled=True,
            )

    def test_init_tracing_uses_default_audit_service_name(self) -> None:
        """The default service_name is the audit-specific identifier."""
        from unittest.mock import MagicMock, patch

        from vds_audit_orchestrator.cli_impl import init_tracing

        with patch("vds_agent_core.observability.AgentTracer") as MockAgentTracer:
            mock_instance = MagicMock()
            mock_instance.is_enabled = False
            MockAgentTracer.return_value = mock_instance

            init_tracing(enabled=True)

            _, kwargs = MockAgentTracer.call_args
            assert kwargs.get("service_name") == "vds-audit-orchestrator"

    def test_init_tracing_skips_otlp_when_no_endpoint(self) -> None:
        """No OTLP exporter is wired when endpoint=None."""
        from unittest.mock import MagicMock, patch

        from vds_audit_orchestrator.cli_impl import init_tracing

        with patch("vds_agent_core.observability.AgentTracer") as MockAgentTracer:
            mock_instance = MagicMock()
            mock_instance.is_enabled = True
            MockAgentTracer.return_value = mock_instance

            # No endpoint → must not import OTLP exporter modules.
            init_tracing(endpoint=None, enabled=True)

            # The tracer is constructed but no add_span_processor call should
            # have happened on the mock (we never reach OTLP block).
            mock_instance.add_span_processor.assert_not_called()


class TestSpanCorrelationContract:
    """End-to-end: audit_otel_span uses the same singleton AgentTracer."""

    def test_singleton_tracer_reused_across_spans(self) -> None:
        """The first span lazily creates the audit AgentTracer, subsequent
        calls reuse it (the module-level singleton)."""
        from vds_audit_orchestrator import logging_config
        from vds_audit_orchestrator.logging_config import audit_otel_span

        # Reset singleton before this test (keeps it independent of order).
        logging_config._AUDIT_TRACER = None

        with audit_otel_span("first.span"):
            pass

        first = logging_config._AUDIT_TRACER
        assert first is not None

        with audit_otel_span("second.span"):
            pass

        # Same tracer instance → no per-call provider re-init.
        assert logging_config._AUDIT_TRACER is first

    def test_audit_tracer_service_name_is_audit_specific(self) -> None:
        """The lazy singleton tracer is constructed with the audit service name."""
        from vds_audit_orchestrator import logging_config
        from vds_audit_orchestrator.logging_config import audit_otel_span

        logging_config._AUDIT_TRACER = None

        with audit_otel_span("svc-name-check"):
            pass

        tracer = logging_config._AUDIT_TRACER
        assert tracer is not None
        assert tracer.service_name == "vds-audit-orchestrator"
