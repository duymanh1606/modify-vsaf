"""CLI for VDS SonarQube Orchestrator.

Provides command-line access to SonarQube code quality scanning and issue management.

Usage:
    # Via direct script
    uv run vds-sonarqube ping
    uv run vds-sonarqube projects list
    uv run vds-sonarqube issues list --project ekyc-business

    # Via vds-cli router
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- ping
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- projects list
    ./scripts/worktree_uv.sh run --project vds_cli vds-cli sonarqube -- issues list --project ekyc-business

    # JSON-only mode (clean JSON output, no headers/decoration)
    uv run vds-sonarqube --json ping
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.external_sca import ExternalSCAClient
from vds_cli_common.app import make_vds_app
from vds_cli_common.context import CLIContext
from vds_cli_common.output import OutputManager
from vds_cli_common.paths import get_shared_env_path
from vds_platform_core.logging import configure_structlog

from vds_sonarqube_orchestrator.client import SonarqubeClient
from vds_sonarqube_orchestrator.config import SettingsError, load_settings
from vds_sonarqube_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    NotFoundError,
    VDSClientError,
)

configure_structlog()
app = make_vds_app(
    name="vds-sonarqube",
    help="VDS SonarQube CLI - Code quality scanning and issue management",
    settings_factory=load_settings,
)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _get_client() -> SonarqubeClient:
    """Load settings and create client."""
    settings = load_settings(strict=True)
    return SonarqubeClient(settings)


def _handle_error(exc: VDSClientError, out: OutputManager) -> None:
    """Handle SonarQube client errors with appropriate hints."""
    if isinstance(exc, AuthError):
        out.output_error(
            str(exc),
            hint="Check VDS_SONAR_TOKEN or VDS_SONAR_USER/VDS_SONAR_PASSWORD",
        )
    elif isinstance(exc, ClientPermissionError):
        out.output_error(
            str(exc),
            hint="Ensure your SonarQube user has access to the requested resource",
        )
    elif isinstance(exc, NotFoundError):
        out.output_error(
            str(exc),
            hint="Check the project key or resource identifier",
        )
    else:
        out.output_error(
            str(exc),
            hint="Ensure Maven or sonar-scanner is installed and in PATH",
        )


def _get_sca_client() -> ExternalSCAClient:
    """Load settings and create SCA client."""
    from vds_sonarqube_orchestrator.external_sca import ExternalSCAClient

    settings = load_settings()
    return ExternalSCAClient(settings)


# -----------------------------------------------------------------------------
# Health Commands
# -----------------------------------------------------------------------------


@app.command()
def ping(
    ctx: typer.Context,
) -> None:
    """Test connectivity to SonarQube server.

    Verifies that:
    1. SonarQube server is reachable
    2. Authentication works
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.ping()
            status = str(result.get("status", "UNKNOWN"))
            is_up = status.upper() == "UP"
            out.output_json(result)
            raise typer.Exit(0 if is_up else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Project Commands
# -----------------------------------------------------------------------------


@app.command("projects")
def projects_cmd(
    ctx: typer.Context,
    query: Annotated[
        str | None,
        typer.Option("--query", "-q", help="Filter projects by name"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum results"),
    ] = 100,
) -> None:
    """List all accessible SonarQube projects."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.search_projects(query=query, per_page=limit)
            out.output_json(result)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


@app.command("project")
def project_get(
    ctx: typer.Context,
    key: Annotated[
        str,
        typer.Option("--key", "-k", help="Project key"),
    ],
) -> None:
    """Get details for a specific project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.get_project(key)
            out.output_json(result)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Issue Commands
# -----------------------------------------------------------------------------


@app.command("issues")
def issues_cmd(
    ctx: typer.Context,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Project key"),
    ] = None,
    severities: Annotated[
        str | None,
        typer.Option(
            "--severities",
            "-s",
            help="Comma-separated severities (BLOCKER,CRITICAL,MAJOR,MINOR,INFO)",
        ),
    ] = None,
    types: Annotated[
        str | None,
        typer.Option(
            "--types",
            "-t",
            help="Comma-separated types (BUG,VULNERABILITY,CODE_SMELL)",
        ),
    ] = None,
    statuses: Annotated[
        str | None,
        typer.Option(
            "--statuses",
            help="Comma-separated statuses (OPEN,CONFIRMED,REOPENED,RESOLVED,CLOSED)",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum results"),
    ] = 100,
) -> None:
    """List issues for a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            sev_list = severities.split(",") if severities else None
            type_list = types.split(",") if types else None
            status_list = statuses.split(",") if statuses else None

            result = client.get_issues(
                project_key=project,
                severities=sev_list,
                types=type_list,
                statuses=status_list,
                per_page=limit,
            )
            out.output_json(result)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Metrics/Measures Commands
# -----------------------------------------------------------------------------


@app.command("measures")
def measures_cmd(
    ctx: typer.Context,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Project key"),
    ] = None,
    metrics: Annotated[
        str,
        typer.Option(
            "--metrics",
            "-m",
            help='Comma-separated metric keys (default: "bugs,vulnerabilities,coverage")',
        ),
    ] = "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density",
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
) -> None:
    """Get quality metrics for a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            metric_list = metrics.split(",")
            result = client.get_measures(project, metric_list, branch)
            out.output_json(result)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Quality Gate Commands
# -----------------------------------------------------------------------------


@app.command("qualitygate")
def qualitygate_cmd(
    ctx: typer.Context,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Project key"),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
) -> None:
    """Check quality gate status for a project."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        with _get_client() as client:
            result = client.get_quality_gate_status(project, branch)
            project_status = result.get("projectStatus", {})
            status = project_status.get("status", "UNKNOWN")
            out.output_json(result)
            raise typer.Exit(0 if status == "OK" else 1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Scan Commands
# -----------------------------------------------------------------------------


@app.command("scan")
def scan_cmd(
    ctx: typer.Context,
    scan_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Scan type: maven or scanner"),
    ] = "maven",
    project_dir: Annotated[
        str | None,
        typer.Option("--project-dir", "-d", help="Path to project directory"),
    ] = None,
    project_key: Annotated[
        str | None,
        typer.Option("--project-key", "-k", help="SonarQube project key"),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for scan completion"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", help="Scan timeout in seconds (default: 600)"),
    ] = 600,
) -> None:
    """Run a local code quality scan.

    Examples:
        # Maven scan
        vds-sonarqube scan --type maven --project-dir /path/to/project --project-key my-project

        # Sonar-scanner
        vds-sonarqube scan --type scanner --project-dir /path/to/project --project-key my-project

        # With branch
        vds-sonarqube scan --type maven --project-dir . --project-key my-project --branch main --wait
    """
    from vds_sonarqube_orchestrator.scanner import SonarqubeScanner

    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        settings = load_settings(strict=True)
        scanner = SonarqubeScanner(settings)

        project_path = Path(project_dir)
        if not project_path.exists():
            out.output_error(f"Project directory does not exist: {project_dir}")
            raise typer.Exit(1)

        if scan_type == "maven":
            out.output_info(f"Running Maven scan for {project_key}...")
            task_id = scanner.scan_maven(
                project_path,
                project_key,
                branch=branch,
                wait=wait,
                timeout=timeout,
            )
        elif scan_type == "scanner":
            out.output_info(f"Running sonar-scanner for {project_key}...")
            task_id = scanner.scan_scanner(
                project_path,
                project_key,
                branch=branch,
                wait=wait,
                timeout=timeout,
            )
        else:
            out.output_error(f"Unknown scan type: {scan_type}. Use 'maven' or 'scanner'")
            raise typer.Exit(1)

        out.output_success("Scan initiated successfully")
        if task_id:
            out.print(f"Task ID: {task_id}")

    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Task Commands
# -----------------------------------------------------------------------------


@app.command("task")
def task_cmd(
    ctx: typer.Context,
    status: Annotated[
        bool,
        typer.Option("--status", help="Show task status subcommand"),
    ] = False,
    id: Annotated[
        str | None,
        typer.Option("--id", help="Task ID (for status subcommand)"),
    ] = None,
) -> None:
    """Get task status or show task help."""
    out = OutputManager(CLIContext.from_typer_context(ctx))
    if not status:
        out.output_info("Use 'vds-sonarqube task --status --id <TASK_ID>' to check task status")
        raise typer.Exit(0)

    if not id:
        out.output_error("--id is required when using --status")
        raise typer.Exit(1)

    try:
        with _get_client() as client:
            result = client.get_task_info(id)
            out.output_json(result)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)
    except VDSClientError as exc:
        _handle_error(exc, out)
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Migration Command
# -----------------------------------------------------------------------------


@app.command("migrate-env")
def migrate_env_cmd(
    ctx: typer.Context,
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Source directory containing .env file"),
    ] = ".",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview changes without applying"),
    ] = False,
) -> None:
    """Migrate SonarQube credentials from project .env to the shared VDS env file.

    Copies SONAR_* variables from project .env to VDS_SONAR_* in the shared VDS env file.

    Examples:
        # Preview migration
        vds-sonarqube migrate-env --source EKYC-project/ekyc-business --dry-run

        # Apply migration
        vds-sonarqube migrate-env --source EKYC-project/ekyc-business
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))

    source_dir = Path(source).resolve()
    source_env = source_dir / ".env"

    if not source_env.exists():
        out.output_error(f".env file not found in: {source_dir}")
        raise typer.Exit(1)

    # Read source .env
    source_vars: dict[str, str] = {}
    with open(source_env) as f:
        for line in f:
            line = line.strip()
            if line.startswith("SONAR_") and "=" in line:
                key, value = line.split("=", 1)
                source_vars[key] = value

    if not source_vars:
        out.output_error("No SONAR_* variables found in source .env")
        raise typer.Exit(0)

    # Build target variables
    target_mappings = {
        "SONAR_TOKEN": "VDS_SONAR_TOKEN",
        "SONAR_HOST_URL": "VDS_SONAR_HOST_URL",
        "SONAR_PROJECT_KEY": "VDS_SONAR_PROJECT_KEY",
        "SONAR_BRANCH_NAME": "VDS_SONAR_BRANCH_NAME",
        "SONAR_USER": "VDS_SONAR_USER",
        "SONAR_PASSWORD": "VDS_SONAR_PASSWORD",
    }

    target_vars: dict[str, str] = {}
    for src_key, tgt_key in target_mappings.items():
        if src_key in source_vars:
            target_vars[tgt_key] = source_vars[src_key]

    # Show preview
    out.print("[bold]Migration Preview:[/bold]")
    for key, value in target_vars.items():
        display_value = f"{value[:20]}..." if len(value) > 20 else value
        if "PASSWORD" in key or "TOKEN" in key:
            display_value = "***"
        out.print(f"  {key} = {display_value}")

    target_env_path = get_shared_env_path()

    if dry_run:
        out.print("\n[yellow]Dry run mode - no changes made[/yellow]")
        out.print(f"Target file: {target_env_path}")
        raise typer.Exit(0)

    # Create backup
    if target_env_path.exists():
        backup_path = target_env_path.with_suffix(f".env.backup.{int(time.time())}")
        shutil.copy2(target_env_path, backup_path)
        out.print(f"[dim]Backup created: {backup_path}[/dim]")

    # Ensure target directory exists
    target_env_path.parent.mkdir(parents=True, exist_ok=True)

    # Append new variables to target .env
    with open(target_env_path, "a") as f:
        f.write("\n# SonarQube Orchestrator (migrated from project .env)\n")
        for key, value in target_vars.items():
            f.write(f"{key}={value}\n")

    out.output_success("Migration complete")
    out.print(f"Updated: {target_env_path}")


# -----------------------------------------------------------------------------
# SCA (External Tool) Commands
# -----------------------------------------------------------------------------


@app.command("sca-status")
def sca_status_cmd(
    ctx: typer.Context,
    install_guide: Annotated[
        bool,
        typer.Option("--install-guide", help="Show installation guide for SCA tools"),
    ] = False,
) -> None:
    """Show available SCA tools and their installation status.

    Examples:
        vds-sonarqube sca-status
        vds-sonarqube sca-status --install-guide
    """
    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        client = _get_sca_client()
        tools = client.detect_available_tools()

        if install_guide:
            out.output_json({"install_guide": client.get_installation_guide()})
            raise typer.Exit(0)

        out.output_json({name: info.to_dict() for name, info in tools.items()})
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)


@app.command("dependencies")
def dependencies_cmd(
    ctx: typer.Context,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Directory to scan (default: current directory)"),
    ] = ".",
    tool: Annotated[
        str,
        typer.Option("--tool", "-t", help="Tool to use (auto, snyk, trivy, grype)"),
    ] = "auto",
    severities: Annotated[
        str | None,
        typer.Option("--severities", "-s", help="Filter by severities (CRITICAL,HIGH,MEDIUM,LOW)"),
    ] = None,
) -> None:
    """Scan dependencies for vulnerabilities using external SCA tools.

    Examples:
        vds-sonarqube dependencies --project-dir /path/to/project
        vds-sonarqube dependencies --tool trivy --severities CRITICAL,HIGH
    """
    from vds_sonarqube_orchestrator.external_sca import (
        SCAError,
        ToolNotAvailableError,
    )

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        client = _get_sca_client()
        project_path = Path(project_dir).resolve()

        if not project_path.exists():
            out.output_error(f"Directory does not exist: {project_path}")
            raise typer.Exit(1)

        sev_list = severities.split(",") if severities else None
        tool_name = None if tool == "auto" else tool

        if not cli_ctx.quiet:
            out.output_info(f"Scanning {project_path} for vulnerabilities...")

        report = client.scan_dependencies(project_path, tool=tool_name, severities=sev_list)
        out.output_json(report.to_dict())

    except ToolNotAvailableError as exc:
        out.output_error(
            str(exc),
            hint="Run 'vds-sonarqube sca-status --install-guide' for installation help",
        )
        raise typer.Exit(1)
    except SCAError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)


@app.command("sbom")
def sbom_cmd(
    ctx: typer.Context,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Directory to scan (default: current directory)"),
    ] = ".",
    sbom_format: Annotated[
        str,
        typer.Option("--format", "-f", help="SBOM format (cyclonedx, spdx)"),
    ] = "cyclonedx",
    tool: Annotated[
        str,
        typer.Option("--tool", "-t", help="Tool to use (auto, syft, trivy)"),
    ] = "auto",
    output: Annotated[
        str | None,
        typer.Option("--output", "-o", help="Output file path (default: stdout)"),
    ] = None,
) -> None:
    """Generate Software Bill of Materials (SBOM) for a project.

    Examples:
        vds-sonarqube sbom --project-dir /path/to/project
        vds-sonarqube sbom --format spdx --output sbom.json
    """
    from vds_sonarqube_orchestrator.external_sca import (
        SCAError,
        ToolNotAvailableError,
    )

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        client = _get_sca_client()
        project_path = Path(project_dir).resolve()

        if not project_path.exists():
            out.output_error(f"Directory does not exist: {project_path}")
            raise typer.Exit(1)

        tool_name = None if tool == "auto" else tool

        if not cli_ctx.quiet:
            out.output_info(f"Generating {sbom_format.upper()} SBOM for {project_path}...")

        sbom = client.generate_sbom(project_path, sbom_format=sbom_format, tool=tool_name)

        if output:
            output_path = Path(output)
            with open(output_path, "w") as f:
                json.dump(sbom.raw_output, f, indent=2)
            if not cli_ctx.quiet:
                out.output_success(f"SBOM saved to {output_path}")
        elif cli_ctx.json_only:
            out.output_json(sbom.raw_output)
        else:
            out.output_json(sbom.to_dict())

    except ToolNotAvailableError as exc:
        out.output_error(
            str(exc),
            hint="Run 'vds-sonarqube sca-status --install-guide' for installation help",
        )
        raise typer.Exit(1)
    except SCAError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)


@app.command("dependencies-check")
def dependencies_check_cmd(
    ctx: typer.Context,
    project_dir: Annotated[
        str,
        typer.Option("--project-dir", "-d", help="Directory to scan (default: current directory)"),
    ] = ".",
    fail_on: Annotated[
        str,
        typer.Option("--fail-on", help="Minimum severity to fail (CRITICAL, HIGH, MEDIUM, LOW)"),
    ] = "HIGH",
    max_vulns: Annotated[
        int,
        typer.Option("--max-vulns", help="Maximum allowed vulnerabilities (0 = fail on any)"),
    ] = 0,
    tool: Annotated[
        str,
        typer.Option("--tool", "-t", help="Tool to use (auto, snyk, trivy, grype)"),
    ] = "auto",
) -> None:
    """Check dependency quality gate (fail on vulnerabilities).

    Exit code 0 = passed, 1 = failed or error.

    Examples:
        vds-sonarqube dependencies-check --project-dir /path/to/project
        vds-sonarqube dependencies-check --fail-on CRITICAL --max-vulns 5
    """
    from vds_sonarqube_orchestrator.external_sca import (
        SCAError,
        ToolNotAvailableError,
    )

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        client = _get_sca_client()
        project_path = Path(project_dir).resolve()

        if not project_path.exists():
            out.output_error(f"Directory does not exist: {project_path}")
            raise typer.Exit(1)

        tool_name = None if tool == "auto" else tool

        if not cli_ctx.quiet:
            out.output_info(f"Checking dependency quality gate for {project_path}...")

        result = client.check_quality_gate(
            project_path,
            fail_threshold=fail_on.upper(),
            max_vulnerabilities=max_vulns,
            tool=tool_name,
        )
        out.output_json(result.to_dict())
        raise typer.Exit(0 if result.passed else 1)

    except ToolNotAvailableError as exc:
        out.output_error(
            str(exc),
            hint="Run 'vds-sonarqube sca-status --install-guide' for installation help",
        )
        raise typer.Exit(1)
    except SCAError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(
            f"Configuration error: {exc}",
            hint=f"Check VDS_SONAR_* variables in {get_shared_env_path()}",
        )
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# PR Integration Commands (Phase 2)
# -----------------------------------------------------------------------------


@app.command("pr-comment")
def pr_comment_cmd(
    ctx: typer.Context,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="Bitbucket project key"),
    ],
    repo: Annotated[
        str,
        typer.Option("--repo", "-r", help="Repository slug"),
    ],
    pr_id: Annotated[
        int,
        typer.Option("--pr", help="Pull request ID"),
    ],
    sonar_project: Annotated[
        str | None,
        typer.Option(
            "--sonar-project",
            "-s",
            help="SonarQube project key (defaults to VDS_SONAR_PROJECT_KEY)",
        ),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name for analysis"),
    ] = None,
) -> None:
    """Decorate a PR with SonarQube analysis results using Bitbucket Code Insights.

    Examples:
        vds-sonarqube pr-comment --project EKYC --repo ekyc-business --pr 154
        vds-sonarqube pr-comment -p EKYC -r ekyc-business --pr 154 --sonar-project ekyc-business
    """
    from vds_sonarqube_orchestrator.pr import PRDecoratorError, SonarqubePRDecorator

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        sonar_settings = load_settings(strict=True)

        from vds_bitbucket_orchestrator.config import load_settings as load_bb_settings

        bb_settings = load_bb_settings(strict=True)
        decorator = SonarqubePRDecorator(sonar_settings, bb_settings)

        if not cli_ctx.quiet:
            out.output_info(f"Decorating PR #{pr_id} with SonarQube results...")

        result = decorator.decorate_pr(
            project_key=project,
            repo_slug=repo,
            pr_id=pr_id,
            sonar_project_key=sonar_project,
            branch=branch,
        )
        out.output_json(result.to_dict())
        raise typer.Exit(0 if result.success else 1)

    except PRDecoratorError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except ImportError:
        out.output_error(
            "vds-bitbucket-orchestrator is required for PR integration",
            hint="Install with: uv add vds-bitbucket-orchestrator",
        )
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


@app.command("pr-status")
def pr_status_cmd(
    ctx: typer.Context,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="SonarQube project key"),
    ],
    _branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name (reserved for future use)"),
    ] = None,
    wait: Annotated[
        bool,
        typer.Option("--wait", "-w", help="Wait for analysis to complete"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", "-t", help="Timeout in seconds when waiting"),
    ] = 300,
) -> None:
    """Check PR analysis status for a project/branch.

    Examples:
        vds-sonarqube pr-status --project ekyc-business
        vds-sonarqube pr-status --project ekyc-business --branch feature/new --wait
    """
    from vds_sonarqube_orchestrator.pr import (
        PRAnalysisStatus,
        PRAnalysisTimeoutError,
    )

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        sonar_settings = load_settings(strict=True)

        class StatusChecker:
            def __init__(self, settings):
                self._settings = settings
                self._client = None

            def _get_client(self):
                if self._client is None:
                    self._client = SonarqubeClient(self._settings)
                return self._client

        checker = StatusChecker(sonar_settings)

        if wait:
            if not cli_ctx.quiet:
                out.output_info(f"Waiting for analysis to complete (timeout: {timeout}s)...")

            start_time = time.time()
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise PRAnalysisTimeoutError(f"Analysis did not complete within {timeout}s")

                with checker._get_client() as client:
                    tasks = client.get_ce_activity(project, limit=1)

                if tasks:
                    task = tasks[0]
                    status_val = task.get("status", "UNKNOWN")
                    if status_val in ("SUCCESS", "FAILED", "CANCELED"):
                        result = PRAnalysisStatus(
                            task_id=task.get("id", ""),
                            status=status_val,
                            component_key=task.get("componentKey"),
                            analysis_id=task.get("analysisId"),
                            error_message=task.get("errorMessage"),
                        )
                        break

                time.sleep(5)
        else:
            with checker._get_client() as client:
                tasks = client.get_ce_activity(project, limit=1)

            if not tasks:
                out.output_json({"status": "NO_ANALYSIS", "message": "No analysis found"})
                raise typer.Exit(0)

            task = tasks[0]
            result = PRAnalysisStatus(
                task_id=task.get("id", ""),
                status=task.get("status", "UNKNOWN"),
                component_key=task.get("componentKey"),
                analysis_id=task.get("analysisId"),
                error_message=task.get("errorMessage"),
            )

        out.output_json(result.to_dict())
        raise typer.Exit(0 if result.is_success else 1)

    except PRAnalysisTimeoutError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Batch Operations Commands (Phase 3)
# -----------------------------------------------------------------------------


@app.command("batch-qualitygate")
def batch_qualitygate_cmd(
    ctx: typer.Context,
    projects: Annotated[
        str,
        typer.Option("--projects", "-p", help="Comma-separated project keys"),
    ],
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
    fail_on_any: Annotated[
        bool,
        typer.Option("--fail-on-any", help="Exit 1 if any quality gate fails"),
    ] = False,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help="Number of parallel requests"),
    ] = 3,
) -> None:
    """Check quality gates for multiple projects in parallel.

    Examples:
        vds-sonarqube batch-qualitygate --projects "proj1,proj2,proj3"
        vds-sonarqube batch-qualitygate -p "proj1,proj2" --fail-on-any
    """
    from vds_sonarqube_orchestrator.batch import BatchExecutor

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        settings = load_settings(strict=True)
        executor = BatchExecutor(settings, concurrency=concurrency)
        project_list = [p.strip() for p in projects.split(",") if p.strip()]

        if not cli_ctx.quiet:
            out.output_info(f"Checking quality gates for {len(project_list)} projects...")

        result = executor.batch_quality_gates(project_list, branch)
        out.output_json(result.to_dict())

        any_failed = any(not pr.data.get("passed", False) for pr in result.results if pr.success)
        raise typer.Exit(1 if fail_on_any and any_failed else 0)

    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


@app.command("batch-issues")
def batch_issues_cmd(
    ctx: typer.Context,
    projects: Annotated[
        str,
        typer.Option("--projects", "-p", help="Comma-separated project keys"),
    ],
    severities: Annotated[
        str | None,
        typer.Option(
            "--severities", "-s", help="Filter by severities (BLOCKER,CRITICAL,MAJOR,MINOR,INFO)"
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Max issues per project"),
    ] = 100,
    concurrency: Annotated[
        int,
        typer.Option("--concurrency", "-c", help="Number of parallel requests"),
    ] = 3,
) -> None:
    """Fetch issues for multiple projects in parallel.

    Examples:
        vds-sonarqube batch-issues --projects "proj1,proj2,proj3"
        vds-sonarqube batch-issues -p "proj1,proj2" --severities CRITICAL,MAJOR
    """
    from vds_sonarqube_orchestrator.batch import BatchExecutor

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        settings = load_settings(strict=True)
        executor = BatchExecutor(settings, concurrency=concurrency)
        project_list = [p.strip() for p in projects.split(",") if p.strip()]
        sev_list = [s.strip() for s in severities.split(",")] if severities else None

        if not cli_ctx.quiet:
            out.output_info(f"Fetching issues for {len(project_list)} projects...")

        result = executor.batch_issues(project_list, severities=sev_list, limit_per_project=limit)
        out.output_json(result.to_dict())
        raise typer.Exit(0)

    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Report Generation Commands (Phase 4)
# -----------------------------------------------------------------------------


@app.command("report")
def report_cmd(
    ctx: typer.Context,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="SonarQube project key"),
    ],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Output file path"),
    ],
    report_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Report format (html, pdf)"),
    ] = "html",
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
    trends: Annotated[
        bool,
        typer.Option("--trends", help="Include trend analysis"),
    ] = False,
    trend_days: Annotated[
        int,
        typer.Option("--trend-days", help="Days of trend data to include"),
    ] = 30,
) -> None:
    """Generate quality report for a project.

    Examples:
        vds-sonarqube report --project ekyc-business --output report.html
        vds-sonarqube report -p ekyc-business -o report.pdf --format pdf --trends
    """
    from vds_sonarqube_orchestrator.reports import ReportError, SonarqubeReportGenerator

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        settings = load_settings(strict=True)
        generator = SonarqubeReportGenerator(settings)
        output_path = Path(output)

        if not cli_ctx.quiet:
            out.output_info(f"Generating {report_format.upper()} report for {project}...")

        if report_format.lower() == "pdf":
            result_path = generator.generate_pdf_report(
                project_key=project,
                output_path=output_path,
                branch=branch,
                include_trends=trends,
                trend_days=trend_days,
            )
        else:
            result_path = generator.generate_html_report(
                project_key=project,
                output_path=output_path,
                branch=branch,
                include_trends=trends,
                trend_days=trend_days,
            )

        out.output_json({"success": True, "output": str(result_path)})
        raise typer.Exit(0)

    except ReportError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)
    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Webhook Commands (Phase 5)
# -----------------------------------------------------------------------------

webhook_app = typer.Typer(name="webhook", help="Webhook management commands.")
app.add_typer(webhook_app)


@webhook_app.command("register")
def webhook_register_cmd(
    ctx: typer.Context,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="Webhook URL"),
    ],
    events: Annotated[
        str,
        typer.Option(
            "--events",
            "-e",
            help="Comma-separated events (scan_complete,quality_gate_change)",
        ),
    ] = "scan_complete",
    secret: Annotated[
        str | None,
        typer.Option("--secret", "-s", help="HMAC secret for signing"),
    ] = None,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Limit to specific project"),
    ] = None,
) -> None:
    """Register a new webhook.

    Examples:
        vds-sonarqube webhook register --url https://example.com/hook --events scan_complete
        vds-sonarqube webhook register -u https://example.com/hook -e scan_complete,quality_gate_change -s mysecret
    """
    from vds_sonarqube_orchestrator.webhooks import WebhookError, WebhookManager

    out = OutputManager(CLIContext.from_typer_context(ctx))
    try:
        manager = WebhookManager()
        event_list = [e.strip() for e in events.split(",")]
        webhook = manager.register_webhook(
            url=url, events=event_list, secret=secret, project_key=project
        )
        out.output_json(webhook.to_dict())
    except WebhookError as exc:
        out.output_error(str(exc))
        raise typer.Exit(1)


@webhook_app.command("list")
def webhook_list_cmd(
    ctx: typer.Context,
    project: Annotated[
        str | None,
        typer.Option("--project", "-p", help="Filter by project"),
    ] = None,
) -> None:
    """List registered webhooks.

    Examples:
        vds-sonarqube webhook list
        vds-sonarqube webhook list --project ekyc-business
    """
    from vds_sonarqube_orchestrator.webhooks import WebhookManager

    out = OutputManager(CLIContext.from_typer_context(ctx))
    manager = WebhookManager()
    webhooks = manager.list_webhooks(project_key=project)
    out.output_json([wh.to_dict() for wh in webhooks])


@webhook_app.command("delete")
def webhook_delete_cmd(
    ctx: typer.Context,
    webhook_id: Annotated[
        str,
        typer.Option("--id", help="Webhook ID to delete"),
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation"),
    ] = False,
) -> None:
    """Delete a webhook.

    Examples:
        vds-sonarqube webhook delete --id abc123 --yes
    """
    from vds_sonarqube_orchestrator.webhooks import WebhookManager

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    manager = WebhookManager()

    if not yes and not cli_ctx.json_only:
        confirm = typer.confirm(f"Delete webhook {webhook_id}?")
        if not confirm:
            raise typer.Exit(0)

    deleted = manager.delete_webhook(webhook_id)
    out.output_json({"deleted": deleted, "id": webhook_id})
    raise typer.Exit(0 if deleted else 1)


# -----------------------------------------------------------------------------
# Diff Analysis Commands (Phase 5)
# -----------------------------------------------------------------------------


@app.command("diff")
def diff_cmd(
    ctx: typer.Context,
    project: Annotated[
        str,
        typer.Option("--project", "-p", help="SonarQube project key"),
    ],
    before_branch: Annotated[
        str,
        typer.Option("--before", help="Before branch name (e.g., main, release)"),
    ],
    after_branch: Annotated[
        str,
        typer.Option("--after", help="After branch name (e.g., feature/new)"),
    ] = "main",
) -> None:
    """Compare issues between two branches.

    Examples:
        vds-sonarqube diff --project ekyc-business --before main --after feature/new
        vds-sonarqube diff -p ekyc-business --before release --after develop
    """
    from vds_sonarqube_orchestrator.diff import DiffAnalyzer

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        settings = load_settings(strict=True)
        analyzer = DiffAnalyzer(settings)

        if not cli_ctx.quiet:
            out.output_info(f"Analyzing diff for {project}...")

        result = analyzer.compare_branches(project, before_branch, after_branch)
        out.output_json(result.to_dict())
        raise typer.Exit(0)

    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Portfolio Commands (Phase 5)
# -----------------------------------------------------------------------------


@app.command("portfolio")
def portfolio_cmd(
    ctx: typer.Context,
    projects: Annotated[
        str,
        typer.Option("--projects", "-p", help="Comma-separated project keys"),
    ],
    by_severity: Annotated[
        bool,
        typer.Option("--by-severity", help="Show breakdown by severity"),
    ] = False,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name"),
    ] = None,
    top_issues: Annotated[
        int,
        typer.Option("--top-issues", help="Show top N common issues"),
    ] = 0,
) -> None:
    """Aggregate metrics across multiple projects.

    Examples:
        vds-sonarqube portfolio --projects "proj1,proj2,proj3"
        vds-sonarqube portfolio -p "proj1,proj2" --by-severity
    """
    from vds_sonarqube_orchestrator.portfolio import PortfolioManager

    cli_ctx = CLIContext.from_typer_context(ctx)
    out = OutputManager(cli_ctx)
    try:
        settings = load_settings(strict=True)
        manager = PortfolioManager(settings)
        project_list = [p.strip() for p in projects.split(",") if p.strip()]

        if not cli_ctx.quiet:
            out.output_info(f"Aggregating metrics for {len(project_list)} projects...")

        result = manager.get_portfolio_metrics(project_keys=project_list, branch=branch)

        if by_severity:
            result.by_severity = manager.get_issues_by_severity(project_list)

        top_issues_list = []
        if top_issues > 0:
            top_issues_list = manager.get_top_issues(project_list, limit=top_issues)

        output_data = result.to_dict()
        if top_issues_list:
            output_data["top_issues"] = [ti.to_dict() for ti in top_issues_list]
        out.output_json(output_data)
        raise typer.Exit(0)

    except SettingsError as exc:
        out.output_error(f"Configuration error: {exc}")
        raise typer.Exit(1)


# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app()
