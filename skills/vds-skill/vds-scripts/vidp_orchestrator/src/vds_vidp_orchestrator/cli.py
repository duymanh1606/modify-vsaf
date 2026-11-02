"""CLI for the VIDP orchestrator.

Examples:
    vds-vidp trigger <workflowId>
    vds-vidp trigger <workflowId> --payload '{"foo": "bar"}'
    vds-vidp trigger <workflowId> --payload-file ./payload.json
    vds-vidp status <jobId>
    vds-vidp status <jobId> --raw
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from vds_cli_common.app import make_vds_app
from vds_cli_common.context import CLIContext
from vds_cli_common.output import OutputManager
from vds_platform_core.errors import SettingsError
from vds_platform_core.logging import configure_structlog

from vds_vidp_orchestrator.client import VidpClient
from vds_vidp_orchestrator.config import load_settings
from vds_vidp_orchestrator.workflows import (
    load_aliases,
    load_package_aliases,
    load_user_aliases,
    package_workflows_file,
    resolve_workflow_id,
    save_user_aliases,
    user_workflows_file,
)

configure_structlog()
app = make_vds_app(
    name="vds-vidp",
    help="VDS VIDP CLI — trigger third-party workflows and poll job status.",
    settings_factory=load_settings,
)


def _resolve_payload(payload: str | None, payload_file: Path | None) -> object | None:
    if payload and payload_file:
        raise typer.BadParameter("Use either --payload or --payload-file, not both.")
    if payload:
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"--payload is not valid JSON: {exc}") from exc
    if payload_file:
        try:
            return json.loads(payload_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"--payload-file is not valid JSON: {exc}") from exc
    return None


@app.command()
def trigger(
    ctx: typer.Context,
    workflow: Annotated[
        str,
        typer.Argument(
            help="Workflow UUID OR alias from ~/.vds/vidp-workflows.json (e.g. 'build-jenkins-by-job-name').",
        ),
    ],
    payload: Annotated[
        str | None,
        typer.Option("--payload", "-p", help="Inline JSON payload"),
    ] = None,
    payload_file: Annotated[
        Path | None,
        typer.Option(
            "--payload-file",
            "-f",
            exists=True,
            readable=True,
            dir_okay=False,
            help="Path to a JSON file containing the payload",
        ),
    ] = None,
) -> None:
    """Trigger a VIDP third-party action by workflow id or alias."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        workflow_id, alias_used = resolve_workflow_id(workflow)
        body = _resolve_payload(payload, payload_file)
        settings = load_settings()
        with VidpClient(settings) as client:
            result = client.trigger(workflow_id, body)
        out.output_json(
            {
                "tool": "vidp.trigger",
                "endpoint": f"/third-party/v2/start/{workflow_id}",
                "aliasUsed": alias_used,
                "workflowId": workflow_id,
                "requestPayload": body if body is not None else {},
                "response": result,
            }
        )
    except KeyError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1) from None
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}", hint="Check VDS_VIDP_* / VIDP_* env vars.")
        raise typer.Exit(1) from None
    except Exception as exc:  # noqa: BLE001 — surface as JSON for AI consumers
        out.output_error(str(exc))
        raise typer.Exit(1) from None


@app.command()
def status(
    ctx: typer.Context,
    job_id: Annotated[
        str,
        typer.Argument(help="Job id (the {jobId} segment of the VIDP status endpoint)"),
    ],
    raw: Annotated[
        bool,
        typer.Option("--raw", help="Emit the raw VIDP response only (skip normalization)."),
    ] = False,
) -> None:
    """Fetch full workflow/stage detail for a VIDP job."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        settings = load_settings()
        with VidpClient(settings) as client:
            response = client.status(job_id)
        if raw:
            out.output_json(response)
            return
        normalized = VidpClient.normalize_status(response)
        out.output_json(
            {
                "tool": "vidp.status",
                "endpoint": f"/third-party/v2/status/{job_id}?full=true",
                "normalized": normalized,
                "response": response,
            }
        )
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}", hint="Check VDS_VIDP_* / VIDP_* env vars.")
        raise typer.Exit(1) from None
    except Exception as exc:  # noqa: BLE001
        out.output_error(str(exc))
        raise typer.Exit(1) from None


workflows_app = typer.Typer(
    name="workflows",
    help=(
        "Manage workflow alias registry. Package defaults ship with vds-scripts "
        "(read-only); add/remove writes to the user override file "
        "(~/.vds/vidp-workflows.json or $VDS_VIDP_WORKFLOWS_FILE)."
    ),
)
app.add_typer(workflows_app, name="workflows")


@workflows_app.command("list")
def workflows_list(ctx: typer.Context) -> None:
    """List alias → workflow-id mappings, separated by source."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    package = load_package_aliases()
    user = load_user_aliases()
    overridden = {k for k in user if k in package and user[k] != package[k]}
    out.output_json(
        {
            "packageFile": str(package_workflows_file()),
            "userFile": str(user_workflows_file()),
            "package": package,
            "user": user,
            "userOverridesPackage": sorted(overridden),
            "merged": load_aliases(),
        }
    )


@workflows_app.command("add")
def workflows_add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Alias name (e.g. 'build-jenkins-by-job-name')")],
    workflow_id: Annotated[str, typer.Argument(help="Workflow UUID")],
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite if alias already exists in user file."),
    ] = False,
) -> None:
    """Add or update an alias in the USER override file.

    Package-shipped aliases are read-only; use ``--force`` to override them
    locally via the user file.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    user = load_user_aliases()
    package = load_package_aliases()
    if name in user and not force:
        out.output_error(
            f"Alias '{name}' already in user file → '{user[name]}'. Use --force to overwrite."
        )
        raise typer.Exit(1) from None
    user[name] = workflow_id
    path = save_user_aliases(user)
    out.output_json(
        {
            "saved": str(path),
            "alias": name,
            "workflowId": workflow_id,
            "overridesPackage": name in package and package[name] != workflow_id,
        }
    )


@workflows_app.command("remove")
def workflows_remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Alias name to remove from user file")],
) -> None:
    """Remove an alias from the USER override file.

    Package-shipped aliases cannot be removed via CLI — edit the package
    workflows.json directly to change the curated catalogue.
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    user = load_user_aliases()
    if name not in user:
        package = load_package_aliases()
        if name in package:
            out.output_error(
                f"Alias '{name}' is shipped with the package (read-only). "
                f"Edit {package_workflows_file()} to change it, or use "
                f"'workflows add {name} <other-uuid> --force' to override locally."
            )
        else:
            out.output_error(f"Alias '{name}' not found.")
        raise typer.Exit(1) from None
    removed = user.pop(name)
    path = save_user_aliases(user)
    out.output_json({"saved": str(path), "removed": name, "wasMappedTo": removed})


if __name__ == "__main__":
    app()
