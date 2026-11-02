"""Unit tests for vds_agent_core.workflows Protocol contract."""

from __future__ import annotations

from vds_agent_core.workflows import WorkflowProvider


class _GoodProvider:
    """Minimal valid WorkflowProvider implementation."""

    def register_workflow_alias(
        self,
        *,
        alias: str,
        workflow_fqn: str,
        owner: str,
    ) -> None:
        pass

    def register_schedule(
        self,
        *,
        schedule_id: str,
        workflow_alias: str,
        cron: str,
        owner: str,
        queue_name: str = "agent-default",
        context_json: dict[str, object] | None = None,
    ) -> None:
        pass


class _MissingMethodProvider:
    """Implementation missing register_schedule."""

    def register_workflow_alias(
        self,
        *,
        alias: str,
        workflow_fqn: str,
        owner: str,
    ) -> None:
        pass


def test_runtime_checkable_accepts_valid_implementation() -> None:
    assert isinstance(_GoodProvider(), WorkflowProvider)


def test_runtime_checkable_rejects_missing_method() -> None:
    assert not isinstance(_MissingMethodProvider(), WorkflowProvider)


def test_protocol_methods_signature_documented() -> None:
    method_names = {"register_workflow_alias", "register_schedule"}
    assert method_names <= set(dir(WorkflowProvider))


def test_provider_call_passes_args_through() -> None:
    captured: dict[str, object] = {}

    class CapturingProvider:
        def register_workflow_alias(
            self,
            *,
            alias: str,
            workflow_fqn: str,
            owner: str,
        ) -> None:
            captured["alias"] = alias
            captured["fqn"] = workflow_fqn
            captured["alias_owner"] = owner

        def register_schedule(
            self,
            *,
            schedule_id: str,
            workflow_alias: str,
            cron: str,
            owner: str,
            queue_name: str = "agent-default",
            context_json: dict[str, object] | None = None,
        ) -> None:
            captured["schedule_id"] = schedule_id
            captured["workflow_alias"] = workflow_alias
            captured["cron"] = cron
            captured["schedule_owner"] = owner
            captured["queue_name"] = queue_name
            captured["context_json"] = context_json

    provider: WorkflowProvider = CapturingProvider()
    provider.register_workflow_alias(
        alias="audit.drift.weekly",
        workflow_fqn="vds_audit_orchestrator.workflows.audit_drift_scan.audit_drift_scan",
        owner="audit_orchestrator",
    )
    provider.register_schedule(
        schedule_id="audit-drift-weekly",
        workflow_alias="audit.drift.weekly",
        cron="0 2 * * MON",
        owner="audit_orchestrator",
    )

    assert captured["alias"] == "audit.drift.weekly"
    assert captured["fqn"] == "vds_audit_orchestrator.workflows.audit_drift_scan.audit_drift_scan"
    assert captured["alias_owner"] == "audit_orchestrator"
    assert captured["schedule_id"] == "audit-drift-weekly"
    assert captured["workflow_alias"] == "audit.drift.weekly"
    assert captured["cron"] == "0 2 * * MON"
    assert captured["schedule_owner"] == "audit_orchestrator"
    assert captured["queue_name"] == "agent-default"
    assert captured["context_json"] is None


def test_register_schedule_accepts_context_json() -> None:
    """context_json defaults to None and accepts a dict for workflow kwargs."""
    captured: dict[str, object] = {}

    class CtxCapturingProvider:
        def register_workflow_alias(self, *, alias, workflow_fqn, owner) -> None:  # type: ignore[no-untyped-def]
            pass

        def register_schedule(
            self, *, schedule_id, workflow_alias, cron, owner, queue_name="agent-default", context_json=None
        ) -> None:  # type: ignore[no-untyped-def]
            captured["context_json"] = context_json

    provider: WorkflowProvider = CtxCapturingProvider()
    provider.register_schedule(
        schedule_id="audit-deep-monthly",
        workflow_alias="audit.deep.monthly",
        cron="0 3 1 * *",
        owner="audit_orchestrator",
        context_json={"project_storage_keys": ["p1", "p2"]},
    )
    assert captured["context_json"] == {"project_storage_keys": ["p1", "p2"]}
