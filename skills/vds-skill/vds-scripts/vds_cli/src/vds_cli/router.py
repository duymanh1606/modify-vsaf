"""Command routing to Python orchestrators.

Routes commands to appropriate orchestrators via uv run.
"""

import glob
import os
import subprocess
import tomllib
from pathlib import Path

ORCHESTRATORS = {
    "jira": {
        "module": "vds_jira_orchestrator.cli",
        "path": "jira_orchestrator",
        "entry": "vds-jira-cli",
    },
    "confluence": {
        "module": "confluence_orchestrator.cli",
        "path": "confluence_orchestrator",
        "entry": "vds-confluence-cli",
    },
    "bitbucket": {
        "module": "vds_bitbucket_orchestrator.cli",
        "path": "bitbucket_orchestrator",
        "entry": "vds-bitbucket-cli",
    },
    "git": {
        "module": "vds_git_orchestrator.cli",
        "path": "git_orchestrator",
        "entry": "vds-git-orchestrator",
    },
    "pdf": {
        "module": "vds_pdf_orchestrator.cli",
        "path": "pdf_orchestrator",
        "entry": "vds-pdf",
    },
    "excel": {
        "module": "vds_excel_orchestrator.cli",
        "path": "excel_orchestrator",
        "entry": "vds-excel",
    },
    "google_sheets": {
        "module": "vds_google_sheets_orchestrator.cli",
        "path": "google_sheets_orchestrator",
        "entry": "vds-google-sheets-cli",
    },
    "elastic": {
        "module": "vds_elastic_orchestrator.cli",
        "path": "elastic_orchestrator",
        "entry": "vds-elastic",
    },
    "grafana": {
        "module": "vds_grafana_orchestrator.cli",
        "path": "grafana_orchestrator",
        "entry": "vds-grafana",
    },
    "sonarqube": {
        "module": "vds_sonarqube_orchestrator.cli",
        "path": "sonarqube_orchestrator",
        "entry": "vds-sonarqube",
    },
    "brd": {
        "module": "vds_brd_orchestrator.cli",
        "path": "brd_orchestrator",
        "entry": "vds-brd",
    },
    "markdown": {
        "module": "vds_markdown_orchestrator.cli",
        "path": "markdown_orchestrator",
        "entry": "vds-markdown",
    },
    "mcp": {
        "module": "vds_mcp_server.cli",
        "path": "mcp_server",
        "entry": "vds-mcp-server",
    },
    "vidp": {
        "module": "vds_vidp_orchestrator.cli",
        "path": "vidp_orchestrator",
        "entry": "vds-vidp",
    },
}


def _project_scripts(project_dir: Path) -> set[str]:
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found for orchestrator: {project_dir}")
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    if isinstance(scripts, dict):
        return set(scripts.keys())
    return set()


def _script_target(project_dir: Path, entry: str) -> str | None:
    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return None
    target = scripts.get(entry)
    return target if isinstance(target, str) else None


def _target_module_exists(project_dir: Path, target: str) -> bool:
    """Check if a module target exists.

    Handles two layouts:
    - src-layout: project/src/<package>/...  (jira_orchestrator, confluence_orchestrator)
    - root-layout: project/<package>/...      (vds_evolution — package at project root)

    For root-layout packages, the package directory name itself is stripped from
    the module path before the lookup, so "vds_evolution.cli" resolves to
    project_dir/cli.py (not project_dir/vds_evolution/cli.py).
    """
    module_path = target.split(":", 1)[0].strip()
    if not module_path:
        return False

    parts = module_path.split(".")
    parts[0]

    # Root-level lookup: package lives directly under project_dir
    # Strip the top-level package so "vds_evolution.cli" → project_dir/cli.py
    relative_parts = parts[1:] if len(parts) >= 2 else parts

    root_module_file = project_dir / Path(*relative_parts)
    root_py_file = root_module_file.with_suffix(".py")
    root_package_init = root_module_file / "__init__.py"
    if root_py_file.exists() or root_package_init.exists():
        return True

    # Src-layout lookup (package inside src/)
    src_dir = project_dir / "src"
    module_file = src_dir / Path(*parts)
    py_file = module_file.with_suffix(".py")
    package_init = module_file / "__init__.py"
    return py_file.exists() or package_init.exists()


def validate_orchestrator(service: str, script_dir: Path) -> tuple[bool, str]:
    """Validate orchestrator project, entrypoint declaration, and module target."""
    if service not in ORCHESTRATORS:
        return False, f"Unknown service: {service}"

    config = ORCHESTRATORS[service]
    project_dir = script_dir / config["path"]
    if not project_dir.exists():
        return False, "❌ Missing project dir"

    pyproject_path = project_dir / "pyproject.toml"
    if not pyproject_path.exists():
        return False, "❌ Missing pyproject.toml"

    entry = config.get("entry")
    if not entry:
        return True, "✅ Available (module)"

    scripts = _project_scripts(project_dir)
    if entry not in scripts:
        return False, f"❌ Missing entry: {entry}"

    target = _script_target(project_dir, entry)
    if not target:
        return False, f"❌ Invalid target for entry: {entry}"

    if not _target_module_exists(project_dir, target):
        return False, f"❌ Broken target module: {target.split(':', 1)[0]}"

    return True, "✅ Available"


def run_orchestrator(service: str, args: list[str], script_dir: Path) -> int:
    """Run orchestrator via uv.

    Args:
        service: Service name (jira, confluence, bitbucket, git)
        args: Command arguments to pass to orchestrator
        script_dir: Base directory containing orchestrators

    Returns:
        int: Exit code from orchestrator (0 for success)

    Raises:
        ValueError: If service is not recognized

    Example:
        >>> exit_code = run_orchestrator("jira", ["search", "project = NTTC"], Path("/path/to/scripts"))
        >>> if exit_code == 0:
        ...     print("Success")
    """
    if service not in ORCHESTRATORS:
        raise ValueError(f"Unknown service: {service}. Available: {list(ORCHESTRATORS.keys())}")

    config = ORCHESTRATORS[service]
    project_dir = script_dir / config["path"]

    if not project_dir.exists():
        raise FileNotFoundError(f"Orchestrator directory not found: {project_dir}")

    # Use uv to run the orchestrator
    entry = config.get("entry")
    if entry:
        ok, status = validate_orchestrator(service, script_dir)
        if not ok:
            raise ValueError(f"Service '{service}' is not runnable: {status}")
        cmd = ["uv", "run", "--project", str(project_dir), entry, *args]
    else:
        cmd = ["uv", "run", "--project", str(project_dir), "python", "-m", config["module"], *args]

    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    orchestrator_src = project_dir / "src"
    existing_path = env.get("PYTHONPATH", "")
    if orchestrator_src.exists():
        env["PYTHONPATH"] = f"{orchestrator_src}{os.pathsep}{existing_path}" if existing_path else str(orchestrator_src)
    # Also prepend workspace .venv site-packages so orchestrators in worktrees can
    # resolve shared workspace dependencies (e.g. vds_platform_core) that are not
    # installed in the orchestrator's own src/ tree.
    venv_site_packages = glob.glob(str(script_dir / ".venv" / "lib" / "python*" / "site-packages"))
    if venv_site_packages:
        current = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{venv_site_packages[0]}{os.pathsep}{current}" if current else venv_site_packages[0]
    # Run from the workspace root so orchestrators with workspace-relative defaults
    # (for example git_orchestrator's default repo-manifest.yaml) behave consistently
    # regardless of the caller's current shell directory.
    result = subprocess.run(cmd, check=False, env=env, cwd=str(script_dir))
    return result.returncode
