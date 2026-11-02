"""P6 WP-6.1 — Static-analysis tests for Dockerfile workspace-dep correctness.

Bug class prevented:
    When a workspace dependency is added to a service's pyproject.toml, its
    Dockerfile MUST also be updated to COPY + uv-pip-install the workspace
    package, because Dockerfiles that use ``--no-sources`` disable
    ``[tool.uv.sources]`` workspace resolution.  Without the explicit COPY
    and install path the build fails at *deploy time* with
    "package not found in registry".

    Caught first during P5 WP-5.2 (scheduler + progress both missed
    platform_core).  Fixed at commit 921c95a9.  This suite prevents the next
    regression.

Approach:
    Pure static analysis — read Dockerfiles and pyproject.toml files with
    stdlib only.  No Docker daemon, no image build, no network.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import NamedTuple

import pytest

# ---------------------------------------------------------------------------
# Repository layout constants
# ---------------------------------------------------------------------------

# The root of the vds-scripts workspace (two levels above this file:
#   scripts/tests/test_dockerfile_correctness.py -> scripts/ -> <root>)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Services that have Dockerfiles inside the workspace root.
# Each entry is the directory name (= uv workspace member directory).
_DOCKERIZED_SERVICES: list[str] = [
    "memory_orchestrator",
    "scheduler_orchestrator",
    "progress_report_orchestrator",
    "audit_orchestrator",
    "multi_agent_orchestrator",
    "pdf_orchestrator",
    "db_query_orchestrator",
    "mcp_server",
    "confluence_orchestrator",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


class DockerfileAnalysis(NamedTuple):
    """Parsed facts about a single Dockerfile."""

    copies: list[tuple[str, str]]
    """(src_path, dst_path) pairs from COPY lines (non-FROM-stage COPYs)."""

    install_paths: list[str]
    """Normalised paths present in ``uv pip install`` invocations."""

    uses_no_sources: bool
    """True when at least one ``uv pip install`` call includes ``--no-sources``."""


class MismatchReport(NamedTuple):
    """One missing-dep finding."""

    service_dir: str
    dep_name: str
    dep_dir: str
    missing_copy: bool
    missing_install: bool


# ---------------------------------------------------------------------------
# Helper: parse the root workspace pyproject to build the package-name → dir map
# ---------------------------------------------------------------------------


def _build_workspace_member_map(repo_root: Path) -> dict[str, str]:
    """Return {package-name: directory-name} for every workspace member.

    We iterate each member listed in ``[tool.uv.workspace] members``, read its
    pyproject.toml, and extract the ``name`` field.
    """
    root_pyproject = repo_root / "pyproject.toml"
    text = root_pyproject.read_text(encoding="utf-8")

    # Extract the members list between [tool.uv.workspace] and the next section.
    members_block = re.search(
        r"\[tool\.uv\.workspace\].*?members\s*=\s*\[(.*?)\]",
        text,
        re.DOTALL,
    )
    if not members_block:
        return {}

    member_dirs = re.findall(r'"([^"]+)"', members_block.group(1))

    mapping: dict[str, str] = {}
    for member_dir in member_dirs:
        member_pyproject = repo_root / member_dir / "pyproject.toml"
        if not member_pyproject.exists():
            continue
        member_text = member_pyproject.read_text(encoding="utf-8")
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', member_text, re.MULTILINE)
        if name_match:
            mapping[name_match.group(1)] = member_dir

    return mapping


# ---------------------------------------------------------------------------
# Helper: _parse_pyproject_workspace_deps
# ---------------------------------------------------------------------------


def _parse_pyproject_workspace_deps(
    pyproject_path: Path,
    workspace_member_dirs: set[str],
) -> set[str]:
    """Return the set of workspace-member dep *directory names* declared in pyproject.

    A dep is a workspace dep if:
    1. It appears in ``[tool.uv.sources]`` with ``workspace = true``, AND
    2. Its resolved directory name is in ``workspace_member_dirs``
       (i.e. it is actually a member of the root workspace).

    Parameters
    ----------
    pyproject_path:
        Absolute path to the service's ``pyproject.toml``.
    workspace_member_dirs:
        Set of workspace member *directory* names (e.g. ``{"platform_core",
        "vds_cli_common", ...}``) built from the root pyproject.
    """
    if not pyproject_path.exists():
        return set()

    text = pyproject_path.read_text(encoding="utf-8")
    pkg_name_to_dir = _build_workspace_member_map(pyproject_path.parent.parent)

    # Collect deps declared as workspace = true in [tool.uv.sources]
    sources_block = re.search(
        r"\[tool\.uv\.sources\](.*?)(?=\n\[|\Z)",
        text,
        re.DOTALL,
    )
    if not sources_block:
        return set()

    workspace_dep_names: set[str] = set()
    for line in sources_block.group(1).splitlines():
        m = re.match(r"\s*([a-zA-Z0-9_-]+)\s*=\s*\{.*workspace\s*=\s*true", line)
        if m:
            workspace_dep_names.add(m.group(1))

    # Map package names → directory names; keep only real workspace members
    result: set[str] = set()
    for dep_name in workspace_dep_names:
        dep_dir = pkg_name_to_dir.get(dep_name)
        if dep_dir and dep_dir in workspace_member_dirs:
            result.add(dep_dir)

    return result


# ---------------------------------------------------------------------------
# Helper: _parse_dockerfile_workspace_deps
# ---------------------------------------------------------------------------

_COPY_LINE_RE = re.compile(r"^\s*COPY\s+(?!--from=)(.+?)\s+(/app/.+?)(?:\s+#.*)?\s*$")
_UV_PIP_INSTALL_RE = re.compile(
    r"uv\s+pip\s+install\b(.*?)(?:&&|$)",
    re.DOTALL,
)
_NO_SOURCES_FLAG_RE = re.compile(r"--no-sources\b")
_PATH_TOKEN_RE = re.compile(r"(/\S+)")


def _parse_dockerfile_workspace_deps(dockerfile_path: Path) -> DockerfileAnalysis:
    """Parse a Dockerfile and return its COPY + install surface.

    Handles:
    * Multi-line ``RUN`` continuations (backslash continuation).
    * ``COPY src /app/dst`` — extracts (src, dst) pairs.
    * ``uv pip install --no-sources /app/foo /app/bar`` — extracts path tokens.
    * ``--no-sources`` presence flag.
    * ``COPY . /app/`` (memory's "copy everything" pattern) — represented as
      src=".".
    """
    if not dockerfile_path.exists():
        return DockerfileAnalysis(copies=[], install_paths=[], uses_no_sources=False)

    raw = dockerfile_path.read_text(encoding="utf-8")

    # Join backslash-continued lines so we see full RUN commands.
    joined = re.sub(r"\\\n\s*", " ", raw)

    copies: list[tuple[str, str]] = []
    install_paths: list[str] = []
    uses_no_sources = False

    for line in joined.splitlines():
        # --- COPY lines (skip multi-stage --from= copies) ---
        stripped = line.strip()
        if stripped.upper().startswith("COPY") and "--from=" not in stripped:
            # COPY . /app/  (memory pattern)
            dot_match = re.match(r"COPY\s+\.\s+(/app/\S*)", stripped, re.IGNORECASE)
            if dot_match:
                copies.append((".", dot_match.group(1).rstrip("/")))
                continue

            # COPY src /app/dst [# comment]
            m = re.match(
                r"COPY\s+(\S+)\s+(/app/\S*?)(?:\s*#.*)?$",
                stripped,
                re.IGNORECASE,
            )
            if m:
                copies.append((m.group(1).rstrip("/"), m.group(2).rstrip("/")))

        # --- uv pip install lines ---
        if "uv pip install" in line and "--from=" not in line:
            for install_match in _UV_PIP_INSTALL_RE.finditer(line):
                args = install_match.group(1)
                if _NO_SOURCES_FLAG_RE.search(args):
                    uses_no_sources = True
                for path_tok in _PATH_TOKEN_RE.findall(args):
                    # Strip trailing brackets like /app/memory_orchestrator[server,...]
                    clean = re.sub(r"\[.*?\]$", "", path_tok).rstrip("/")
                    install_paths.append(clean)

    return DockerfileAnalysis(
        copies=copies,
        install_paths=install_paths,
        uses_no_sources=uses_no_sources,
    )


# ---------------------------------------------------------------------------
# Core assertion helper
# ---------------------------------------------------------------------------


def _assert_workspace_deps_in_dockerfile(
    service_dir: str,
    repo_root: Path,
    *,
    workspace_member_dirs: set[str] | None = None,
) -> list[MismatchReport]:
    """Return a list of MismatchReport for every workspace dep missing from the
    service's Dockerfile.  Empty list means the service is compliant.

    Returns an empty list if:
    - The service has no Dockerfile (not containerised).
    - The Dockerfile uses ``uv pip install`` WITHOUT ``--no-sources`` (workspace
      resolution is handled by uv natively, so no manual COPY+install required).
    - ``COPY . /app/`` is present (memory's "copy everything" pattern; workspace
      deps are implicitly available).
    """
    dockerfile_path = repo_root / service_dir / "Dockerfile"
    pyproject_path = repo_root / service_dir / "pyproject.toml"

    if not dockerfile_path.exists():
        return []

    if workspace_member_dirs is None:
        pkg_to_dir = _build_workspace_member_map(repo_root)
        workspace_member_dirs = set(pkg_to_dir.values())

    analysis = _parse_dockerfile_workspace_deps(dockerfile_path)
    workspace_deps = _parse_pyproject_workspace_deps(pyproject_path, workspace_member_dirs)
    # Exclude self from the dep check (the service installs itself last)
    workspace_deps.discard(service_dir)

    if not workspace_deps:
        return []

    # If no --no-sources anywhere, workspace resolution is implicit → OK
    if not analysis.uses_no_sources:
        return []

    # If "COPY . /app/" is present, all workspace packages are available → OK
    if any(src == "." for src, _dst in analysis.copies):
        return []

    mismatches: list[MismatchReport] = []
    copy_srcs = {src for src, _dst in analysis.copies}
    # Normalise install paths: strip /app/ prefix for comparison
    install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}

    for dep_dir in sorted(workspace_deps):
        # A dep_dir like "platform_core" may appear in COPY as:
        #   platform_core              (relative, scheduler/progress style)
        #   WHO-project/vds-scripts/platform_core  (audit style)
        #   /app/platform_core         (would be unusual but handle it)
        copied = (
            dep_dir in copy_srcs
            or any(s.endswith("/" + dep_dir) for s in copy_srcs)
            or any(s == f"WHO-project/vds-scripts/{dep_dir}" for s in copy_srcs)
        )
        installed = dep_dir in install_bare or f"/app/{dep_dir}" in analysis.install_paths

        if not copied or not installed:
            mismatches.append(
                MismatchReport(
                    service_dir=service_dir,
                    dep_name=dep_dir,
                    dep_dir=dep_dir,
                    missing_copy=not copied,
                    missing_install=not installed,
                )
            )

    return mismatches


# ===========================================================================
# Concrete per-service tests (RED→GREEN narrative; all should be GREEN now)
# ===========================================================================


class TestSchedulerOrchestratorDockerfile:
    """scheduler_orchestrator Dockerfile must include platform_core (P5 WP-5.2 fix)."""

    def test_scheduler_orchestrator_dockerfile_has_platform_core(self) -> None:
        """platform_core must be COPY'd and installed in scheduler Dockerfile."""
        dockerfile = _REPO_ROOT / "scheduler_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)

        copy_srcs = {src for src, _dst in analysis.copies}
        assert "platform_core" in copy_srcs, "scheduler Dockerfile is missing: COPY platform_core /app/platform_core"

        install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}
        assert "platform_core" in install_bare, "scheduler Dockerfile is missing /app/platform_core in uv pip install"

    def test_scheduler_orchestrator_uses_no_sources(self) -> None:
        """scheduler Dockerfile must use --no-sources (workspace resolution off)."""
        dockerfile = _REPO_ROOT / "scheduler_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)
        assert analysis.uses_no_sources, (
            "scheduler Dockerfile no longer uses --no-sources; update the invariant check if this is intentional"
        )


class TestProgressReportOrchestratorDockerfile:
    """progress_report_orchestrator Dockerfile must include platform_core (P5 WP-5.2 fix)."""

    def test_progress_report_orchestrator_dockerfile_has_platform_core(self) -> None:
        """platform_core must be COPY'd and installed in progress Dockerfile."""
        dockerfile = _REPO_ROOT / "progress_report_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)

        copy_srcs = {src for src, _dst in analysis.copies}
        assert "platform_core" in copy_srcs, "progress Dockerfile is missing: COPY platform_core /app/platform_core"

        install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}
        assert "platform_core" in install_bare, "progress Dockerfile is missing /app/platform_core in uv pip install"


class TestMemoryOrchestratorDockerfile:
    """memory_orchestrator uses COPY . /app/ so workspace resolution is implicit."""

    def test_memory_orchestrator_dockerfile_workspace_resolution(self) -> None:
        """memory Dockerfile must either lack --no-sources OR use COPY . /app/."""
        dockerfile = _REPO_ROOT / "memory_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)

        # Memory copies entire workspace context — all deps are present.
        copies_all = any(src == "." for src, _dst in analysis.copies)

        # Either it doesn't restrict workspace resolution, or it copies everything.
        assert (not analysis.uses_no_sources) or copies_all, (
            "memory Dockerfile uses --no-sources without COPY . /app/; workspace deps may be missing from the image"
        )

    def test_memory_orchestrator_installs_platform_core(self) -> None:
        """memory Dockerfile must explicitly install platform_core."""
        dockerfile = _REPO_ROOT / "memory_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)
        install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}
        assert "platform_core" in install_bare, "memory Dockerfile is missing /app/platform_core in uv pip install"


class TestAuditOrchestratorDockerfile:
    """audit_orchestrator uses WHO-project/vds-scripts/<pkg> COPY paths."""

    def test_audit_orchestrator_dockerfile_has_platform_core(self) -> None:
        """platform_core must be COPY'd and installed in audit Dockerfile."""
        dockerfile = _REPO_ROOT / "audit_orchestrator" / "Dockerfile"
        analysis = _parse_dockerfile_workspace_deps(dockerfile)

        copy_srcs = {src for src, _dst in analysis.copies}
        platform_core_copied = "platform_core" in copy_srcs or any("platform_core" in s for s in copy_srcs)
        assert platform_core_copied, "audit Dockerfile is missing COPY ... platform_core /app/platform_core"

        install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}
        assert "platform_core" in install_bare, "audit Dockerfile is missing /app/platform_core in uv pip install"


# ===========================================================================
# Synthetic mismatch detector (RED test to confirm helper catches the bug)
# ===========================================================================


class TestValidatorFlagsMissingWorkspaceDep:
    """Ensure the helper correctly flags a mismatched Dockerfile+pyproject pair."""

    def test_validator_flags_missing_workspace_dep_in_dockerfile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Inject a synthetic service with a workspace dep absent from Dockerfile.

        The helper must return at least one MismatchReport for the missing dep.
        This is the RED-phase confirmation test: it validates that
        ``_assert_workspace_deps_in_dockerfile`` actually detects the bug class.
        """
        # --- Synthetic workspace root ---
        fake_root = tmp_path / "fake_workspace"
        fake_root.mkdir()

        # Root pyproject.toml (workspace manifest)
        (fake_root / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "fake-workspace"
                version = "0.0.0"
                requires-python = ">=3.11"

                [tool.uv]
                package = false

                [tool.uv.workspace]
                members = [
                  "my_service",
                  "vds_secret_pkg",
                ]
            """),
            encoding="utf-8",
        )

        # Workspace member: vds_secret_pkg (the dep we'll OMIT from Dockerfile)
        secret_dir = fake_root / "vds_secret_pkg"
        secret_dir.mkdir()
        (secret_dir / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "vds-secret-pkg"
                version = "0.1.0"
                requires-python = ">=3.11"
                dependencies = []
            """),
            encoding="utf-8",
        )

        # Service: my_service — declares vds-secret-pkg as a workspace dep
        service_dir = fake_root / "my_service"
        service_dir.mkdir()
        (service_dir / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "vds-my-service"
                version = "0.1.0"
                requires-python = ">=3.11"
                dependencies = ["vds-secret-pkg"]

                [tool.uv.sources]
                vds-secret-pkg = { workspace = true }
            """),
            encoding="utf-8",
        )

        # Dockerfile: uses --no-sources but DOES NOT COPY or install vds_secret_pkg
        (service_dir / "Dockerfile").write_text(
            textwrap.dedent("""\
                FROM python:3.14-slim
                WORKDIR /app
                COPY my_service/pyproject.toml /app/my_service/
                COPY my_service/src /app/my_service/src
                RUN uv pip install --python /opt/venv/bin/python --no-sources \\
                    /app/my_service
            """),
            encoding="utf-8",
        )

        # Run the checker
        pkg_to_dir = _build_workspace_member_map(fake_root)
        workspace_member_dirs = set(pkg_to_dir.values())

        mismatches = _assert_workspace_deps_in_dockerfile(
            "my_service",
            fake_root,
            workspace_member_dirs=workspace_member_dirs,
        )

        assert len(mismatches) >= 1, (
            f"Expected at least one MismatchReport for missing 'vds_secret_pkg', got {mismatches}"
        )
        dep_dirs = {m.dep_dir for m in mismatches}
        assert "vds_secret_pkg" in dep_dirs, f"Expected 'vds_secret_pkg' in flagged deps, got {dep_dirs}"
        # Both copy and install should be flagged missing
        report = next(m for m in mismatches if m.dep_dir == "vds_secret_pkg")
        assert report.missing_copy, "Should flag missing COPY for vds_secret_pkg"
        assert report.missing_install, "Should flag missing install for vds_secret_pkg"

    def test_validator_passes_compliant_dockerfile(self, tmp_path: Path) -> None:
        """A Dockerfile that correctly COPY+installs all workspace deps must pass."""
        fake_root = tmp_path / "fake_workspace_ok"
        fake_root.mkdir()

        (fake_root / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "fake-workspace"
                version = "0.0.0"
                requires-python = ">=3.11"

                [tool.uv]
                package = false

                [tool.uv.workspace]
                members = ["my_service", "shared_lib"]
            """),
            encoding="utf-8",
        )

        shared_dir = fake_root / "shared_lib"
        shared_dir.mkdir()
        (shared_dir / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "vds-shared-lib"
                version = "0.1.0"
                requires-python = ">=3.11"
                dependencies = []
            """),
            encoding="utf-8",
        )

        service_dir = fake_root / "my_service"
        service_dir.mkdir()
        (service_dir / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [project]
                name = "vds-my-service"
                version = "0.1.0"
                requires-python = ">=3.11"
                dependencies = ["vds-shared-lib"]

                [tool.uv.sources]
                vds-shared-lib = { workspace = true }
            """),
            encoding="utf-8",
        )

        # Compliant Dockerfile: copies and installs shared_lib
        (service_dir / "Dockerfile").write_text(
            textwrap.dedent("""\
                FROM python:3.14-slim
                WORKDIR /app
                COPY my_service/pyproject.toml /app/my_service/
                COPY my_service/src /app/my_service/src
                COPY shared_lib /app/shared_lib
                RUN uv pip install --python /opt/venv/bin/python --no-sources \\
                    /app/shared_lib \\
                    /app/my_service
            """),
            encoding="utf-8",
        )

        pkg_to_dir = _build_workspace_member_map(fake_root)
        workspace_member_dirs = set(pkg_to_dir.values())

        mismatches = _assert_workspace_deps_in_dockerfile(
            "my_service",
            fake_root,
            workspace_member_dirs=workspace_member_dirs,
        )
        assert mismatches == [], f"Compliant Dockerfile should produce no mismatches, got: {mismatches}"


# ===========================================================================
# Generic parametrized test — the actual bug-catcher for future PRs
# ===========================================================================


def _get_service_ids() -> list[str]:
    """Return service directory names that have both a Dockerfile and pyproject."""
    result = []
    for svc in _DOCKERIZED_SERVICES:
        dockerfile = _REPO_ROOT / svc / "Dockerfile"
        pyproject = _REPO_ROOT / svc / "pyproject.toml"
        if dockerfile.exists() and pyproject.exists():
            result.append(svc)
    return result


@pytest.mark.parametrize("service_dir", _get_service_ids())
def test_all_dockerfiles_match_pyproject_workspace_deps(service_dir: str) -> None:
    """For each service, every workspace dep in pyproject must appear in the Dockerfile.

    This is the generic regression guard: if a future PR adds a workspace dep
    to a service's pyproject.toml without updating its Dockerfile, this test
    will fail for that service.

    Exemptions (no assertion made):
    - Dockerfiles that use ``COPY . /app/`` (workspace available wholesale).
    - Dockerfiles that use ``uv pip install`` without ``--no-sources``
      (uv handles workspace resolution natively).
    """
    pkg_to_dir = _build_workspace_member_map(_REPO_ROOT)
    workspace_member_dirs = set(pkg_to_dir.values())

    mismatches = _assert_workspace_deps_in_dockerfile(
        service_dir,
        _REPO_ROOT,
        workspace_member_dirs=workspace_member_dirs,
    )

    if mismatches:
        lines = []
        for m in mismatches:
            parts = []
            if m.missing_copy:
                parts.append(f"missing COPY {m.dep_dir} /app/{m.dep_dir}")
            if m.missing_install:
                parts.append(f"missing /app/{m.dep_dir} in uv pip install")
            lines.append(f"  - {m.dep_dir}: {'; '.join(parts)}")
        detail = "\n".join(lines)
        pytest.fail(
            f"Dockerfile for '{service_dir}' is missing workspace deps:\n{detail}\n\n"
            "Fix: add the COPY line(s) and /app/<dep> to the uv pip install command."
        )


# ===========================================================================
# Parser unit tests — validate the helpers in isolation
# ===========================================================================


class TestParseDockerfileWorkspaceDeps:
    """Unit tests for ``_parse_dockerfile_workspace_deps``."""

    def _write_dockerfile(self, tmp_path: Path, content: str) -> Path:
        df = tmp_path / "Dockerfile"
        df.write_text(textwrap.dedent(content), encoding="utf-8")
        return df

    def test_extracts_copy_lines(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            COPY platform_core /app/platform_core
            COPY vds_cli_common /app/vds_cli_common
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        copy_srcs = {src for src, _dst in analysis.copies}
        assert "platform_core" in copy_srcs
        assert "vds_cli_common" in copy_srcs

    def test_detects_no_sources_flag(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            RUN uv pip install --python /opt/venv/bin/python --no-sources \\
                /app/vds_cli_common \\
                /app/my_service
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        assert analysis.uses_no_sources is True

    def test_no_no_sources_flag(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            RUN uv pip install --python /opt/venv/bin/python \\
                /app/memory_orchestrator[server,celery]
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        assert analysis.uses_no_sources is False

    def test_extracts_install_paths(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            RUN uv pip install --python /opt/venv/bin/python --no-sources \\
                /app/platform_core \\
                /app/vds_cli_common \\
                /app/my_service
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        assert "/app/platform_core" in analysis.install_paths
        assert "/app/vds_cli_common" in analysis.install_paths

    def test_strips_extras_from_install_paths(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            RUN uv pip install --python /opt/venv/bin/python \\
                /app/memory_orchestrator[server,celery,mem0]
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        assert "/app/memory_orchestrator" in analysis.install_paths

    def test_detects_copy_dot_pattern(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            COPY . /app/
            RUN uv pip install /app/memory_orchestrator[server]
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        copy_srcs = {src for src, _dst in analysis.copies}
        assert "." in copy_srcs

    def test_skips_from_stage_copies(self, tmp_path: Path) -> None:
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM builder AS runtime
            COPY --from=builder /app/.venv /app/.venv
            COPY platform_core /app/platform_core
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        copy_srcs = {src for src, _dst in analysis.copies}
        # --from= copy should not appear
        assert "/app/.venv" not in copy_srcs
        # Regular COPY should appear
        assert "platform_core" in copy_srcs

    def test_handles_audit_who_project_path(self, tmp_path: Path) -> None:
        """audit Dockerfile uses WHO-project/vds-scripts/<pkg> COPY paths."""
        df = self._write_dockerfile(
            tmp_path,
            """\
            FROM python:3.14-slim
            COPY WHO-project/vds-scripts/platform_core /app/platform_core
            RUN uv pip install --no-sources /app/platform_core /app/audit_orchestrator
            """,
        )
        analysis = _parse_dockerfile_workspace_deps(df)
        copy_srcs = {src for src, _dst in analysis.copies}
        assert "WHO-project/vds-scripts/platform_core" in copy_srcs
        install_bare = {p.removeprefix("/app/") for p in analysis.install_paths}
        assert "platform_core" in install_bare

    def test_missing_dockerfile_returns_empty(self, tmp_path: Path) -> None:
        analysis = _parse_dockerfile_workspace_deps(tmp_path / "Dockerfile")
        assert analysis.copies == []
        assert analysis.install_paths == []
        assert analysis.uses_no_sources is False


class TestBuildWorkspaceMemberMap:
    """Unit tests for ``_build_workspace_member_map``."""

    def test_builds_map_from_synthetic_workspace(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [tool.uv.workspace]
                members = ["pkg_a", "pkg_b"]
            """),
            encoding="utf-8",
        )
        for pkg_dir, pkg_name in [("pkg_a", "vds-pkg-a"), ("pkg_b", "vds-pkg-b")]:
            d = tmp_path / pkg_dir
            d.mkdir()
            (d / "pyproject.toml").write_text(
                f'[project]\nname = "{pkg_name}"\nversion = "0.1.0"\n',
                encoding="utf-8",
            )

        result = _build_workspace_member_map(tmp_path)
        assert result["vds-pkg-a"] == "pkg_a"
        assert result["vds-pkg-b"] == "pkg_b"

    def test_skips_missing_member_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            textwrap.dedent("""\
                [tool.uv.workspace]
                members = ["exists", "missing"]
            """),
            encoding="utf-8",
        )
        exists_dir = tmp_path / "exists"
        exists_dir.mkdir()
        (exists_dir / "pyproject.toml").write_text(
            '[project]\nname = "vds-exists"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        # "missing" directory not created

        result = _build_workspace_member_map(tmp_path)
        assert "vds-exists" in result
        # "missing" silently skipped
        assert len(result) == 1
