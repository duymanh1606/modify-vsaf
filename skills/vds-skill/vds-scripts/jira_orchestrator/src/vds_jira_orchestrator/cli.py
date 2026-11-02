"""Typer CLI for Jira using the SDK-only adapter."""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import typer
from vds_platform_core.logging import configure_structlog

from .adapter import JiraAdapter
from .config import JiraSettings, SettingsError, load_settings
from .errors import AuthError, VDSClientError
from .reporting import RunSummary, write_reports

app = typer.Typer(add_completion=False, help="Jira operations orchestrator (SDK-only)")
logger = logging.getLogger("jira_cli")

APP_NAME = "vds-jira-orchestrator"
APP_VERSION = "2025.11.0"

_REPORT_DIR = (Path(__file__).resolve().parents[3] / "reports" / "jira_runs").resolve()


def _emit_json(payload: Any) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True)
    if sys.stdout.isatty():
        typer.echo(text)
    else:
        sys.stdout.write(text + "\n")


def _parse_set(items: Sequence[str], *, allow_scalar_json: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for raw in items:
        if "=" not in raw:
            raise typer.BadParameter(f"Invalid --set item '{raw}', expected key=value")
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise typer.BadParameter(f"Invalid key in --set '{raw}'")

        # Try parsing value as JSON for complex field structures (e.g., customfields)
        try:
            val = json.loads(v)
            if isinstance(val, (dict, list)) or allow_scalar_json:
                out[k] = val
            else:
                out[k] = v
        except json.JSONDecodeError:
            # Fallback to string if not valid JSON
            out[k] = v

    return out


# ---------------------------------------------------------------------------
# Field metadata helpers
# ---------------------------------------------------------------------------


def _normalize_allowed_values(field_info: dict[str, Any]) -> list[dict[str, str]]:
    allowed_values: list[dict[str, str]] = []
    for raw in field_info.get("allowedValues", []) or []:
        if not isinstance(raw, dict):
            continue
        value = raw.get("value") or raw.get("name") or raw.get("displayName")
        if value is None:
            continue
        allowed_values.append({"id": str(raw.get("id") or ""), "value": str(value)})
    return allowed_values


def _merge_allowed_values_from_editmeta(raw_fields: dict[str, Any], editmeta_fields: dict[str, Any]) -> None:
    for field_id, field_info in raw_fields.items():
        if not isinstance(field_info, dict):
            continue
        if field_info.get("allowedValues"):
            continue
        edit_info = editmeta_fields.get(field_id)
        if not isinstance(edit_info, dict):
            continue
        if not edit_info.get("allowedValues"):
            continue
        merged = dict(field_info)
        merged["allowedValues"] = edit_info["allowedValues"]
        raw_fields[field_id] = merged


def _build_field_data(field_id: str, field_info: dict[str, Any]) -> dict[str, Any]:
    field_name = str(field_info.get("name") or "")
    field_data = {
        "id": field_id,
        "name": field_name,
        "type": field_info.get("schema", {}).get("type", "unknown"),
        "required": bool(field_info.get("required", False)),
        "is_custom": field_id.startswith("customfield_"),
    }
    allowed_values = _normalize_allowed_values(field_info)
    if allowed_values:
        field_data["allowedValues"] = allowed_values
    return field_data


def _field_matches_filter(field_id: str, field_name: str, field_filter: str) -> bool:
    token = field_filter.strip().lower()
    if not token:
        return True
    return token in field_name.lower() or token in field_id.lower()


def _collect_fields(
    raw_fields: dict[str, Any],
    *,
    field_filter: str | None,
    include_system: bool,
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    for field_id, field_info in raw_fields.items():
        field_name = str(field_info.get("name") or "")
        if field_filter and not _field_matches_filter(field_id, field_name, field_filter):
            continue
        is_custom = field_id.startswith("customfield_")
        if not include_system and not is_custom:
            continue
        fields.append(_build_field_data(field_id, field_info))
    return fields


def _extract_createmeta_fields(meta: dict[str, Any], project: str, issuetype: str) -> dict[str, Any]:
    found_project = None
    for p in meta.get("projects", []) or []:
        project_key = str(p.get("key", ""))
        project_id = str(p.get("id", ""))
        if project_key.lower() == project.lower() or project_id == project:
            found_project = p
            break
    if not found_project:
        raise typer.BadParameter(f"Project '{project}' not found in metadata response")

    found_issuetype = None
    for it in found_project.get("issuetypes", []) or []:
        it_name = str(it.get("name", ""))
        it_id = str(it.get("id", ""))
        if it_name.lower() == issuetype.lower() or it_id == issuetype:
            found_issuetype = it
            break
    if not found_issuetype:
        available_types = [it.get("name") for it in found_project.get("issuetypes", [])]
        raise typer.BadParameter(
            f"Issue type '{issuetype}' not found in project '{project}'. Available types: {available_types}"
        )

    return found_issuetype.get("fields", {})


def _extract_required_field_ref(message: str) -> str | None:
    match = re.search(r"(?:Field ['\"])?(.+?)(?:['\"])? is required", message, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_error_field_refs(message: str) -> list[str]:
    refs: set[str] = set()
    required_ref = _extract_required_field_ref(message)
    if required_ref:
        refs.add(required_ref)

    for ref in re.findall(r"customfield_\d+", message, re.IGNORECASE):
        refs.add(ref)

    errors_match = re.search(r"errors\s*[:=]\s*{([^}]+)}", message, re.IGNORECASE)
    if errors_match:
        for key in re.findall(r"[\"']([A-Za-z][A-Za-z0-9_]+)[\"']\s*:", errors_match.group(1)):
            if key not in {"errorMessages", "errors"}:
                refs.add(key)

    return [ref for ref in sorted(refs) if ref]


def _match_fields_by_refs(fields: list[dict[str, Any]], refs: Sequence[str]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ref in refs:
        token = ref.strip().lower()
        if not token:
            continue
        for field in fields:
            field_id = str(field.get("id") or "")
            field_name = str(field.get("name") or "")
            if token in field_id.lower() or token in field_name.lower():
                if field_id and field_id in seen:
                    continue
                matched.append(field)
                if field_id:
                    seen.add(field_id)
    return matched


def _format_allowed_values(allowed_values: list[dict[str, str]], limit: int = 20) -> str:
    if not allowed_values:
        return ""
    parts: list[str] = []
    for item in allowed_values[:limit]:
        value = item.get("value") or ""
        ident = item.get("id") or ""
        if ident:
            parts.append(f"{value} (id: {ident})")
        else:
            parts.append(value)
    if len(allowed_values) > limit:
        parts.append(f"... (+{len(allowed_values) - limit} more)")
    return ", ".join([p for p in parts if p])


# ---------------------------------------------------------------------------
# Remote link helpers
# ---------------------------------------------------------------------------


def _build_remote_link_payload(
    *,
    url: str | None,
    title: str | None,
    summary: str | None,
    relationship: str | None,
    global_id: str | None,
    application_type: str | None,
    application_name: str | None,
    icon_url: str | None,
    icon_title: str | None,
    data_file: Path | None,
) -> dict[str, Any]:
    if data_file:
        if not data_file.exists():
            raise typer.BadParameter(f"Data file not found: {data_file}")
        try:
            with data_file.open() as f:
                parsed = json.load(f)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON in {data_file}: {exc}") from exc
        if not isinstance(parsed, dict):
            raise typer.BadParameter("Remote link data file must contain a JSON object")
        return parsed

    if not url:
        raise typer.BadParameter("--url required when --data-file is not provided")

    payload: dict[str, Any] = {"object": {"url": url}}

    if title:
        payload["object"]["title"] = title
    if summary:
        payload["object"]["summary"] = summary
    if icon_url:
        icon: dict[str, Any] = {"url16x16": icon_url}
        if icon_title:
            icon["title"] = icon_title
        payload["object"]["icon"] = icon
    if relationship:
        payload["relationship"] = relationship
    if global_id:
        payload["globalId"] = global_id
    if application_type or application_name:
        if not (application_type and application_name):
            raise typer.BadParameter("--application-type and --application-name must be provided together")
        payload["application"] = {"type": application_type, "name": application_name}

    return payload


# Global state for report directory and markdown flag
_report_dir_global: Path = _REPORT_DIR
_markdown_global: bool = True
_reports_global: bool = True


@app.callback(invoke_without_command=True)
def main(
    report_dir: Path | None = typer.Option(None, help=f"Directory for run reports (default: {_REPORT_DIR})"),
    markdown: bool = typer.Option(True, help="Emit Markdown summaries alongside JSON reports"),
    reports: bool = typer.Option(True, "--reports/--no-reports", help="Persist run reports to disk"),
    json_only: bool = typer.Option(
        False,
        "--json-only",
        help="Emit JSON to stdout only (disables reports and markdown)",
    ),
    structured_logs: bool = typer.Option(
        False, "--structured-logs/--no-structured-logs", help="Emit structured JSON logs to stderr"
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show vds-jira-orchestrator version and exit",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(f"{APP_NAME} {APP_VERSION}")
        raise typer.Exit() from None
    global _report_dir_global, _markdown_global, _reports_global
    if json_only:
        markdown = False
        reports = False
    _report_dir_global = report_dir.resolve() if report_dir else _REPORT_DIR
    _markdown_global = markdown
    _reports_global = reports
    if structured_logs or json_only:
        configure_structlog(
            json_logs=structured_logs, quiet=json_only and not structured_logs, cache_logger=structured_logs
        )
    if structured_logs:
        global logger
        logger = structlog.get_logger("jira_cli")  # type: ignore[assignment]


def _record_summary(
    *, command: str, args: list[str], exit_code: int, started_at: datetime, finished_at: datetime
) -> None:
    global _report_dir_global, _markdown_global
    summary = RunSummary(
        command=command,
        args=args,
        exit_code=exit_code,
        duration_ms=int((finished_at - started_at).total_seconds() * 1000),
        started_at=started_at,
        finished_at=finished_at,
    )
    if _reports_global:
        write_reports(summary, base_dir=_report_dir_global, include_markdown=_markdown_global)


@app.command("projects")
def cmd_projects(
    search: str | None = typer.Option(
        None,
        "--search",
        "-s",
        help="Case-insensitive substring filter on project name or key",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-l",
        help="Maximum number of projects to return (applied after filtering)",
    ),
) -> None:
    """List JIRA projects accessible to the current user."""
    started_at = datetime.now(UTC)
    code = 0
    args_summary = []
    if search:
        args_summary.append(f"search={search}")
    if limit is not None:
        args_summary.append(f"limit={limit}")
    try:
        s = load_settings(strict=True)
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.list_projects()

        if search:
            needle = search.lower()
            payload = [p for p in payload if needle in p.get("name", "").lower() or needle in p.get("key", "").lower()]
        if limit is not None:
            payload = payload[:limit]

        _emit_json({"count": len(payload), "projects": payload})
    except (AuthError, VDSClientError, SettingsError) as exc:
        code = 1
        logger.exception("projects_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="projects",
            args=args_summary,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("component")
def cmd_component(
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    project_key: str | None = typer.Option(None, "--project-key", "-P", help="Project key (for list)"),
    component_id: str | None = typer.Option(None, "--component-id", "-c", help="Component ID (for get/update/delete)"),
    name: str | None = typer.Option(None, "--name", help="Component name (for create/update)"),
    description: str | None = typer.Option(None, "--description", help="Component description"),
    lead_account_id: str | None = typer.Option(None, "--lead-account-id", help="Account ID of component lead"),
    assignee_type: str | None = typer.Option(
        None, "--assignee-type", help="Assignee type (e.g., PROJECT_LEAD, COMPONENT_LEAD)"
    ),
    is_assignee_type_valid: bool | None = typer.Option(
        None, "--assignee-valid/--no-assignee-valid", help="Assignee validity flag"
    ),
    data_file: Path | None = typer.Option(None, "--data-file", help="JSON file for component payload"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (create/update/delete)"),
) -> None:
    """Manage project components."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [
        action,
        f"project_key={project_key}",
        f"component_id={component_id}",
        f"data_file={data_file}",
    ]

    def _build_payload() -> dict[str, Any]:
        if data_file:
            if not data_file.exists():
                raise typer.BadParameter(f"Data file not found: {data_file}")
            try:
                parsed = json.loads(data_file.read_text())
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(f"Invalid JSON in {data_file}: {exc}") from exc
            if not isinstance(parsed, dict):
                raise typer.BadParameter("--data-file must contain a JSON object")
            return parsed
        payload: dict[str, Any] = {}
        if name:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if lead_account_id:
            payload["leadAccountId"] = lead_account_id
        if assignee_type:
            payload["assigneeType"] = assignee_type
        if is_assignee_type_valid is not None:
            payload["isAssigneeTypeValid"] = is_assignee_type_valid
        if not payload:
            raise typer.BadParameter("Provide --data-file or at least one field option for create/update")
        return payload

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            if not project_key:
                raise typer.BadParameter("--project-key required for list")
            project = adapter.get_project(project_key, expand="components")
            components = project.get("components", []) if isinstance(project, dict) else []
            _emit_json({"count": len(components), "components": components})

        elif action == "get":
            if not component_id:
                raise typer.BadParameter("--component-id required for get")
            payload = adapter.get_component(component_id)
            _emit_json(payload)

        elif action == "create":
            if not yes:
                raise typer.BadParameter("--yes required for create")
            payload = _build_payload()
            if (
                not project_key
                and "project" not in payload
                and "projectId" not in payload
                and "projectKey" not in payload
            ):
                raise typer.BadParameter(
                    "--project-key required (or include project/projectId in --data-file) for create"
                )
            if project_key and "project" not in payload and "projectId" not in payload:
                payload["project"] = project_key
            result = adapter.create_component(payload)
            _emit_json(result)

        elif action == "update":
            if not yes:
                raise typer.BadParameter("--yes required for update")
            if not component_id:
                raise typer.BadParameter("--component-id required for update")
            payload = _build_payload()
            result = adapter.update_component(payload, component_id)
            _emit_json(result)

        elif action == "delete":
            if not yes:
                raise typer.BadParameter("--yes required for delete")
            if not component_id:
                raise typer.BadParameter("--component-id required for delete")
            adapter.delete_component(component_id)
            _emit_json({"status": "deleted", "component_id": component_id})

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("component_command_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="component",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("version")
def cmd_version(
    action: str = typer.Argument(..., help="Action: list, create, update"),
    project_key: str | None = typer.Option(None, "--project-key", "-P", help="Project key (for list/create)"),
    project_id: str | None = typer.Option(None, "--project-id", help="Project ID (for create)"),
    version_id: str | None = typer.Option(None, "--version-id", help="Version ID (for update)"),
    name: str | None = typer.Option(None, "--name", help="Version name (for create/update)"),
    description: str | None = typer.Option(None, "--description", help="Version description (for update)"),
    start: int | None = typer.Option(None, "--start", help="Start index for pagination (for list)"),
    limit: int | None = typer.Option(None, "--limit", help="Limit for pagination (for list)"),
    order_by: str | None = typer.Option(
        None, "--order-by", help="Order by field: sequence, name, startDate, releaseDate (for list)"
    ),
    query: str | None = typer.Option(None, "--query", help="Query filter (for list)"),
    status: str | None = typer.Option(None, "--status", help="Status filter (for list)"),
    archived: bool | None = typer.Option(None, "--archived/--no-archived", help="Archived flag (for create/update)"),
    released: bool | None = typer.Option(None, "--released/--no-released", help="Released flag (for create/update)"),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (YYYY-MM-DD) (for update)"),
    release_date: str | None = typer.Option(None, "--release-date", help="Release date (YYYY-MM-DD) (for update)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (create/update)"),
) -> None:
    """Manage project versions."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [
        action,
        f"project_key={project_key}",
        f"project_id={project_id}",
        f"version_id={version_id}",
        f"name={name}",
    ]

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            if not project_key:
                raise typer.BadParameter("--project-key required for list")
            payload = adapter.get_project_versions_paginated(
                project_key=project_key,
                start=start,
                limit=limit,
                order_by=order_by,
                query=query,
                status=status,
            )
            _emit_json(payload)

        elif action == "create":
            if not yes:
                raise typer.BadParameter("Refusing to create version without --yes")
            if not project_key:
                raise typer.BadParameter("--project-key required for create")
            if not project_id:
                raise typer.BadParameter("--project-id required for create")
            if not name:
                raise typer.BadParameter("--name required for create")
            result = adapter.add_version(
                key=project_key,
                project_id=project_id,
                version=name,
                is_archived=archived if archived is not None else False,
                is_released=released if released is not None else False,
            )
            _emit_json(result)

        elif action == "update":
            if not yes:
                raise typer.BadParameter("Refusing to update version without --yes")
            if not version_id:
                raise typer.BadParameter("--version-id required for update")
            # At least one field must be provided for update
            if not any(
                [name, description is not None, archived is not None, released is not None, start_date, release_date]
            ):
                raise typer.BadParameter(
                    "At least one update field required (--name, --description, --archived, --released, --start-date, --release-date)"
                )
            result = adapter.update_version(
                version=version_id,
                name=name,
                description=description,
                is_archived=archived,
                is_released=released,
                start_date=start_date,
                release_date=release_date,
            )
            _emit_json(result)

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("version_command_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="version",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("search")
def cmd_search(
    jql: str = typer.Argument(..., help="JQL query string"),
    limit: int = typer.Option(25, "--limit", help="Number of results"),
    fields: str | None = typer.Option(None, "--fields", help="Comma separated fields"),
    start: int = typer.Option(0, "--start", help="Start index for pagination (advanced search)"),
    advanced: bool = typer.Option(False, "--advanced", help="Use advanced search with pagination"),
    json_only: bool = typer.Option(False, "--json-only", help="Emit JSON payload for this command"),
) -> None:
    """Search issues using JQL. Use --advanced for pagination support."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        fields_list = [f.strip() for f in fields.split(",")] if fields else None
        if advanced or start > 0:
            payload = adapter.search_issues_advanced(jql, start=start, limit=limit, fields=fields_list)
        else:
            payload = adapter.jql(jql, limit=limit, fields=fields_list)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("search_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        args_list = [jql, f"limit={limit}"]
        if start > 0:
            args_list.append(f"start={start}")
        if advanced:
            args_list.append("advanced=True")
        if json_only:
            args_list.append("json_only=True")
        _record_summary(
            command="search",
            args=args_list,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("search-by-filter")
def cmd_search_by_filter(
    filter_id: int = typer.Argument(..., help="Filter ID"),
    limit: int = typer.Option(50, "--limit", help="Number of results"),
    fields: str | None = typer.Option(None, "--fields", help="Comma separated fields"),
    start: int = typer.Option(0, "--start", help="Start index for pagination"),
) -> None:
    """Search issues using a saved filter."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        fields_list = [f.strip() for f in fields.split(",")] if fields else None
        payload = adapter.search_issues_by_filter(filter_id, start=start, limit=limit, fields=fields_list)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("search_by_filter_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        args_list = [str(filter_id), f"limit={limit}"]
        if start > 0:
            args_list.append(f"start={start}")
        _record_summary(
            command="search-by-filter",
            args=args_list,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue")
def cmd_issue(
    key: str = typer.Argument(..., help="Issue key (e.g., NTTC-123)"),
) -> None:
    """Show details for a single JIRA issue by key."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.get_issue(key)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("issue_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(command="issue", args=[key], exit_code=code, started_at=started_at, finished_at=finished_at)
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("bulk-update")
def cmd_bulk_update(
    issue_keys: str = typer.Option(..., "--issue-keys", help="Comma-separated issue keys (e.g., NTTC-1,NTTC-2)"),
    fields: str | None = typer.Option(None, "--fields", help="JSON string or '*all' for all fields"),
    fields_file: Path | None = typer.Option(None, "--fields-file", help="JSON file containing field updates"),
    yes: bool = typer.Option(False, "--yes", help="Confirm bulk update operation"),
) -> None:
    """Bulk update multiple issues."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [f"issue_keys={issue_keys}", f"fields_file={fields_file}"]

    def _load_fields() -> str:
        if fields_file:
            if not fields_file.exists():
                raise typer.BadParameter(f"Fields file not found: {fields_file}")
            try:
                parsed = json.loads(fields_file.read_text())
                return json.dumps(parsed)
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(f"Invalid JSON in {fields_file}: {exc}") from exc
        if fields:
            # Validate JSON if provided
            if fields != "*all":
                try:
                    json.loads(fields)
                except json.JSONDecodeError as exc:
                    raise typer.BadParameter(f"Invalid JSON in --fields: {exc}") from exc
            return fields
        return "*all"

    try:
        if not yes:
            raise typer.BadParameter("Refusing to bulk update issues without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        key_list = [k.strip() for k in issue_keys.split(",") if k.strip()]
        if not key_list:
            raise typer.BadParameter("At least one issue key required in --issue-keys")
        fields_value = _load_fields()
        result = adapter.bulk_update_issue_field(key_list=key_list, fields=fields_value)
        _emit_json(result)

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("bulk_update_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="bulk-update",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("field-append")
def cmd_field_append(
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    field: str = typer.Option(..., "--field", help="Field ID (e.g., customfield_10000)"),
    value: str | None = typer.Option(None, "--value", help="JSON string value to append"),
    value_file: Path | None = typer.Option(None, "--value-file", help="JSON file containing value to append"),
    no_notify: bool = typer.Option(False, "--no-notify", help="Don't notify users"),
    yes: bool = typer.Option(False, "--yes", help="Confirm field append operation"),
) -> None:
    """Append value to issue field (for multi-select fields)."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [f"issue_key={issue_key}", f"field={field}", f"value_file={value_file}"]

    def _load_value() -> dict[str, Any]:
        if value_file:
            if not value_file.exists():
                raise typer.BadParameter(f"Value file not found: {value_file}")
            try:
                parsed = json.loads(value_file.read_text())
                if not isinstance(parsed, dict):
                    raise typer.BadParameter("--value-file must contain a JSON object")
                return parsed
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(f"Invalid JSON in {value_file}: {exc}") from exc
        if not value:
            raise typer.BadParameter("Provide --value or --value-file")
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise typer.BadParameter("--value must be a JSON object")
            return parsed
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON in --value: {exc}") from exc

    try:
        if not yes:
            raise typer.BadParameter("Refusing to append field value without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        value_dict = _load_value()
        result = adapter.issue_field_value_append(
            issue_id_or_key=issue_key, field=field, value=value_dict, notify_users=not no_notify
        )
        _emit_json(result)

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("field_append_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="field-append",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue-archive")
def cmd_issue_archive(
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm archive operation"),
) -> None:
    """Archive an issue."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [f"issue_key={issue_key}"]

    try:
        if not yes:
            raise typer.BadParameter("Refusing to archive issue without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        adapter.issue_archive(issue_key)
        _emit_json({"status": "archived", "issue_key": issue_key})

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("issue_archive_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="issue-archive",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue-restore")
def cmd_issue_restore(
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm restore operation"),
) -> None:
    """Restore an archived issue."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [f"issue_key={issue_key}"]

    try:
        if not yes:
            raise typer.BadParameter("Refusing to restore issue without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        adapter.issue_restore(issue_key)
        _emit_json({"status": "restored", "issue_key": issue_key})

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("issue_restore_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="issue-restore",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("property")
def cmd_property(
    action: str = typer.Argument(..., help="Action: get, set"),
    property_id: str | None = typer.Option(None, "--property-id", help="Property ID (for set)"),
    key: str | None = typer.Option(None, "--key", help="Property key (for get)"),
    permission_level: str | None = typer.Option(None, "--permission-level", help="Permission level (for get)"),
    key_filter: str | None = typer.Option(None, "--key-filter", help="Key filter pattern (for get)"),
    value: str | None = typer.Option(None, "--value", help="Property value (for set)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for set)"),
) -> None:
    """Manage JIRA application properties."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [action]

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "get":
            summary_args.extend([f"key={key}", f"permission_level={permission_level}", f"key_filter={key_filter}"])
            payload = adapter.get_property(key=key, permission_level=permission_level, key_filter=key_filter)
            _emit_json(payload)

        elif action == "set":
            if not yes:
                raise typer.BadParameter("Refusing to set property without --yes")
            if not property_id:
                raise typer.BadParameter("--property-id required for set")
            if value is None:
                raise typer.BadParameter("--value required for set")
            summary_args.extend([f"property_id={property_id}", f"value={value}"])
            adapter.set_property(property_id, value)
            _emit_json({"status": "set", "property_id": property_id, "value": value})

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("property_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="property",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("settings")
def cmd_settings(
    action: str = typer.Argument(..., help="Action: advanced"),
) -> None:
    """Manage JIRA settings."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [action]

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "advanced":
            payload = adapter.get_advanced_settings()
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("settings_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="settings",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("create")
def cmd_create(
    project: str = typer.Option(..., "--project", help="Project key"),
    issuetype: str = typer.Option(..., "--issuetype", help="Issue type name (e.g., Task, Bug)"),
    summary: str = typer.Option(..., "--summary", help="Summary"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    assignee: str | None = typer.Option(None, "--assignee", help="Assignee username (Server/DC)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels"),
    set_field: list[str] = typer.Option(
        [], "--set", help="Additional key=value field pairs (e.g., customfield_12345=10001)"
    ),
    set_json: bool = typer.Option(
        False,
        "--set-json",
        help="Allow JSON scalar values (e.g., true, 1) in --set (default: objects/arrays only)",
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate payload without sending"),
) -> None:
    """Create a new JIRA issue."""
    started_at = datetime.now(UTC)
    code = 0
    args = [f"project={project}", f"issuetype={issuetype}"]
    try:
        if not yes and not dry_run:
            raise typer.BadParameter("Refusing to create without --yes (or use --dry-run)")

        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        label_list = [x.strip() for x in labels.split(",")] if labels else None
        extras = _parse_set(set_field, allow_scalar_json=set_json) if set_field else {}

        # Build core payload
        payload = {
            "project": {"key": project},
            "summary": summary,
            "issuetype": {"name": issuetype},
        }
        if description:
            payload["description"] = description
        if assignee:
            payload["assignee"] = {"name": assignee}
        if label_list:
            payload["labels"] = label_list
        if extras:
            payload.update(extras)

        if dry_run:
            typer.echo(f"[DRY RUN] Validating payload for {project} / {issuetype}...", err=True)

            # Basic validation: Check if required fields from metadata are present
            # This is "best effort" validation
            field_name_map: dict[str, str] = {}
            try:
                meta = adapter.get_createmeta(project_key=project, expand="projects.issuetypes.fields")

                # Find project and issuetype
                found_it = None
                if "projects" in meta:
                    for p in meta["projects"]:
                        project_key = str(p.get("key", ""))
                        project_id = str(p.get("id", ""))
                        if project_key.lower() == project.lower() or project_id == project:
                            for it in p.get("issuetypes", []):
                                it_name = str(it.get("name", ""))
                                it_id = str(it.get("id", ""))
                                if it_name.lower() == issuetype.lower() or it_id == issuetype:
                                    found_it = it
                                    break

                if found_it:
                    missing = []
                    fields_meta = found_it.get("fields", {})
                    field_name_map = {
                        fid: str(fmeta.get("name"))
                        for fid, fmeta in fields_meta.items()
                        if isinstance(fmeta, dict) and fmeta.get("name")
                    }
                    for fid, fmeta in fields_meta.items():
                        if fmeta.get("required") and not fmeta.get("hasDefaultValue"):
                            # Check if field is in payload
                            # Note: Payload keys might be field IDs (customfield_X) or system names (summary)
                            # We need to check both
                            fname = fmeta.get("name", "").lower()
                            if fid not in payload and fname not in payload:
                                # Special case mapping for standard fields that might match
                                is_present = False
                                if fid in {"issuetype", "project"}:
                                    is_present = True

                                if not is_present:
                                    missing.append(f"{fmeta.get('name')} ({fid})")

                    if missing:
                        typer.echo("[DRY RUN] ⚠️  Warning: The following REQUIRED fields appear missing:", err=True)
                        for m in missing:
                            typer.echo(f"  - {m}", err=True)
                        typer.echo("Tip: Use --set to provide them.", err=True)
                    else:
                        typer.echo("[DRY RUN] ✅  All required fields appear to be present.", err=True)
            except Exception as e:
                typer.echo(f"[DRY RUN] Metadata validation skipped due to warning: {e}", err=True)

            output = {"dry_run": True, "payload": payload}
            if field_name_map:
                output["field_name_map"] = field_name_map
            _emit_json(output)
            return

        # Execute creation
        res = adapter.create_issue(
            project_key=project,
            summary=summary,
            issuetype=issuetype,
            description=description,
            assignee=assignee,
            labels=label_list or [],
            extra_fields=extras,
        )
        _emit_json(res)

    except VDSClientError as exc:
        code = 1
        msg = str(exc)
        logger.exception("create_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)

        required_ref = _extract_required_field_ref(msg)
        field_refs = _extract_error_field_refs(msg)
        matched_fields: list[dict[str, Any]] = []

        if field_refs:
            try:
                meta = adapter.get_createmeta(project_key=project, issuetype=issuetype)
                raw_fields = _extract_createmeta_fields(meta, project, issuetype)
                all_fields = _collect_fields(raw_fields, field_filter=None, include_system=True)
                matched_fields = _match_fields_by_refs(all_fields, field_refs)
            except Exception:
                matched_fields = []

        if matched_fields:
            typer.echo("\n--- Field Details ---", err=True)
            for field_data in matched_fields:
                field_name = field_data.get("name") or ""
                field_id = field_data.get("id") or ""
                typer.echo(f"Field: {field_name} (id: {field_id})", err=True)
                allowed_values = field_data.get("allowedValues") or []
                allowed_text = _format_allowed_values(allowed_values)
                if allowed_text:
                    typer.echo(f"  Allowed values: {allowed_text}", err=True)

        if required_ref:
            set_field_ref = required_ref
            if matched_fields:
                for field_data in matched_fields:
                    field_id = str(field_data.get("id") or "")
                    field_name = str(field_data.get("name") or "")
                    if required_ref.lower() in field_id.lower() or required_ref.lower() in field_name.lower():
                        if field_id:
                            set_field_ref = field_id
                        break
            typer.echo("\n--- Troubleshooting Guide ---", err=True)
            typer.echo(f"It looks like a required field '{required_ref}' is missing.", err=True)
            typer.echo("To find the correct ID and allowed values, run:", err=True)
            typer.echo(
                f"  vds-cli jira discover-fields --project {project} --issuetype {issuetype} "
                f'--include-system --field "{required_ref}"',
                err=True,
            )
            typer.echo("\nThen use --set to provide the value:", err=True)
            typer.echo(f'  --set \'{set_field_ref}={{"value": "..."}}\'', err=True)

    except (AuthError, typer.BadParameter) as exc:
        code = 1
        logger.exception("create_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="create",
            args=[*args, f"set_json={set_json}", f"dry_run={dry_run}", f"yes={yes}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("update")
def cmd_update(
    key: str = typer.Argument(..., help="Issue key"),
    set_field: list[str] = typer.Option([], "--set", help="key=value pairs to update (repeatable)"),
    set_json: bool = typer.Option(
        False,
        "--set-json",
        help="Allow JSON scalar values (e.g., true, 1) in --set (default: objects/arrays only)",
    ),
    add_label: list[str] = typer.Option([], "--add-label", help="Labels to add"),
    remove_label: list[str] = typer.Option([], "--remove-label", help="Labels to remove"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate payload without sending"),
) -> None:
    """Update fields on an existing JIRA issue."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        if not yes and not dry_run:
            raise typer.BadParameter("Refusing to update without --yes (or use --dry-run)")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        fields: dict[str, Any] = _parse_set(set_field, allow_scalar_json=set_json)
        if add_label or remove_label:
            current = adapter.get_issue(key)
            cur_labels = list(current.get("fields", {}).get("labels") or [])
            if add_label:
                cur_labels = sorted(set(cur_labels + add_label))
            if remove_label:
                cur_labels = [label for label in cur_labels if label not in set(remove_label)]
            fields["labels"] = cur_labels
        if dry_run and not yes:
            _emit_json({"dry_run": True, "request": {"key": key, "fields": fields}})
        else:
            res = adapter.update_issue_fields(key, fields)
            _emit_json(res)
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("update_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="update",
            args=[
                key,
                *set_field,
                f"set_json={set_json}",
                f"add_label={add_label}",
                f"remove_label={remove_label}",
                f"dry_run={dry_run}",
                f"yes={yes}",
            ],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("comment")
def cmd_comment(
    key: str = typer.Argument(..., help="Issue key"),
    message: str = typer.Option(..., "--message", help="Comment message"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Add a comment to a JIRA issue."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        if not yes:
            raise typer.BadParameter("Refusing to comment without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        res = adapter.add_comment(key, message)
        _emit_json(res)
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("comment_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(command="comment", args=[key], exit_code=code, started_at=started_at, finished_at=finished_at)
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("transition")
def cmd_transition(
    key: str = typer.Argument(..., help="Issue key"),
    to: str = typer.Option(..., "--to", help="Target status name"),
    admin: bool = typer.Option(False, "--admin", help="Acknowledge administrative action"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Transition a JIRA issue to a new workflow status."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        if not (admin and yes):
            raise typer.BadParameter("Refusing to transition without --admin and --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        adapter.transition_issue(key, to)
        _emit_json({"key": key, "transitioned_to": to})
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("transition_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="transition", args=[key, f"to={to}"], exit_code=code, started_at=started_at, finished_at=finished_at
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("delete")
def cmd_delete(
    key: str = typer.Argument(..., help="Issue key"),
    yes: bool = typer.Option(False, "--yes", help="Confirm deletion"),
    force: bool = typer.Option(False, "--force", help="Double confirm deletion"),
) -> None:
    """Delete a JIRA issue (requires permissions)."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        if not (yes and force):
            raise typer.BadParameter("Refusing to delete without --yes and --force")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        adapter.delete_issue(key)
        _emit_json({"deleted": key})
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("delete_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(command="delete", args=[key], exit_code=code, started_at=started_at, finished_at=finished_at)
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("createmeta")
def cmd_createmeta(
    project: str = typer.Option(..., "--project", help="Project key"),
    issuetype: str = typer.Option(..., "--issuetype", help="Issue type name"),
    expand: str | None = typer.Option(None, "--expand", help="Expand options"),
) -> None:
    """Get create metadata for issue creation (field definitions, allowed values)."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.get_createmeta(project_key=project, issuetype=issuetype, expand=expand)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("createmeta_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="createmeta",
            args=[f"project={project}", f"issuetype={issuetype}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("custom-fields")
def cmd_custom_fields(
    search: str | None = typer.Option(None, "--search", help="Search filter"),
    start: int = typer.Option(1, "--start", help="Start index"),
    limit: int = typer.Option(50, "--limit", help="Number of results"),
) -> None:
    """Get existing custom fields or find by filter."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.get_custom_fields(search=search, start=start, limit=limit)
        _emit_json({"count": len(payload), "custom_fields": payload})
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("custom_fields_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="custom-fields",
            args=[f"search={search}", f"start={start}", f"limit={limit}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("board")
def cmd_board(
    action: str = typer.Argument(..., help="Action: list, get, create, delete, config, issues, properties, velocity"),
    board_id: int | None = typer.Option(None, "--board-id", help="Board ID"),
    filter_id: int | None = typer.Option(None, "--filter-id", help="Filter ID (for create/get-by-filter)"),
    name: str | None = typer.Option(None, "--name", help="Board name (for create)"),
    board_type: str | None = typer.Option(None, "--type", help="Board type: scrum, kanban (for create)"),
    project_key: str | None = typer.Option(None, "--project", help="Project key (for list)"),
    limit: int = typer.Option(50, "--limit", help="Number of results"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Agile board operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_all_agile_boards(project_key=project_key, board_type=board_type, start=0, limit=limit)
            _emit_json({"count": len(payload), "boards": payload})
        elif action == "get":
            if not board_id and not filter_id:
                raise typer.BadParameter("Either --board-id or --filter-id required")
            if filter_id:
                payload = adapter.get_agile_board_by_filter_id(filter_id)
            else:
                payload = adapter.get_agile_board(board_id)  # type: ignore[arg-type]
            _emit_json(payload)
        elif action == "create":
            if not yes:
                raise typer.BadParameter("Refusing to create without --yes")
            if not name or not board_type or not filter_id:
                raise typer.BadParameter("--name, --type, and --filter-id required for create")
            payload = adapter.create_agile_board(name, board_type, filter_id)
            _emit_json(payload)
        elif action == "delete":
            if not (yes and board_id):
                raise typer.BadParameter("Refusing to delete without --yes and --board-id")
            adapter.delete_agile_board(board_id)  # type: ignore[arg-type]
            _emit_json({"deleted": board_id})
        elif action == "config":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_agile_board_configuration(board_id)  # type: ignore[arg-type]
            _emit_json(payload)
        elif action == "issues":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_issues_for_board(board_id)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "issues": payload})
        elif action == "properties":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_agile_board_properties(board_id)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "properties": payload})
        elif action == "velocity":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_agile_board_refined_velocity(board_id)  # type: ignore[arg-type]
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("board_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="board",
            args=[action, f"board_id={board_id}", f"limit={limit}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("epic")
def cmd_epic(
    action: str = typer.Argument(..., help="Action: issues, list, issues-for-epic"),
    epic_key: str | None = typer.Option(None, "--epic-key", help="Epic key (for issues)"),
    board_id: int | None = typer.Option(None, "--board-id", help="Board ID (for list/issues-for-epic)"),
    epic_id: int | None = typer.Option(None, "--epic-id", help="Epic ID (for issues-for-epic)"),
    done: bool = typer.Option(False, "--done", help="Include done epics (for list)"),
    limit: int = typer.Option(50, "--limit", help="Number of results"),
) -> None:
    """Epic operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "issues":
            if not epic_key:
                raise typer.BadParameter("--epic-key required")
            payload = adapter.epic_issues(epic_key)
            _emit_json({"count": len(payload), "issues": payload})
        elif action == "list":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_epics(board_id, done=done, start=0, limit=limit)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "epics": payload})
        elif action == "issues-for-epic":
            if not board_id or not epic_id:
                raise typer.BadParameter("--board-id and --epic-id required")
            payload = adapter.get_issues_for_epic(
                board_id, epic_id, jql="", validate_query="", fields="*all", expand="", start=0, limit=limit
            )  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "issues": payload})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("epic_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="epic",
            args=[action, f"epic_key={epic_key}", f"board_id={board_id}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("sprint")
def cmd_sprint(
    action: str = typer.Argument(..., help="Action: list, issues, versions, create, rename, add-issues"),
    board_id: int | None = typer.Option(None, "--board-id", help="Board ID"),
    sprint_id: int | None = typer.Option(None, "--sprint-id", help="Sprint ID"),
    state: str | None = typer.Option(None, "--state", help="Sprint state filter"),
    sprint_name: str | None = typer.Option(None, "--name", help="Sprint name (for create/rename)"),
    start_date: str | None = typer.Option(None, "--start-date", help="Start date (for create/rename)"),
    end_date: str | None = typer.Option(None, "--end-date", help="End date (for create/rename)"),
    goal: str | None = typer.Option(None, "--goal", help="Sprint goal (for create)"),
    issues: str | None = typer.Option(None, "--issues", help="Comma-separated issue keys (for add-issues)"),
    limit: int = typer.Option(50, "--limit", help="Number of results"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Sprint operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_all_sprints_from_board(board_id, state=state, start=0, limit=limit)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "sprints": payload})
        elif action == "issues":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_all_issues_for_sprint_in_board(board_id, state=state, start=0, limit=limit)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "issues": payload})
        elif action == "versions":
            if not board_id:
                raise typer.BadParameter("--board-id required")
            payload = adapter.get_all_versions_from_board(board_id, start=0, limit=limit)  # type: ignore[arg-type]
            _emit_json({"count": len(payload), "versions": payload})
        elif action == "create":
            if not yes:
                raise typer.BadParameter("Refusing to create without --yes")
            if not sprint_name or not board_id:
                raise typer.BadParameter("--name and --board-id required for create")
            payload = adapter.create_sprint(
                sprint_name,
                board_id,
                start_datetime=start_date,
                end_datetime=end_date,
                goal=goal,  # type: ignore[arg-type]
            )
            _emit_json(payload)
        elif action == "rename":
            if not yes:
                raise typer.BadParameter("Refusing to rename without --yes")
            if not sprint_id:
                raise typer.BadParameter("--sprint-id required")
            payload = adapter.rename_sprint(sprint_id, name=sprint_name, start_date=start_date, end_date=end_date)  # type: ignore[arg-type]
            _emit_json(payload)
        elif action == "add-issues":
            if not yes:
                raise typer.BadParameter("Refusing to add issues without --yes")
            if not sprint_id or not issues:
                raise typer.BadParameter("--sprint-id and --issues required")
            issues_list = [i.strip() for i in issues.split(",")]
            adapter.add_issues_to_sprint(sprint_id, issues_list)  # type: ignore[arg-type]
            _emit_json({"sprint_id": sprint_id, "issues_added": issues_list})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("sprint_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="sprint",
            args=[action, f"board_id={board_id}", f"sprint_id={sprint_id}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("backlog")
def cmd_backlog(
    action: str = typer.Argument(..., help="Action: move, add"),
    issues: str = typer.Option(..., "--issues", help="Comma-separated issue keys"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Backlog operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        if not yes:
            raise typer.BadParameter("Refusing to modify backlog without --yes")
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        issues_list = [i.strip() for i in issues.split(",")]

        if action == "move":
            adapter.move_issues_to_backlog(issues_list)
            _emit_json({"action": "moved_to_backlog", "issues": issues_list})
        elif action == "add":
            adapter.add_issues_to_backlog(issues_list)
            _emit_json({"action": "added_to_backlog", "issues": issues_list})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("backlog_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="backlog",
            args=[action, f"issues={issues}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("worklog")
def cmd_worklog(
    action: str = typer.Argument(..., help="Action: get, add, updated, deleted"),
    issue_key: str | None = typer.Option(None, "--issue-key", help="Issue key (for get/add)"),
    time_spent: str | None = typer.Option(None, "--time-spent", help="Time spent (e.g., '2h 30m') (for add)"),
    comment: str | None = typer.Option(None, "--comment", help="Worklog comment (for add)"),
    started: str | None = typer.Option(None, "--started", help="Start datetime in ISO format (for add)"),
    time_sec: int | None = typer.Option(None, "--time-sec", help="Time in seconds (alternative to --time-spent)"),
    since: str | None = typer.Option(None, "--since", help="Timestamp for updated/deleted (YYYY-MM-DD HH:mm or ISO)"),
    expand: str | None = typer.Option(None, "--expand", help="Expand parameter (for updated)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Worklog operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "get":
            if not issue_key:
                raise typer.BadParameter("--issue-key required for get")
            payload = adapter.get_worklogs(issue_key)
            _emit_json(payload)
        elif action == "add":
            if not yes:
                raise typer.BadParameter("Refusing to add worklog without --yes")
            if not issue_key:
                raise typer.BadParameter("--issue-key required for add")
            if not time_spent and time_sec is None:
                raise typer.BadParameter("--time-spent or --time-sec required for add")
            payload = adapter.issue_add_worklog(
                issue_key=issue_key,
                time_spent=time_spent or "",
                comment=comment,
                started=started,
                time_sec=time_sec,
            )
            _emit_json(payload)
        elif action == "updated":
            if not since:
                raise typer.BadParameter("--since required for updated")
            payload = adapter.get_updated_worklogs(since, expand=expand)
            _emit_json(payload)
        elif action == "deleted":
            if not since:
                raise typer.BadParameter("--since required for deleted")
            payload = adapter.get_deleted_worklogs(since)
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("worklog_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="worklog",
            args=[action, f"issue_key={issue_key}", f"since={since}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("transitions")
def cmd_transitions(
    issue_key: str = typer.Argument(..., help="Issue key"),
) -> None:
    """Get available transitions for an issue."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        payload = adapter.get_issue_transitions(issue_key)
        _emit_json(payload)
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("transitions_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="transitions",
            args=[issue_key],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("changelog")
def cmd_changelog(
    action: str = typer.Argument(..., help="Action: get, status"),
    issue_key: str = typer.Argument(..., help="Issue key"),
    start: int | None = typer.Option(None, "--start", help="Start index for pagination"),
    limit: int | None = typer.Option(None, "--limit", help="Limit for pagination"),
) -> None:
    """Get issue changelog (change history)."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "get":
            payload = adapter.get_issue_changelog(issue_key, start=start, limit=limit)
            _emit_json(payload)
        elif action == "status":
            payload = adapter.get_issue_status_changelog(issue_key)
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("changelog_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="changelog",
            args=[action, issue_key, f"start={start}", f"limit={limit}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("filter")
def cmd_filter(
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    filter_id: int | None = typer.Option(None, "--filter-id", help="Filter ID (for get, update, delete)"),
    owner: str | None = typer.Option(None, "--owner", help="Owner username (for list)"),
    name: str | None = typer.Option(None, "--name", help="Filter name (for create, update)"),
    jql: str | None = typer.Option(None, "--jql", help="JQL query (for create, update)"),
    description: str | None = typer.Option(None, "--description", help="Filter description (for create, update)"),
    favourite: bool | None = typer.Option(
        None, "--favourite/--no-favourite", help="Mark as favourite (for create, update)"
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for create, update, delete)"),
) -> None:
    """Filter management operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_filters(owner=owner)
            _emit_json({"filters": payload, "count": len(payload)})
        elif action == "get":
            if not filter_id:
                raise typer.BadParameter("--filter-id required for get")
            payload = adapter.get_filter(filter_id)
            _emit_json(payload)
        elif action == "create":
            if not yes:
                raise typer.BadParameter("Refusing to create filter without --yes")
            if not name:
                raise typer.BadParameter("--name required for create")
            if not jql:
                raise typer.BadParameter("--jql required for create")
            payload = adapter.create_filter(
                name=name, jql=jql, description=description, favourite=favourite if favourite is not None else False
            )
            _emit_json(payload)
        elif action == "update":
            if not yes:
                raise typer.BadParameter("Refusing to update filter without --yes")
            if not filter_id:
                raise typer.BadParameter("--filter-id required for update")
            if not (name or jql or description is not None or favourite is not None):
                raise typer.BadParameter(
                    "At least one of --name, --jql, --description, or --favourite must be provided for update"
                )
            payload = adapter.update_filter(
                filter_id=filter_id, name=name, jql=jql, description=description, favourite=favourite
            )
            _emit_json(payload)
        elif action == "delete":
            if not yes:
                raise typer.BadParameter("Refusing to delete filter without --yes")
            if not filter_id:
                raise typer.BadParameter("--filter-id required for delete")
            adapter.delete_filter(filter_id)
            _emit_json({"status": "success", "filter_id": filter_id, "message": "Filter deleted"})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("filter_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        args_list: list[str] = [action]
        if filter_id:
            args_list.append(f"filter_id={filter_id}")
        if owner:
            args_list.append(f"owner={owner}")
        if name:
            args_list.append(f"name={name}")
        if jql:
            args_list.append(f"jql={jql}")
        if description:
            args_list.append(f"description={description}")
        if favourite is not None:
            args_list.append(f"favourite={favourite}")
        _record_summary(
            command="filter",
            args=args_list,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("dashboard")
def cmd_dashboard(
    action: str = typer.Argument(..., help="Action: get, list"),
    dashboard_id: str | None = typer.Option(None, "--dashboard-id", help="Dashboard ID (for get)"),
    filter_str: str | None = typer.Option(None, "--filter", help="Filter string (for list)"),
    start: int = typer.Option(0, "--start", help="Start index for pagination (for list)"),
    limit: int = typer.Option(10, "--limit", help="Limit for pagination (for list)"),
) -> None:
    """Dashboard operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "get":
            if not dashboard_id:
                raise typer.BadParameter("--dashboard-id required for get")
            # Try to parse as int, otherwise use as string
            try:
                dashboard_id_int = int(dashboard_id)
                payload = adapter.get_dashboard(dashboard_id_int)
            except ValueError:
                payload = adapter.get_dashboard(dashboard_id)
            _emit_json(payload)
        elif action == "list":
            payload = adapter.get_dashboards(filter=filter_str or "", start=start, limit=limit)
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("dashboard_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="dashboard",
            args=[action, f"dashboard_id={dashboard_id}", f"filter={filter_str}", f"start={start}", f"limit={limit}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue-link")
def cmd_issue_link(
    action: str = typer.Argument(..., help="Action: create, delete"),
    link_type: str | None = typer.Option(None, "--type", help="Issue link type name (e.g., Blocks)"),
    inward_issue: str | None = typer.Option(
        None, "--inward-issue", help="Inward issue key (the issue being blocked/related)"
    ),
    outward_issue: str | None = typer.Option(
        None, "--outward-issue", help="Outward issue key (the issue that blocks/relates)"
    ),
    link_id: str | None = typer.Option(None, "--link-id", help="Issue link ID (required for delete)"),
    comment: str | None = typer.Option(None, "--comment", help="Optional comment for the created link"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate payload without sending"),
) -> None:
    """Issue-to-issue link operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "create":
            if not yes and not dry_run:
                raise typer.BadParameter("--yes required for create (or use --dry-run)")
            if not link_type:
                raise typer.BadParameter("--type required for create")
            if not inward_issue:
                raise typer.BadParameter("--inward-issue required for create")
            if not outward_issue:
                raise typer.BadParameter("--outward-issue required for create")

            # Atlassian semantics for "Blocks":
            # - inwardIssue: issue on the "is blocked by" side (the blocker)
            # - outwardIssue: issue on the "blocks" side (the blocked issue)
            payload: dict[str, Any] = {
                "type": {"name": link_type},
                "inwardIssue": {"key": outward_issue},
                "outwardIssue": {"key": inward_issue},
            }
            if comment:
                payload["comment"] = {"body": comment}

            if dry_run and not yes:
                _emit_json({"dry_run": True, "request": payload})
            else:
                result = adapter.create_issue_link(payload)
                _emit_json(
                    {
                        "status": "created",
                        "type": link_type,
                        "inward_issue": inward_issue,
                        "outward_issue": outward_issue,
                        "result": result,
                    }
                )
        elif action == "delete":
            if not yes and not dry_run:
                raise typer.BadParameter("--yes required for delete (or use --dry-run)")
            if not link_id:
                raise typer.BadParameter("--link-id required for delete")

            parsed_link_id: str | int
            try:
                parsed_link_id = int(link_id)
            except ValueError:
                parsed_link_id = link_id

            if dry_run and not yes:
                _emit_json({"dry_run": True, "request": {"action": "delete", "link_id": parsed_link_id}})
            else:
                adapter.remove_issue_link(parsed_link_id)
                _emit_json({"status": "deleted", "link_id": parsed_link_id})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("issue_link_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="issue-link",
            args=[
                action,
                f"type={link_type}",
                f"inward_issue={inward_issue}",
                f"outward_issue={outward_issue}",
                f"link_id={link_id}",
                f"comment={comment}",
                f"yes={yes}",
                f"dry_run={dry_run}",
            ],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("link-type")
def cmd_link_type(
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    link_type_id: str | None = typer.Option(None, "--link-type-id", help="Link type ID (for get, update, delete)"),
    name: str | None = typer.Option(None, "--name", help="Link type name (for create, update)"),
    inward: str | None = typer.Option(None, "--inward", help="Inward description (for create, update)"),
    outward: str | None = typer.Option(None, "--outward", help="Outward description (for create, update)"),
    data_file: Path | None = typer.Option(
        None, "--data-file", help="JSON file with link type data (for create, update)"
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for create, update, delete)"),
) -> None:
    """Issue link type operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_issue_link_types()
            _emit_json({"count": len(payload), "link_types": payload})
        elif action == "get":
            if not link_type_id:
                raise typer.BadParameter("--link-type-id required for get")
            payload = adapter.get_issue_link_type(link_type_id)
            _emit_json(payload)
        elif action == "create":
            if not yes:
                raise typer.BadParameter("Refusing to create link type without --yes")
            if data_file:
                if not data_file.exists():
                    raise typer.BadParameter(f"Data file not found: {data_file}")
                with data_file.open() as f:
                    data = json.load(f)
            else:
                if not name or not inward or not outward:
                    raise typer.BadParameter("--name, --inward, and --outward required for create (or use --data-file)")
                data = {"name": name, "inward": inward, "outward": outward}
            payload = adapter.create_issue_link_type(data)
            _emit_json(payload)
        elif action == "update":
            if not yes:
                raise typer.BadParameter("Refusing to update link type without --yes")
            if not link_type_id:
                raise typer.BadParameter("--link-type-id required for update")
            if data_file:
                if not data_file.exists():
                    raise typer.BadParameter(f"Data file not found: {data_file}")
                with data_file.open() as f:
                    data = json.load(f)
            else:
                if not name or not inward or not outward:
                    raise typer.BadParameter("--name, --inward, and --outward required for update (or use --data-file)")
                data = {"name": name, "inward": inward, "outward": outward}
            payload = adapter.update_issue_link_type(link_type_id, data)
            _emit_json(payload)
        elif action == "delete":
            if not yes:
                raise typer.BadParameter("Refusing to delete link type without --yes")
            if not link_type_id:
                raise typer.BadParameter("--link-type-id required for delete")
            adapter.delete_issue_link_type(link_type_id)
            _emit_json({"status": "deleted", "link_type_id": link_type_id})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("link_type_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="link-type",
            args=[
                action,
                f"link_type_id={link_type_id}",
                f"name={name}",
                f"inward={inward}",
                f"outward={outward}",
                f"data_file={data_file}",
                f"yes={yes}",
            ],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("remote-link")
def cmd_remote_link(
    action: str = typer.Argument(..., help="Action: list, get, create, update, delete"),
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    remote_link_id: str | None = typer.Option(
        None, "--remote-link-id", "-r", help="Remote link ID (for get/update/delete)"
    ),
    url: str | None = typer.Option(None, "--url", help="Remote link target URL (for create/update)"),
    title: str | None = typer.Option(None, "--title", help="Remote link title"),
    summary: str | None = typer.Option(None, "--summary", help="Remote link summary/description"),
    relationship: str | None = typer.Option(None, "--relationship", help="Relationship description"),
    global_id: str | None = typer.Option(None, "--global-id", help="Global ID for remote link"),
    application_type: str | None = typer.Option(None, "--application-type", help="Application type for remote link"),
    application_name: str | None = typer.Option(None, "--application-name", help="Application name for remote link"),
    icon_url: str | None = typer.Option(None, "--icon-url", help="Icon URL for the remote link object"),
    icon_title: str | None = typer.Option(None, "--icon-title", help="Icon title for the remote link object"),
    data_file: Path | None = typer.Option(None, "--data-file", help="JSON file describing the remote link payload"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (create/update/delete)"),
) -> None:
    """Manage Jira issue remote links."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args: list[str] = [
        action,
        f"issue={issue_key}",
        f"remote_link_id={remote_link_id}",
        f"data_file={data_file}",
    ]

    def _parse_remote_link_identifier(value: str | None) -> str | int | None:
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return value

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_issue_remote_links(issue_key)
            _emit_json({"count": len(payload), "remote_links": payload})

        elif action == "get":
            remote_id = _parse_remote_link_identifier(remote_link_id)
            if remote_id is None:
                raise typer.BadParameter("--remote-link-id required for get")
            payload = adapter.get_issue_remote_link_by_id(issue_key, remote_id)
            _emit_json(payload)

        elif action == "create":
            if not yes:
                raise typer.BadParameter("--yes required for create")
            payload_data = _build_remote_link_payload(
                url=url,
                title=title,
                summary=summary,
                relationship=relationship,
                global_id=global_id,
                application_type=application_type,
                application_name=application_name,
                icon_url=icon_url,
                icon_title=icon_title,
                data_file=data_file,
            )
            result = adapter.create_or_update_issue_remote_link(issue_key, payload_data)
            _emit_json(result)

        elif action == "update":
            if not yes:
                raise typer.BadParameter("--yes required for update")
            remote_id = _parse_remote_link_identifier(remote_link_id)
            if remote_id is None:
                raise typer.BadParameter("--remote-link-id required for update")
            payload_data = _build_remote_link_payload(
                url=url,
                title=title,
                summary=summary,
                relationship=relationship,
                global_id=global_id,
                application_type=application_type,
                application_name=application_name,
                icon_url=icon_url,
                icon_title=icon_title,
                data_file=data_file,
            )
            result = adapter.update_issue_remote_link_by_id(issue_key, remote_id, payload_data)
            _emit_json(result)

        elif action == "delete":
            if not yes:
                raise typer.BadParameter("--yes required for delete")
            remote_id = _parse_remote_link_identifier(remote_link_id)
            if remote_id is None:
                raise typer.BadParameter("--remote-link-id required for delete")
            adapter.delete_issue_remote_link_by_id(issue_key, remote_id)
            _emit_json({"status": "deleted", "issue": issue_key, "remote_link_id": remote_id})

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("remote_link_command_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="remote-link",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue-property")
def cmd_issue_property(
    action: str = typer.Argument(..., help="Action: list, get, set, delete"),
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    property_key: str | None = typer.Option(
        None, "--property-key", "-p", help="Property key (required for get/set/delete)"
    ),
    data_file: Path | None = typer.Option(None, "--data-file", help="JSON file containing property value (for set)"),
    value: str | None = typer.Option(None, "--value", help="JSON string value (for set when no file provided)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (set/delete)"),
) -> None:
    """Manage Jira issue properties."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [
        action,
        f"issue={issue_key}",
        f"property_key={property_key}",
        f"data_file={data_file}",
    ]

    def _load_value() -> dict[str, Any]:
        if data_file:
            if not data_file.exists():
                raise typer.BadParameter(f"Data file not found: {data_file}")
            try:
                return json.loads(data_file.read_text())
            except json.JSONDecodeError as exc:
                raise typer.BadParameter(f"Invalid JSON in {data_file}: {exc}") from exc
        if value is None:
            raise typer.BadParameter("Provide --value or --data-file for set action")
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"Invalid JSON for --value: {exc}") from exc
        if not isinstance(parsed, dict):
            raise typer.BadParameter("--value must decode to a JSON object")
        return parsed

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_issue_property_keys(issue_key)
            _emit_json(payload)

        elif action == "get":
            if not property_key:
                raise typer.BadParameter("--property-key required for get")
            payload = adapter.get_issue_property(issue_key, property_key)
            _emit_json(payload)

        elif action == "set":
            if not yes:
                raise typer.BadParameter("--yes required for set")
            if not property_key:
                raise typer.BadParameter("--property-key required for set")
            payload = _load_value()
            adapter.set_issue_property(issue_key, property_key, payload)
            _emit_json({"status": "updated", "issue": issue_key, "property_key": property_key})

        elif action == "delete":
            if not yes:
                raise typer.BadParameter("--yes required for delete")
            if not property_key:
                raise typer.BadParameter("--property-key required for delete")
            adapter.delete_issue_property(issue_key, property_key)
            _emit_json({"status": "deleted", "issue": issue_key, "property_key": property_key})

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("issue_property_command_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="issue-property",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("watcher")
def cmd_watcher(
    action: str = typer.Argument(..., help="Action: list, add, remove"),
    issue_key: str = typer.Option(..., "--issue-key", "-k", help="Issue key (e.g., NTTC-123)"),
    account: str | None = typer.Option(
        None,
        "--account",
        "-a",
        help="Username or accountId (required for add/remove)",
    ),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operations (add/remove)"),
) -> None:
    """Manage issue watchers."""
    started_at = datetime.now(UTC)
    code = 0
    summary_args = [action, f"issue={issue_key}", f"account={account}"]

    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.issue_get_watchers(issue_key)
            _emit_json(payload)

        elif action == "add":
            if not yes:
                raise typer.BadParameter("--yes required for add")
            if not account:
                raise typer.BadParameter("--account required for add")
            adapter.issue_add_watcher(issue_key, account)
            _emit_json({"status": "added", "issue": issue_key, "account": account})

        elif action == "remove":
            if not yes:
                raise typer.BadParameter("--yes required for remove")
            if not account:
                raise typer.BadParameter("--account required for remove")
            adapter.issue_delete_watcher(issue_key, account)
            _emit_json({"status": "removed", "issue": issue_key, "account": account})

        else:
            raise typer.BadParameter(f"Unknown action: {action}")

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("watcher_command_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="watcher",
            args=summary_args,
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("security-scheme")
def cmd_security_scheme(
    action: str = typer.Argument(..., help="Action: list, get"),
    scheme_id: str | None = typer.Option(None, "--scheme-id", help="Scheme ID (for get)"),
    only_levels: bool = typer.Option(False, "--only-levels", help="Return only security levels (for get)"),
) -> None:
    """Issue security scheme operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "list":
            payload = adapter.get_issue_security_schemes()
            _emit_json({"count": len(payload), "security_schemes": payload})
        elif action == "get":
            if not scheme_id:
                raise typer.BadParameter("--scheme-id required for get")
            payload = adapter.get_issue_security_scheme(scheme_id, only_levels=only_levels)
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("security_scheme_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="security-scheme",
            args=[action, f"scheme_id={scheme_id}", f"only_levels={only_levels}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("permissions")
def cmd_permissions(
    action: str = typer.Argument(..., help="Action: all, check"),
    permissions: str | None = typer.Option(None, "--permissions", help="Comma-separated permission names (for check)"),
    project_key: str | None = typer.Option(None, "--project-key", help="Project key (for check)"),
    issue_key: str | None = typer.Option(None, "--issue-key", help="Issue key (for check)"),
) -> None:
    """Permission operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "all":
            payload = adapter.get_all_permissions()
            _emit_json({"count": len(payload), "permissions": payload})
        elif action == "check":
            if not permissions:
                raise typer.BadParameter("--permissions required for check")
            perms_list = [p.strip() for p in permissions.split(",")]
            payload = adapter.get_permissions(
                permissions=perms_list,
                project_key=project_key,
                issue_key=issue_key,
            )
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("permissions_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="permissions",
            args=[action, f"permissions={permissions}", f"project_key={project_key}", f"issue_key={issue_key}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("permission-scheme")
def cmd_permission_scheme(
    project_key: str = typer.Argument(..., help="Project key"),
    expand: str | None = typer.Option(None, "--expand", help="Expand options (comma-separated)"),
) -> None:
    """Get project permission scheme."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.get_project_permission_scheme(project_key, expand=expand)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("permission_scheme_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="permission-scheme",
            args=[project_key, f"expand={expand}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("issue-security-scheme")
def cmd_issue_security_scheme(
    project_key: str = typer.Argument(..., help="Project key"),
    only_levels: bool = typer.Option(False, "--only-levels", help="Return only security levels"),
) -> None:
    """Get project issue security scheme."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)
        payload = adapter.get_project_issue_security_scheme(project_key, only_levels=only_levels)
        _emit_json(payload)
    except (AuthError, VDSClientError) as exc:
        code = 1
        logger.exception("issue_security_scheme_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="issue-security-scheme",
            args=[project_key, f"only_levels={only_levels}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("reindex")
def cmd_reindex(
    action: str = typer.Argument(..., help="Action: start, status, with-type"),
    reindex_type: str | None = typer.Option(None, "--type", help="Reindex type (for with-type)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation"),
) -> None:
    """Reindex operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "start":
            if not yes:
                raise typer.BadParameter("Refusing to start reindex without --yes")
            payload = adapter.reindex()
            _emit_json(payload)
        elif action == "status":
            payload = adapter.reindex_status()
            _emit_json(payload)
        elif action == "with-type":
            if not yes:
                raise typer.BadParameter("Refusing to reindex without --yes")
            if not reindex_type:
                raise typer.BadParameter("--type required for with-type")
            payload = adapter.reindex_with_type(reindex_type)
            _emit_json(payload)
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("reindex_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="reindex",
            args=[action, f"type={reindex_type}"],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


@app.command("user")
def cmd_user(
    action: str = typer.Argument(..., help="Action: search, groups, deactivate"),
    query: str | None = typer.Option(None, "--query", help="Search query (for search)"),
    account_id: str | None = typer.Option(None, "--account-id", help="Account ID (for groups)"),
    username: str | None = typer.Option(None, "--username", help="Username (for deactivate)"),
    start: int = typer.Option(0, "--start", help="Start index for pagination (for search)"),
    limit: int = typer.Option(50, "--limit", help="Limit for pagination (for search)"),
    include_inactive: bool = typer.Option(False, "--include-inactive", help="Include inactive users (for search)"),
    yes: bool = typer.Option(False, "--yes", help="Confirm write operation (for deactivate)"),
) -> None:
    """User management operations."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        if action == "search":
            if not query:
                raise typer.BadParameter("--query required for search")
            payload = adapter.find_users(query=query, start=start, limit=limit, include_inactive=include_inactive)
            _emit_json({"count": len(payload), "users": payload})
        elif action == "groups":
            if not account_id:
                raise typer.BadParameter("--account-id required for groups")
            payload = adapter.get_user_groups(account_id)
            _emit_json({"count": len(payload), "groups": payload})
        elif action == "deactivate":
            if not yes:
                raise typer.BadParameter("Refusing to deactivate user without --yes")
            if not username:
                raise typer.BadParameter("--username required for deactivate")
            adapter.deactivate_user(username)
            _emit_json({"status": "deactivated", "username": username})
        else:
            raise typer.BadParameter(f"Unknown action: {action}")
    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("user_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="user",
            args=[
                action,
                f"query={query}",
                f"account_id={account_id}",
                f"username={username}",
                f"start={start}",
                f"limit={limit}",
                f"include_inactive={include_inactive}",
                f"yes={yes}",
            ],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None


if __name__ == "__main__":
    app()


@app.command("discover-fields")
def cmd_discover_fields(
    project: str = typer.Option(..., "--project", help="Project key"),
    issuetype: str = typer.Option(..., "--issuetype", help="Issue type name (e.g., Task, Bug)"),
    field: str | None = typer.Option(
        None, "--field", help="Optional: Filter by field name or ID (case-insensitive substring)"
    ),
    include_system: bool = typer.Option(False, "--include-system", help="Include system (non-custom) fields"),
    issue_key: str | None = typer.Option(
        None, "--issue-key", help="Issue key for editmeta fallback when createmeta is unavailable"
    ),
) -> None:
    """Discover custom fields (default), requirements, and allowed values for a project/issuetype."""
    started_at = datetime.now(UTC)
    code = 0
    try:
        s = JiraSettings()
        s.require_basic_or_token()
        adapter = JiraAdapter(url=str(s.base_url), username=s.username, password=s.password, token=s.token)

        raw_fields: dict[str, Any] | None = None
        editmeta_fields: dict[str, Any] | None = None
        createmeta_error: Exception | None = None

        try:
            meta = adapter.get_createmeta(project_key=project, issuetype=issuetype)
            raw_fields = _extract_createmeta_fields(meta, project, issuetype)
        except (VDSClientError, typer.BadParameter) as exc:
            createmeta_error = exc

        if issue_key:
            try:
                editmeta = adapter.get_editmeta(issue_key)
                editmeta_fields = editmeta.get("fields", {})
            except VDSClientError as exc:
                if createmeta_error:
                    raise typer.BadParameter(
                        f"Failed to load create metadata for {project}/{issuetype}: {createmeta_error}. "
                        f"Editmeta fallback for {issue_key} also failed: {exc}"
                    ) from exc
                editmeta_fields = None
                typer.echo(f"Warning: editmeta fallback unavailable: {exc}", err=True)

        if raw_fields is None or not raw_fields:
            if editmeta_fields:
                raw_fields = editmeta_fields
            elif createmeta_error:
                raise typer.BadParameter(
                    f"Failed to load create metadata for {project}/{issuetype}: {createmeta_error}"
                ) from createmeta_error
        elif editmeta_fields:
            _merge_allowed_values_from_editmeta(raw_fields, editmeta_fields)

        if raw_fields is None:
            if createmeta_error:
                raise createmeta_error
            raw_fields = {}

        fields = _collect_fields(raw_fields, field_filter=field, include_system=include_system)

        duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
        output = {
            "project": project,
            "issueType": issuetype,
            "count": len(fields),
            "duration_ms": duration_ms,
            "fields": sorted(fields, key=lambda x: (not x["required"], x["name"])),
        }

        if (len(fields) <= 50 and duration_ms > 2000) or (len(fields) <= 200 and duration_ms > 5000):
            logger.warning("discover_fields_slow duration_ms=%s count=%s", duration_ms, len(fields))

        _emit_json(output)

    except (AuthError, VDSClientError, typer.BadParameter) as exc:
        code = 1
        logger.exception("discover_fields_failed %s", exc)
        typer.echo(f"Error: {exc}", err=True)
    finally:
        finished_at = datetime.now(UTC)
        _record_summary(
            command="discover-fields",
            args=[
                f"project={project}",
                f"issuetype={issuetype}",
                f"field={field}",
                f"include_system={include_system}",
                f"issue_key={issue_key}",
            ],
            exit_code=code,
            started_at=started_at,
            finished_at=finished_at,
        )
        if code != 0:
            raise typer.Exit(code=code) from None
