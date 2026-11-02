"""P6 WP-6.2 — Makefile target loadout validation tests.

Catches the WP-5.3-class bug: when a service moves between compose files
(services.yml ↔ cli.yml) or a cross-profile depends_on is added, EVERY
Makefile up-*/run-* target's compose-file loadout must resolve without
"undefined service" errors.

Strategy: for each Makefile up-/run- target, extract the recipe, substitute
macros, replace `up -d` / `run --rm <svc>` with `config --quiet`, execute,
assert exit 0 + clean stderr. No Docker daemon needed (only docker CLI for
`compose config`).

Skips gracefully if docker is not on PATH.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MAKEFILE_PATH = REPO_ROOT / "Makefile"
DOCKER_DIR = REPO_ROOT / "docker"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MacroSet(NamedTuple):
    """Resolved Makefile macro values for compose-file flags."""

    dc: str
    infra: str
    services: str
    cli: str
    all_files: str
    build_flag: str

def _extract_macros(makefile_text: str) -> MacroSet:
    """Parse DC / INFRA / SERVICES / CLI / ALL / BUILD_FLAG from Makefile."""

    def _get(pattern: str) -> str:
        m = re.search(pattern, makefile_text, re.MULTILINE)
        return m.group(1).strip() if m else ""

    dc_raw = _get(r"^DC\s*:=\s*(.+)$")
    compose_project = _get(r"^COMPOSE_PROJECT\s*:=\s*(.+)$")
    infra = _get(r"^INFRA\s*:=\s*(.+)$")
    services = _get(r"^SERVICES\s*:=\s*(.+)$")
    cli = _get(r"^CLI\s*:=\s*(.+)$")
    all_files = _get(r"^ALL\s*:=\s*(.+)$")

    # Resolve $(COMPOSE_PROJECT) inside DC definition
    dc = dc_raw.replace("$(COMPOSE_PROJECT)", compose_project)

    return MacroSet(
        dc=dc,
        infra=infra,
        services=services,
        cli=cli,
        all_files=all_files,
        build_flag="",  # NO_BUILD=1 behaviour: empty string → no --build flag
    )

def _substitute_macros(recipe: str, macros: MacroSet) -> str:
    """Expand Makefile macro references in a recipe line."""
    result = recipe
    result = result.replace("$(DC)", macros.dc)
    result = result.replace("$(INFRA)", macros.infra)
    result = result.replace("$(SERVICES)", macros.services)
    result = result.replace("$(CLI)", macros.cli)
    result = result.replace("$(ALL)", macros.all_files)
    result = result.replace("$(BUILD_FLAG)", macros.build_flag)
    # Strip leading tab (recipe indentation)
    result = result.strip()
    return result

def _recipe_to_config_command(recipe: str) -> list[str]:
    """Convert a compose up/run recipe into a `config --quiet` validation command.

    Transformations applied (in order):
    1. ``up -d [--build]`` → ``config --quiet``
    2. ``run --rm <service> [ARGS or --help]`` → ``config --quiet``
    3. Drop trailing tokens that are not compose flags (e.g., ``$(ARGS)``)
    """
    # Tokenise for manipulation
    tokens = recipe.split()

    # Find the index of the docker-compose subcommand (up / run / build / down …)
    subcommand_index: int | None = None
    for i, tok in enumerate(tokens):
        if tok in ("up", "run", "build", "down"):
            subcommand_index = i
            break

    if subcommand_index is None:
        # Cannot determine subcommand → return as-is; caller will handle failure
        return tokens

    # Keep everything up to (but not including) the subcommand, then append config --quiet
    compose_prefix = tokens[:subcommand_index]
    return [*compose_prefix, "config", "--quiet"]

def _parse_makefile_targets(makefile_path: Path) -> dict[str, str]:
    """Return {target_name: substituted_recipe_line} for all up-* and run-* targets.

    Only considers the FIRST non-comment recipe line after the target header.
    Lines starting with ``#`` or ``@`` directives are skipped.
    """
    text = makefile_path.read_text()
    macros = _extract_macros(text)

    targets: dict[str, str] = {}
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        # Match a make target declaration (up-* or run-*)
        target_match = re.match(r"^((?:up|run)-[\w-]+)\s*:", line)
        if target_match:
            target_name = target_match.group(1)
            # Scan ahead for the first non-blank, non-comment recipe line
            i += 1
            while i < len(lines):
                recipe_line = lines[i]
                # Recipe lines are tab-indented
                if not recipe_line.startswith("\t"):
                    break
                stripped = recipe_line.strip()
                # Skip blank lines, comment-only lines, and @ echo / read lines
                if stripped and not stripped.startswith("#") and not stripped.startswith("@"):
                    targets[target_name] = _substitute_macros(stripped, macros)
                    break
                i += 1
            continue
        i += 1

    return targets

def _docker_available() -> bool:
    return shutil.which("docker") is not None

def _stub_env() -> dict[str, str]:
    """Build a sanitised environment for `compose config` structural validation.

    ``compose config`` resolves YAML interpolation before the daemon is involved,
    so variables marked as required (``:?``) must be present even for a pure
    structural check.  We inject safe stubs for those variables only — all other
    host env vars are inherited so that PATH, HOME, etc. remain correct.

    Stubs injected:
    - ``SERVICE_JWT_SECRET_KEY``:  the single ``:?`` required var in the VDS
      compose stack.  A 64-char hex string satisfies any downstream validation.

    This does NOT change the semantics of the loadout test — we are verifying
    that the *file set* + *depends_on graph* is structurally valid, not that the
    container would start successfully with real credentials.
    """
    env = os.environ.copy()
    # Inject stub only when not already supplied by the operator's environment
    env.setdefault("SERVICE_JWT_SECRET_KEY", "stub_jwt_secret_for_compose_config_validation_only")
    return env

def _run_config(
    command_tokens: list[str],
    cwd: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a compose config command and return the result."""
    env = _stub_env()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        command_tokens,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )

# ---------------------------------------------------------------------------
# Test: Makefile parsing
# ---------------------------------------------------------------------------

class TestMakefileParses:
    """Verify that the Makefile contains all expected targets."""

    EXPECTED_UP_TARGETS = {
        "up-infra",
        "up-memory",
        "up-scheduler",
        "up-multi-agent",
        "up-services",
    }

    EXPECTED_RUN_TARGETS = {
        "run-audit",
        "run-audit-migrate",
        "run-pdf",
        "run-progress",
        "run-progress-migrate",
        "run-db-query",
        "run-vds-cli",
    }

    def test_makefile_exists(self) -> None:
        assert MAKEFILE_PATH.exists(), f"Makefile not found at {MAKEFILE_PATH}"

    def test_makefile_parses_correctly(self) -> None:
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        assert targets, "No up-/run- targets parsed from Makefile"
        discovered = set(targets.keys())
        missing_up = self.EXPECTED_UP_TARGETS - discovered
        missing_run = self.EXPECTED_RUN_TARGETS - discovered
        assert not missing_up, f"Missing up-* targets: {missing_up}"
        assert not missing_run, f"Missing run-* targets: {missing_run}"

    def test_all_expected_targets_have_recipe(self) -> None:
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        for name in self.EXPECTED_UP_TARGETS | self.EXPECTED_RUN_TARGETS:
            assert name in targets, f"Target '{name}' has no parsed recipe"
            recipe = targets[name]
            assert recipe, f"Target '{name}' has an empty recipe"

    def test_substituted_recipe_contains_docker_compose(self) -> None:
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        for name, recipe in targets.items():
            assert "docker" in recipe, (
                f"Target '{name}' recipe does not contain 'docker' after substitution: {recipe!r}"
            )

    def test_up_memory_recipe_contains_cli_yml(self) -> None:
        """WP-5.3 fix: up-memory must load cli.yml to resolve memory-migrate."""
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        recipe = targets.get("up-memory", "")
        assert "docker-compose.cli.yml" in recipe, (
            "up-memory does not load docker-compose.cli.yml — "
            "memory-api/worker depends_on memory-migrate which lives in cli.yml "
            "(WP-5.3 regression guard)"
        )

    def test_up_scheduler_recipe_contains_cli_yml(self) -> None:
        """WP-5.3 fix: up-scheduler must load cli.yml for memory-migrate transitive dep."""
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        recipe = targets.get("up-scheduler", "")
        assert "docker-compose.cli.yml" in recipe, (
            "up-scheduler does not load docker-compose.cli.yml — "
            "scheduler-orchestrator depends_on memory-api which depends_on memory-migrate "
            "(cli.yml), WP-5.3 regression guard"
        )

    def test_up_services_recipe_uses_all_macro(self) -> None:
        """up-services must include all three compose files (ALL macro = infra+services+cli)."""
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        recipe = targets.get("up-services", "")
        # After substitution the ALL macro expands to all three files
        assert "docker-compose.cli.yml" in recipe, (
            "up-services does not load docker-compose.cli.yml — "
            "memory-worker depends_on memory-migrate (cli.yml), P5 e8de66d2 regression guard"
        )

# ---------------------------------------------------------------------------
# Test: per-target compose config validation (parametrized)
# ---------------------------------------------------------------------------

def _collect_parametrize_cases() -> list[pytest.param]:
    """Build parametrize cases from parsed Makefile targets."""
    if not MAKEFILE_PATH.exists():
        return []
    try:
        targets = _parse_makefile_targets(MAKEFILE_PATH)
    except Exception:
        return []
    cases = []
    for target_name, recipe in sorted(targets.items()):
        cmd = _recipe_to_config_command(recipe)
        cases.append(pytest.param(target_name, cmd, id=target_name))
    return cases

_PARAMETRIZE_CASES = _collect_parametrize_cases()

@pytest.mark.skipif(not _docker_available(), reason="docker not available on PATH")
@pytest.mark.parametrize("target_name,cmd", _PARAMETRIZE_CASES)
def test_makefile_target_compose_config_validates(
    target_name: str,
    cmd: list[str],
) -> None:
    """Assert that every up-/run-* target's compose loadout passes `config --quiet`.

    Passes when:
    - exit code is 0
    - stderr contains no "undefined service" or "has neither an image nor a build" errors

    The ``--quiet`` flag suppresses the resolved YAML output so failures are
    signalled only via exit code and error messages.
    """
    assert cmd, f"No config command derived for target '{target_name}'"

    result = _run_config(cmd, cwd=REPO_ROOT)

    # Compose config errors that indicate a loadout bug
    fatal_patterns = [
        "undefined service",
        "has neither an image nor a build",
        "service .* depends on service .* which is undefined",
        "no such file or directory",
        "cannot find",
    ]
    stderr_lower = result.stderr.lower()
    found_errors = [p for p in fatal_patterns if re.search(p, stderr_lower)]

    assert result.returncode == 0, (
        f"[{target_name}] compose config returned exit {result.returncode}.\n"
        f"  Command: {' '.join(cmd)}\n"
        f"  stderr: {result.stderr.strip()}"
    )
    assert not found_errors, (
        f"[{target_name}] compose config stderr contains fatal pattern(s) {found_errors!r}.\n"
        f"  Command: {' '.join(cmd)}\n"
        f"  stderr: {result.stderr.strip()}"
    )

# ---------------------------------------------------------------------------
# Focused known-good tests (named; complement the parametrized suite)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _docker_available(), reason="docker not available on PATH")
class TestKnownGoodTargets:
    """Named tests for the specific targets that P5 surfaced as broken."""

    def _validate(self, target_name: str) -> None:
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        assert target_name in targets, f"Target '{target_name}' not found in Makefile"
        cmd = _recipe_to_config_command(targets[target_name])
        result = _run_config(cmd, cwd=REPO_ROOT)
        assert result.returncode == 0, (
            f"[{target_name}] compose config failed (exit {result.returncode}).\n"
            f"  Command: {' '.join(cmd)}\n"
            f"  stderr: {result.stderr.strip()}"
        )

    def test_up_memory_loadout_validates(self) -> None:
        self._validate("up-memory")

    def test_up_scheduler_loadout_validates(self) -> None:
        self._validate("up-scheduler")

    def test_up_services_loadout_validates(self) -> None:
        self._validate("up-services")

    def test_up_multi_agent_loadout_validates(self) -> None:
        self._validate("up-multi-agent")

    def test_up_infra_loadout_validates(self) -> None:
        self._validate("up-infra")

    def test_run_audit_loadout_validates(self) -> None:
        self._validate("run-audit")

    def test_run_audit_migrate_loadout_validates(self) -> None:
        self._validate("run-audit-migrate")

    def test_run_pdf_loadout_validates(self) -> None:
        self._validate("run-pdf")

    def test_run_progress_loadout_validates(self) -> None:
        self._validate("run-progress")

    def test_run_progress_migrate_loadout_validates(self) -> None:
        self._validate("run-progress-migrate")

    def test_run_db_query_loadout_validates(self) -> None:
        self._validate("run-db-query")

    def test_run_vds_cli_loadout_validates(self) -> None:
        self._validate("run-vds-cli")

# ---------------------------------------------------------------------------
# Synthetic-mismatch detection test
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _docker_available(), reason="docker not available on PATH")
class TestSyntheticMismatchDetection:
    """Prove that the validator catches the WP-5.3 bug class.

    A deliberately broken `up-services` target that omits cli.yml will fail
    `compose config` because services.yml references memory-migrate (in cli.yml)
    via depends_on — the exact failure mode from P5.
    """
    def test_services_only_loadout_is_valid(self, tmp_path: Path) -> None:
        """infra.yml + services.yml is a valid standalone combination (v2.15.10+).

        After Tier 3B retirement in v2.15.10 (ADR-INF-10), the migrate containers
        (audit-migrate, memory-migrate, progress-migrate) were removed from cli.yml.
        This means infra.yml + services.yml is now VALID for running long-running
        services — it no longer requires cli.yml for migration dependencies.

        Historical context: pre-v2.15.10, memory-migrate lived in cli.yml and
        missing it caused compose validation to fail. The test
        test_synthetic_missing_cli_yml_for_up_services (pre-v2.15.10) caught this.
        This test verifies the CORRECT behavior post-v2.15.10.
        """
        # services.yml only (no cli.yml) — this is now VALID for running services
        services_only_cmd = [
            "docker",
            "compose",
            "-p",
            "vds-platform",
            "-f",
            "docker/docker-compose.infra.yml",
            "-f",
            "docker/docker-compose.services.yml",
            "--profile",
            "full",
            "config",
            "--quiet",
        ]

        result = _run_config(services_only_cmd, cwd=REPO_ROOT)

        # Post-v2.15.10: infra + services is VALID (no migrate containers needed)
        assert result.returncode == 0, (
            "services-only loadout (infra+services) should be valid post-v2.15.10 "
            "Tier 3B retirement. If this fails, check if migrate containers were "
            "re-added to cli.yml or if profile activation changed.\n"
            f"Command: {' '.join(services_only_cmd)}\n"
            f"stderr: {result.stderr.strip()}\n"
            f"stdout: {result.stdout.strip()}"
        )

    def test_synthetic_correct_loadout_passes(self) -> None:
        """Correct ALL-macro loadout (infra+services+cli) must exit 0."""
        correct_cmd = [
            "docker",
            "compose",
            "-p",
            "vds-platform",
            "-f",
            "docker/docker-compose.infra.yml",
            "-f",
            "docker/docker-compose.services.yml",
            "-f",
            "docker/docker-compose.cli.yml",
            "--profile",
            "full",
            "config",
            "--quiet",
        ]

        result = _run_config(correct_cmd, cwd=REPO_ROOT)

        assert result.returncode == 0, (
            "Correct ALL-macro loadout failed config validation.\n"
            f"  Command: {' '.join(correct_cmd)}\n"
            f"  stderr: {result.stderr.strip()}"
        )

# ---------------------------------------------------------------------------
# Helper unit tests (test the test helpers themselves)
# ---------------------------------------------------------------------------

class TestHelpers:
    """Unit tests for the parsing helpers — no docker required."""

    def test_substitute_macros_dc(self) -> None:
        macros = MacroSet(
            dc="docker compose -p vds-platform",
            infra="-f docker/docker-compose.infra.yml",
            services="-f docker/docker-compose.infra.yml -f docker/docker-compose.services.yml",
            cli="-f docker/docker-compose.infra.yml -f docker/docker-compose.cli.yml",
            all_files="-f docker/docker-compose.infra.yml -f docker/docker-compose.services.yml -f docker/docker-compose.cli.yml",
            build_flag="",
        )
        recipe = "$(DC) $(SERVICES) --profile memory up -d $(BUILD_FLAG)"
        result = _substitute_macros(recipe, macros)
        assert "docker compose -p vds-platform" in result
        assert "$(DC)" not in result
        assert "$(BUILD_FLAG)" not in result

    def test_recipe_to_config_command_up(self) -> None:
        recipe = "docker compose -p vds-platform -f docker/docker-compose.infra.yml up -d --build"
        cmd = _recipe_to_config_command(recipe)
        assert "config" in cmd
        assert "--quiet" in cmd
        assert "up" not in cmd
        assert "--build" not in cmd

    def test_recipe_to_config_command_run(self) -> None:
        recipe = "docker compose -p vds-platform -f docker/docker-compose.infra.yml -f docker/docker-compose.cli.yml --profile audit run --rm audit-orchestrator --help"
        cmd = _recipe_to_config_command(recipe)
        assert "config" in cmd
        assert "--quiet" in cmd
        assert "run" not in cmd
        assert "--rm" not in cmd

    def test_recipe_to_config_command_preserves_file_flags(self) -> None:
        recipe = (
            "docker compose -p vds-platform "
            "-f docker/docker-compose.infra.yml "
            "-f docker/docker-compose.services.yml "
            "-f docker/docker-compose.cli.yml "
            "--profile full up -d"
        )
        cmd = _recipe_to_config_command(recipe)
        # All -f flags must survive
        assert cmd.count("-f") == 3
        assert "docker-compose.infra.yml" in " ".join(cmd)
        assert "docker-compose.services.yml" in " ".join(cmd)
        assert "docker-compose.cli.yml" in " ".join(cmd)

    def test_extract_macros_from_real_makefile(self) -> None:
        if not MAKEFILE_PATH.exists():
            pytest.skip("Makefile not found")
        text = MAKEFILE_PATH.read_text()
        macros = _extract_macros(text)
        assert "docker compose" in macros.dc
        assert "docker-compose.infra.yml" in macros.infra
        assert "docker-compose.services.yml" in macros.services
        assert "docker-compose.cli.yml" in macros.cli
        assert "docker-compose.cli.yml" in macros.all_files

    def test_parse_makefile_returns_nonempty_dict(self) -> None:
        if not MAKEFILE_PATH.exists():
            pytest.skip("Makefile not found")
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        assert len(targets) >= 12, f"Expected at least 12 targets, got {len(targets)}: {list(targets)}"

    def test_parse_makefile_all_targets_start_with_up_or_run(self) -> None:
        if not MAKEFILE_PATH.exists():
            pytest.skip("Makefile not found")
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        for name in targets:
            assert name.startswith("up-") or name.startswith("run-"), (
                f"Unexpected target name '{name}' — parser should only return up-/run-* targets"
            )

    def test_substitute_no_residual_make_vars(self) -> None:
        """After substitution there must be no un-expanded $(VAR) references."""
        if not MAKEFILE_PATH.exists():
            pytest.skip("Makefile not found")
        targets = _parse_makefile_targets(MAKEFILE_PATH)
        for name, recipe in targets.items():
            residual = re.findall(r"\$\([A-Z_]+\)", recipe)
            # $(ARGS) is the only legitimately un-expanded variable (user-supplied at runtime)
            residual = [r for r in residual if r != "$(ARGS)"]
            assert not residual, (
                f"Target '{name}' has un-expanded Make variables after substitution: {residual}\n  recipe: {recipe!r}"
            )
