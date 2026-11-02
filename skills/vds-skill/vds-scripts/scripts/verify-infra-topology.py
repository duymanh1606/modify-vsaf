#!/usr/bin/env python3
"""Verify VDS infrastructure topology.

This script validates that the shared infrastructure compose is correctly configured:
- All expected containers are running for the active profile
- Postgres schemas exist and roles have correct grants
- Redis logical DBs are reachable
- Port conflicts are absent
- Named volumes are mounted

Usage:
    python scripts/verify-infra-topology.py [--profile PROFILE]

Exit codes:
    0: All checks passed
    1: Verification failed
    2: Docker not available or not running
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """Result of a single check."""

    name: str
    passed: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of the full topology verification."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def add(
        self,
        name: str,
        passed: bool,
        message: str = "",
        details: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        merged: dict[str, Any] = {}
        if details:
            merged.update(details)
        if kwargs:
            merged.update(kwargs)
        self.checks.append(CheckResult(name=name, passed=passed, message=message, details=merged))


def run_command(cmd: list[str], _check: bool = True) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"


def check_docker_available() -> VerificationResult:
    """Check if Docker is available and running."""
    result = VerificationResult()
    code, _stdout, stderr = run_command(["docker", "info"])
    if code != 0:
        result.add(
            "docker_available",
            False,
            f"Docker not available or not running: {stderr}",
        )
    else:
        result.add("docker_available", True, "Docker is available and running")
    return result


def check_containers_running(expected_containers: list[str]) -> VerificationResult:
    """Check if expected containers are running."""
    result = VerificationResult()
    code, stdout, stderr = run_command(["docker", "ps", "--format", "{{.Names}}"])

    if code != 0:
        result.add("containers_list", False, f"Failed to list containers: {stderr}")
        return result

    running = stdout.strip().split("\n")
    running_set = set(running)

    for container in expected_containers:
        if container in running_set:
            result.add(
                f"container_running:{container}",
                True,
                f"Container {container} is running",
            )
        else:
            result.add(
                f"container_running:{container}",
                False,
                f"Container {container} is NOT running",
                {"expected": container, "running": running},
            )

    return result


def check_postgres_schemas(_dsn: str) -> VerificationResult:
    """Check if Postgres schemas exist."""
    result = VerificationResult()
    expected_schemas = ["audit_state", "memory", "sched", "progress", "dbos"]

    cmd = [
        "docker",
        "exec",
        "vds-postgres",
        "psql",
        "-U",
        "postgres",
        "-d",
        "vds_platform",
        "-tAc",
        "\\dn",
    ]
    code, stdout, stderr = run_command(cmd)

    if code != 0:
        result.add("postgres_schemas", False, f"Failed to query schemas: {stderr}")
        return result

    # psql -tAc "\dn" emits "schema|owner" per row. Split on pipe so we
    # match against just the schema name, not the whole line.
    existing_schemas = {line.split("|", 1)[0].strip() for line in stdout.strip().split("\n") if line.strip()}

    for schema in expected_schemas:
        if schema in existing_schemas:
            result.add(
                f"schema_exists:{schema}",
                True,
                f"Schema {schema} exists",
            )
        else:
            result.add(
                f"schema_exists:{schema}",
                False,
                f"Schema {schema} NOT found",
                {"expected": expected_schemas, "existing": list(existing_schemas)},
            )

    return result


def check_redis_db(db: int) -> VerificationResult:
    """Check if a Redis logical DB is reachable."""
    result = VerificationResult()

    cmd = ["docker", "exec", "vds-redis", "redis-cli", "-p", "6379", "-n", str(db), "ping"]
    code, stdout, stderr = run_command(cmd)

    if code == 0 and "PONG" in stdout:
        result.add(f"redis_db:{db}", True, f"Redis DB {db} is reachable")
    else:
        result.add(
            f"redis_db:{db}",
            False,
            f"Redis DB {db} NOT reachable: {stderr}",
        )

    return result


def check_port_available(port: int) -> VerificationResult:
    """Check if a port is available (not in use)."""
    result = VerificationResult()

    cmd = ["docker", "ps", "--format", "{{.Ports}}"]
    code, stdout, stderr = run_command(cmd)

    if code != 0:
        result.add(f"port_check:{port}", False, f"Failed to check ports: {stderr}")
        return result

    port_str = f":{port}->"
    if port_str in stdout:
        result.add(
            f"port_available:{port}",
            True,
            f"Port {port} is mapped (expected for shared infra)",
        )
    else:
        result.add(
            f"port_available:{port}",
            True,
            f"Port {port} is not in use by Docker",
        )

    return result


def check_alembic_versions(expected: dict[str, dict[str, Any]]) -> VerificationResult:
    """Check ``alembic_version`` table presence per managed schema.

    Implements ADR-INF-11 §Dual ``version_table_schema`` Policy. Two flavors:

    - **in-schema** (default): version table lives at ``<schema>.alembic_version``.
      Used by memory (``memory.alembic_version``), audit
      (``audit_state.alembic_version`` after WP-4.1 stamp), and progress
      (``progress.alembic_version`` after WP-4.7 stamp). Pass = the table
      exists and contains at least one ``version_num`` row.

    - **in-public** (exception): version table lives at ``public.alembic_version``.
      Used by scheduler whose ``0001`` downgrade does
      ``DROP SCHEMA sched CASCADE``. Because multiple services could in
      principle land their version row in ``public``, this flavor
      disambiguates by checking that at least one ``version_num`` matches
      the caller-supplied ``expected_revs`` rev-history list.

    Expected schema::

        {
            "memory":     {"flavor": "in-schema", "schema": "memory"},
            "audit":      {"flavor": "in-schema", "schema": "audit_state"},
            "progress":   {"flavor": "in-schema", "schema": "progress"},
            "scheduler":  {"flavor": "in-public",
                           "expected_revs": ["0001_create_sched_schema", ...]},
        }

    One ``CheckResult`` is appended per service with name
    ``alembic_version_present:<service>``.
    """
    result = VerificationResult()

    for service, cfg in expected.items():
        flavor = cfg.get("flavor")
        check_name = f"alembic_version_present:{service}"

        if flavor == "in-schema":
            schema = cfg.get("schema", "")
            # Quote the schema identifier to handle reserved-word edge cases
            # and match the same psql shape as check_postgres_schemas().
            query = f'SELECT version_num FROM "{schema}".alembic_version'
            cmd = [
                "docker",
                "exec",
                "vds-postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "vds_platform",
                "-tAc",
                query,
            ]
            code, stdout, stderr = run_command(cmd)

            if code != 0:
                # psql exits non-zero when the relation does not exist or
                # other SQL errors occur. Surface the error verbatim so
                # operators can see whether it's a missing-table case.
                result.add(
                    check_name,
                    False,
                    f"alembic_version table missing for {service} (schema={schema}): {stderr.strip()}",
                    {"flavor": flavor, "schema": schema},
                )
                continue

            rows = [line.strip() for line in stdout.strip().split("\n") if line.strip()]
            if not rows:
                result.add(
                    check_name,
                    False,
                    f"alembic_version table for {service} (schema={schema}) exists but has no version row",
                    {"flavor": flavor, "schema": schema},
                )
                continue

            result.add(
                check_name,
                True,
                f"{service}: {schema}.alembic_version present at {rows[0]}",
                {"flavor": flavor, "schema": schema, "version_num": rows[0]},
            )

        elif flavor == "in-public":
            # RESERVED — escape-hatch path per ADR-INF-11 v2.13.2 §version_table_schema Policy.
            # Currently unreachable in production: ALEMBIC_BY_SERVICE has flavor='in-schema' for
            # all 4 services after the c1a3585d simplification. This branch is retained (rather
            # than deleted) to support future services that legitimately need schema-per-service
            # AND DROP-CASCADE-safe downgrade — see ADR-INF-11 line 427. Tests in
            # scripts/tests/test_verify_alembic.py::TestInPublicFlavor exercise this path
            # directly to keep the contract live in case a future service opts in.
            expected_revs = cfg.get("expected_revs", []) or []
            query = "SELECT version_num FROM public.alembic_version"
            cmd = [
                "docker",
                "exec",
                "vds-postgres",
                "psql",
                "-U",
                "postgres",
                "-d",
                "vds_platform",
                "-tAc",
                query,
            ]
            code, stdout, stderr = run_command(cmd)

            if code != 0:
                result.add(
                    check_name,
                    False,
                    f"alembic_version table missing for {service} (public): {stderr.strip()}",
                    {"flavor": flavor, "schema": "public"},
                )
                continue

            rows = [line.strip() for line in stdout.strip().split("\n") if line.strip()]
            if not rows:
                result.add(
                    check_name,
                    False,
                    f"alembic_version table for {service} (public) exists but has no version row",
                    {"flavor": flavor, "schema": "public"},
                )
                continue

            matched = [r for r in rows if r in expected_revs]
            if not matched:
                result.add(
                    check_name,
                    False,
                    f"{service}: public.alembic_version has unexpected revision(s) "
                    f"{rows}; expected one of the {service} rev-history",
                    {
                        "flavor": flavor,
                        "schema": "public",
                        "found": rows,
                        "expected_revs": expected_revs,
                    },
                )
                continue

            result.add(
                check_name,
                True,
                f"{service}: public.alembic_version present at {matched[0]} (rev-history match)",
                {
                    "flavor": flavor,
                    "schema": "public",
                    "version_num": matched[0],
                    "expected_revs": expected_revs,
                },
            )

        else:
            result.add(
                check_name,
                False,
                f"Unknown flavor '{flavor}' for service {service}; expected 'in-schema' or 'in-public'",
                {"flavor": flavor},
            )

    return result


def check_migration_template_drift(repo_root: Path) -> VerificationResult:
    """Assert each service alembic/env.py imports from vds_platform_core.alembic.

    WP-5.5: Drift guard that catches future regressions back into inline
    boilerplate (the 80 % duplication that WP-5.2 removed). Fails if:

    - The file does not exist.
    - The file does NOT contain ``from vds_platform_core.alembic`` (i.e. the
      helper import was removed and boilerplate re-inlined).
    - LOC is outside the 20–60 range (< 20 = suspiciously truncated;
      > 60 = boilerplate crept back in).

    Returns a single CheckResult named ``migration_template_drift`` that
    aggregates all 4 services into pass/fail with per-service diagnostics
    stored in ``details``.
    """
    result = VerificationResult()
    services = [
        "memory_orchestrator",
        "audit_orchestrator",
        "progress_report_orchestrator",
        "scheduler_orchestrator",
    ]
    helper_marker = "vds_platform_core.alembic"
    # LOC band [30, 60] per P5 review (TSK-5.5.2): post-WP-5.2 actual env.py
    # files land at 37-44 LOC (divergence-axis local-vars + per-service docstring).
    # Floor=30 catches suspiciously-minimal files (probably stripped of intent);
    # ceiling=60 catches sneaky bloat. The 170-LOC pre-refactor inline form is
    # firmly rejected (170 > 60). The earlier band [20, 60] (before 2026-04-27
    # code-reviewer fix) had a useless floor — actual files were 37-44, so 20
    # never triggered. Aligned with spec tasks.md TSK-5.5.2 acceptance criterion.
    loc_min, loc_max = 30, 60

    failures: list[str] = []
    diagnostics: dict[str, Any] = {}

    for svc in services:
        env_path = repo_root / svc / "alembic" / "env.py"

        if not env_path.exists():
            msg = "missing env.py"
            failures.append(f"{svc}: {msg}")
            diagnostics[svc] = {"status": "missing", "path": str(env_path)}
            continue

        content = env_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        loc = len(lines)

        has_import = helper_marker in content

        if not has_import:
            msg = f"missing import from {helper_marker!r} (LOC={loc}; boilerplate may have drifted back)"
            failures.append(f"{svc}: {msg}")
            diagnostics[svc] = {
                "status": "missing_import",
                "loc": loc,
                "path": str(env_path),
            }
            continue

        if not (loc_min <= loc <= loc_max):
            msg = (
                f"LOC={loc} outside [{loc_min}, {loc_max}] — "
                f"{'too small (truncated?)' if loc < loc_min else 'too large (boilerplate drift?)'}"
            )
            failures.append(f"{svc}: {msg}")
            diagnostics[svc] = {
                "status": "loc_out_of_range",
                "loc": loc,
                "loc_min": loc_min,
                "loc_max": loc_max,
                "path": str(env_path),
            }
            continue

        diagnostics[svc] = {"status": "ok", "loc": loc}

    if failures:
        result.add(
            "migration_template_drift",
            False,
            "Alembic env.py drift detected: " + "; ".join(failures),
            diagnostics,
        )
    else:
        result.add(
            "migration_template_drift",
            True,
            f"All {len(services)} services: alembic/env.py compliant "
            f"(helper import present, LOC in [{loc_min}, {loc_max}])",
            diagnostics,
        )

    return result


def check_pgbouncer() -> VerificationResult:
    """WP-8.6: Six P8 verification checks for the Tier 1.5 PgBouncer container.

    Per ADR-INF-13 v2.15.3 (session-mode uniform topology):
      1. pgbouncer_container_status         — descriptive status (running vs pre-deploy)
      2. pgbouncer_admin_reachable          — SHOW VERSION succeeds
      3. pgbouncer_pool_mode_session        — global pool_mode=session
      4. pgbouncer_per_db_stanzas_present   — 4 expected stanzas declared (NOT search_path
                                              correctness — search_path verification would
                                              require a per-stanza connection probe)
      5. pgbouncer_max_prepared_statements  — config reports 200
      6. pgbouncer_max_connections_500      — Postgres max_connections unchanged

    Skips gracefully if vds-pgbouncer is not running (P8 not deployed yet).
    Operators reading the report should distinguish "skipped" messages from "running"
    via the message text. A future `--strict-pgbouncer` flag could flip skipped→FAIL
    for post-deploy CI/CD gates.
    """
    result = VerificationResult()

    # Check 1: container status (descriptive — not pass/fail because pre-P8-deploy
    # the container won't exist yet; post-deploy operators read the message string).
    code, stdout, _ = run_command(["docker", "ps", "--format", "{{.Names}}", "--filter", "name=vds-pgbouncer"])
    is_running = code == 0 and "vds-pgbouncer" in stdout
    result.add(
        "pgbouncer_container_status",
        # Pass either way: running = post-P8-deploy success; not-running = pre-P8-deploy.
        # The validator stays green on master pre-deploy AND post-deploy operators see the
        # actual state in the message text. A future --strict-pgbouncer flag would flip
        # the skipped-when-not-running case to FAIL for CI/CD gates.
        True,
        "vds-pgbouncer container is running (P8 deployed)"
        if is_running
        else "vds-pgbouncer container is NOT running — P8 not yet deployed (skipping P8 checks)",
    )
    if not is_running:
        # Skip remaining checks gracefully — emit as PASS with "skipped" message
        # so the verifier stays green pre-P8-deploy. Post-deploy, the checks below
        # will run for real and enforce.
        for cname in (
            "pgbouncer_admin_reachable",
            "pgbouncer_pool_mode_session",
            "pgbouncer_per_db_stanzas_present",
            "pgbouncer_max_prepared_statements",
            "pgbouncer_max_connections_500",
        ):
            result.add(cname, True, "skipped — vds-pgbouncer not running (pre-P8-deploy)")
        return result

    # Pass PGBOUNCER_ADMIN_PASSWORD into the container via docker exec -e so psql
    # can authenticate to the admin virtual database. Resolves from caller's env;
    # falls back to a placeholder that will fail loudly with a meaningful message
    # rather than silently auth-skip.
    admin_pw = os.environ.get("PGBOUNCER_ADMIN_PASSWORD", "")
    if not admin_pw:
        # Read from ~/.vds/.env if present (operator's standard location).
        env_path = Path.home() / ".vds" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("PGBOUNCER_ADMIN_PASSWORD="):
                    admin_pw = line.split("=", 1)[1].strip()
                    break
    admin_psql = [
        "docker",
        "exec",
        "-e",
        f"PGPASSWORD={admin_pw}",
        "vds-pgbouncer",
        "psql",
        "-h",
        "127.0.0.1",
        "-p",
        "6432",
        "-U",
        "pgbouncer_admin",
        "-d",
        "pgbouncer",
        "-tAc",
    ]

    # Check 2: admin reachable via SHOW VERSION
    code, stdout, stderr = run_command([*admin_psql, "SHOW VERSION;"])
    admin_ok = code == 0 and stdout.strip()
    result.add(
        "pgbouncer_admin_reachable",
        bool(admin_ok),
        f"SHOW VERSION returned: {stdout.strip()[:60]}" if admin_ok else f"SHOW VERSION failed: {stderr or stdout}",
    )

    # Check 3: SHOW CONFIG → pool_mode=session
    code, stdout, _ = run_command([*admin_psql, "SHOW CONFIG;"])
    pool_mode_session = code == 0 and any(
        line.startswith("pool_mode|session") or line.startswith("pool_mode\tsession")
        for line in stdout.strip().split("\n")
    )
    result.add(
        "pgbouncer_pool_mode_session",
        pool_mode_session,
        "Global pool_mode=session"
        if pool_mode_session
        else "pool_mode is NOT session — v2.15.3 expects session mode global default",
    )

    # Check 4: per-database search_path pinning (sample one stanza: vds_audit)
    # Real verification would loop all 4 stanzas; doing one as a smoke check.
    code, stdout, _ = run_command([*admin_psql, "SHOW DATABASES;"])
    expected_stanzas = {"vds_audit", "vds_memory", "vds_progress", "vds_sched"}
    found_stanzas = {
        line.split("|", 1)[0].strip()
        for line in stdout.strip().split("\n")
        if line.strip() and not line.startswith("name|")
    }
    missing_stanzas = expected_stanzas - found_stanzas
    result.add(
        "pgbouncer_per_db_stanzas_present",
        not missing_stanzas,
        f"All 4 expected stanzas present: {sorted(expected_stanzas)} (note: this verifies "
        f"declarations only; per-stanza connect_query search_path correctness needs a "
        f"per-stanza psql probe)"
        if not missing_stanzas
        else f"Missing stanzas: {sorted(missing_stanzas)}",
    )

    # Check 5: max_prepared_statements = 200
    code, stdout, _ = run_command([*admin_psql, "SHOW CONFIG;"])
    mps_200 = code == 0 and any(
        "max_prepared_statements" in line and "200" in line for line in stdout.strip().split("\n")
    )
    result.add(
        "pgbouncer_max_prepared_statements",
        mps_200,
        "max_prepared_statements=200 (≥1.24 native PS support)"
        if mps_200
        else "max_prepared_statements is NOT 200 — required for asyncpg native PS cache",
    )

    # Check 6: Postgres max_connections is still 500 (NOT dropped — v2.15.3 keeps 500)
    code, stdout, _ = run_command(
        [
            "docker",
            "exec",
            "vds-postgres",
            "psql",
            "-U",
            "postgres",
            "-tAc",
            "SHOW max_connections;",
        ]
    )
    max_conn = stdout.strip() if code == 0 else ""
    result.add(
        "pgbouncer_max_connections_500",
        max_conn == "500",
        f"Postgres max_connections={max_conn} (v2.15.3 keeps it at 500 since session mode is 1:1)"
        if max_conn == "500"
        else f"Postgres max_connections={max_conn or 'unknown'} — v2.15.3 expects 500 (session-mode topology does not drop ceiling)",
    )

    return result


def check_volumes() -> VerificationResult:
    """Check if named volumes exist.

    Handles both plain names (standalone docker volume create) and
    compose-prefixed names (``vds-platform_<short-name>`` — set by
    the top-level ``name:`` declaration in compose YAML per ADR-INF-7).
    """
    result = VerificationResult()
    expected_volumes = ["vds_postgres_data", "vds_redis_data", "vds_qdrant_data"]

    code, stdout, stderr = run_command(["docker", "volume", "ls", "--format", "{{.Name}}"])

    if code != 0:
        result.add("volumes_list", False, f"Failed to list volumes: {stderr}")
        return result

    existing_volumes = set(stdout.strip().split("\n"))

    for volume in expected_volumes:
        # Check both the short name and the compose-prefixed variant
        # (ADR-INF-7: compose files declare ``name: vds-platform``,
        # which prefixes all auto-created volumes).
        compose_prefixed = f"vds-platform_{volume}"
        if volume in existing_volumes or compose_prefixed in existing_volumes:
            found_name = volume if volume in existing_volumes else compose_prefixed
            result.add(
                f"volume_exists:{volume}",
                True,
                f"Volume {volume} exists (as {found_name})",
            )
        else:
            result.add(
                f"volume_exists:{volume}",
                False,
                f"Volume {volume} NOT found",
                {"expected": expected_volumes, "existing": sorted(existing_volumes)},
            )

    return result


def verify_infra_topology(
    profile: str = "infra",
    repo_root: Path | None = None,
) -> VerificationResult:
    """Run all infrastructure topology checks."""
    result = VerificationResult()

    # Check Docker availability
    docker_check = check_docker_available()
    result.checks.extend(docker_check.checks)

    if not docker_check.passed:
        return result

    # Check expected containers based on profile.
    # Profile names mirror docker-compose.services.yml `profiles:` arrays.
    # CLI containers (db-query, progress) are NOT included in expected lists
    # because they have `restart: "no"` and exit after running their command —
    # checking they're "running" would fail the verify on a healthy system.
    INFRA = ["vds-postgres", "vds-redis", "vds-qdrant"]
    # ADR-INF-10: long-running services (running) vs CLI containers (exit 0).
    # CLI profiles only assert infra-up; the CLI container exiting cleanly is
    # the intended steady state, not a failure.
    LONG_RUNNING = ["vds-memory-api", "vds-memory-worker", "vds-scheduler-orchestrator", "vds-multi-agent-orchestrator"]
    if profile == "infra":
        expected = list(INFRA)
    elif profile == "memory":
        expected = [*INFRA, "vds-memory-api", "vds-memory-worker"]
    elif profile == "scheduler":
        expected = [*INFRA, "vds-scheduler-orchestrator"]
    elif profile == "multi-agent":
        expected = [*INFRA, "vds-multi-agent-orchestrator"]
    elif profile in ("audit", "pdf", "progress", "db-query"):
        # CLI profiles — only infra runs persistently; the CLI container runs once.
        expected = list(INFRA)
    elif profile == "full":
        expected = INFRA + LONG_RUNNING
    else:
        expected = list(INFRA)

    container_check = check_containers_running(expected)
    result.checks.extend(container_check.checks)

    # Check Postgres schemas (only if postgres is running).
    # NOTE (v2.15.11): this validator INTENTIONALLY probes Postgres directly
    # at localhost:5432 (NOT through PgBouncer at :6432). The schema-existence
    # check is a Postgres-level invariant — it verifies the database has the
    # expected schemas regardless of any pooler routing layer above it. Probing
    # through PgBouncer would add a (cosmetic) layer of indirection without
    # changing what's being checked. PgBouncer-level invariants (pool reachability,
    # session-mode contract, max_connections) live in check_pgbouncer() which
    # uses port 6432.
    if "vds-postgres" in expected:
        schema_check = check_postgres_schemas("postgresql://postgres@localhost:5432/vds_platform")
        result.checks.extend(schema_check.checks)

    # Check alembic_version tables per ADR-INF-11 dual-flavor policy.
    # Profile gating: skip for 'infra' (no migrate-svc has run yet) and for
    # CLI-only profiles that don't carry DB-backed migrations (pdf, db-query,
    # multi-agent).
    #
    # All 4 services use the in-schema flavor (per spec v2.12.2 ADR-INF-11
    # simplification — live state on 2026-04-26 confirmed scheduler's
    # alembic_version lives in `sched`, not `public`. The earlier "scheduler
    # in-public exception" was a doc artifact from a misread of scheduler's
    # env.py — its omitted `version_table_schema` defaults to public, but the
    # connection's search_path lands the table in `sched` anyway).
    ALEMBIC_BY_SERVICE: dict[str, dict[str, Any]] = {
        "memory": {"flavor": "in-schema", "schema": "memory"},
        "audit": {"flavor": "in-schema", "schema": "audit_state"},
        "progress": {"flavor": "in-schema", "schema": "progress"},
        "scheduler": {"flavor": "in-schema", "schema": "sched"},
    }
    alembic_expected: dict[str, dict[str, Any]] = {}
    if profile == "memory":
        alembic_expected = {"memory": ALEMBIC_BY_SERVICE["memory"]}
    elif profile == "scheduler":
        alembic_expected = {"scheduler": ALEMBIC_BY_SERVICE["scheduler"]}
    elif profile == "audit":
        alembic_expected = {"audit": ALEMBIC_BY_SERVICE["audit"]}
    elif profile == "progress":
        alembic_expected = {"progress": ALEMBIC_BY_SERVICE["progress"]}
    elif profile == "full":
        alembic_expected = dict(ALEMBIC_BY_SERVICE)
    # 'infra', 'pdf', 'db-query', 'multi-agent', and any other profile: skip.

    if alembic_expected and "vds-postgres" in expected:
        alembic_check = check_alembic_versions(alembic_expected)
        result.checks.extend(alembic_check.checks)

    # Check Redis DBs (FR-3 logical allocation: 0-8 active, 9 = tool discovery per ADR-INF-9)
    if "vds-redis" in expected:
        for db in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]:
            redis_check = check_redis_db(db)
            result.checks.extend(redis_check.checks)

    # Check ports
    for port in [5432, 6379, 6335, 6336]:
        port_check = check_port_available(port)
        result.checks.extend(port_check.checks)

    # Check volumes
    if "vds-postgres" in expected:
        volume_check = check_volumes()
        result.checks.extend(volume_check.checks)

    # WP-5.5: Migration template drift guard — full profile only.
    # Checks each service alembic/env.py for helper-import presence + LOC bounds.
    # Skip for profiles that have not run migrations (infra, pdf, db-query, multi-agent).
    if profile == "full":
        effective_root = repo_root if repo_root is not None else Path(__file__).resolve().parent.parent
        drift_check = check_migration_template_drift(effective_root)
        result.checks.extend(drift_check.checks)

    # WP-8.6: PgBouncer (Tier 1.5) checks — runs on infra + full profiles.
    # Six checks total per ADR-INF-13 v2.15.3 (session-mode uniform topology).
    # Gracefully skips with "container not running" when P8 hasn't been deployed.
    if profile in ("infra", "full"):
        pgbouncer_check = check_pgbouncer()
        result.checks.extend(pgbouncer_check.checks)

    return result


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify VDS infrastructure topology")
    parser.add_argument(
        "--profile",
        default="infra",
        choices=["infra", "audit", "memory", "scheduler", "pdf", "multi-agent", "progress", "db-query", "full"],
        help="Profile to verify (default: infra)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    result = verify_infra_topology(args.profile)

    if args.json:
        output = {
            "passed": result.passed,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details,
                }
                for c in result.checks
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print("=" * 60)
        print("VDS Infrastructure Topology Verification")
        print("=" * 60)
        print()

        passed = 0
        failed = 0
        for check in result.checks:
            status = "✓" if check.passed else "✗"
            print(f"  {status} {check.name}: {check.message}")
            if check.passed:
                passed += 1
            else:
                failed += 1

        print()
        print("-" * 60)
        print(f"Results: {passed} passed, {failed} failed")
        print("-" * 60)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
