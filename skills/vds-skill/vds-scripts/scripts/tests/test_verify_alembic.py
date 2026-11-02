"""Tests for ``check_alembic_versions()`` in ``scripts/verify-infra-topology.py``.

Covers ADR-INF-11 §Dual ``version_table_schema`` Policy, with strict mocking
per VDS Testing Rules — no real Postgres / Docker calls.

The verify-infra-topology script is named with a hyphen, so we load it via
``importlib.util.spec_from_file_location`` rather than ``import``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module loader — verify-infra-topology.py has a hyphen, so we cannot use
# ``import scripts.verify_infra_topology``. Load by file path once per session.
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "verify-infra-topology.py"


def _load_verify_module() -> Any:
    """Load verify-infra-topology.py as a module (cached via sys.modules)."""
    mod_name = "_verify_infra_topology_under_test"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verify() -> Any:
    """Return the loaded verify-infra-topology module."""
    return _load_verify_module()


# Known scheduler rev-history per ADR-INF-11 (matches the list embedded in
# verify_infra_topology() profile dispatch).
SCHEDULER_EXPECTED_REVS = [
    "0001_create_sched_schema",
    "20260424_04f7169497f6",
    "20260424_a1b2c3d4e5f6",
    "20260424_b2c3d4e5f6a7",
    "20260424_c3d4e5f6a7b8",
    "20260424_d4e5f6a7b8c9",
    "20260424_e5f6a7b8c9d0",
]


# ---------------------------------------------------------------------------
# In-schema flavor
# ---------------------------------------------------------------------------


class TestInSchemaFlavor:
    """ADR-INF-11 in-schema flavor — ``<schema>.alembic_version`` table."""

    def test_table_exists_with_row_passes(self, verify: Any) -> None:
        """Table exists and has a version row -> passed=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc123def456\n",
                stderr="",
            )
            expected = {"memory": {"flavor": "in-schema", "schema": "memory"}}
            result = verify.check_alembic_versions(expected)

        assert result.passed is True
        assert len(result.checks) == 1
        check = result.checks[0]
        assert check.name == "alembic_version_present:memory"
        assert check.passed is True
        assert "memory.alembic_version" in check.message
        assert check.details["version_num"] == "abc123def456"

    def test_table_missing_fails(self, verify: Any) -> None:
        """psql returns non-zero (relation does not exist) -> passed=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr=('ERROR:  relation "audit_state.alembic_version" does not exist\n'),
            )
            expected = {"audit": {"flavor": "in-schema", "schema": "audit_state"}}
            result = verify.check_alembic_versions(expected)

        assert result.passed is False
        check = result.checks[0]
        assert check.name == "alembic_version_present:audit"
        assert check.passed is False
        assert "missing" in check.message
        assert "audit_state" in check.message

    def test_table_exists_but_empty_fails(self, verify: Any) -> None:
        """psql returns 0 rows (table exists but no version row) -> passed=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="\n",  # empty result
                stderr="",
            )
            expected = {"progress": {"flavor": "in-schema", "schema": "progress"}}
            result = verify.check_alembic_versions(expected)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "no version row" in check.message


# ---------------------------------------------------------------------------
# In-public flavor (scheduler)
# ---------------------------------------------------------------------------


class TestInPublicFlavor:
    """ADR-INF-11 in-public flavor — ``public.alembic_version`` + rev-history match."""

    def test_version_num_in_expected_revs_passes(self, verify: Any) -> None:
        """version_num matches a known scheduler revision -> passed=True."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="20260424_e5f6a7b8c9d0\n",
                stderr="",
            )
            expected = {
                "scheduler": {
                    "flavor": "in-public",
                    "expected_revs": SCHEDULER_EXPECTED_REVS,
                },
            }
            result = verify.check_alembic_versions(expected)

        assert result.passed is True
        check = result.checks[0]
        assert check.name == "alembic_version_present:scheduler"
        assert check.passed is True
        assert "rev-history match" in check.message
        assert check.details["version_num"] == "20260424_e5f6a7b8c9d0"

    def test_version_num_not_in_expected_revs_fails(self, verify: Any) -> None:
        """version_num does NOT match any expected scheduler rev -> passed=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="some_unknown_revision_xyz\n",
                stderr="",
            )
            expected = {
                "scheduler": {
                    "flavor": "in-public",
                    "expected_revs": SCHEDULER_EXPECTED_REVS,
                },
            }
            result = verify.check_alembic_versions(expected)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "unexpected revision" in check.message
        assert check.details["found"] == ["some_unknown_revision_xyz"]

    def test_table_missing_fails(self, verify: Any) -> None:
        """public.alembic_version missing entirely -> passed=False."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr='ERROR:  relation "public.alembic_version" does not exist\n',
            )
            expected = {
                "scheduler": {
                    "flavor": "in-public",
                    "expected_revs": SCHEDULER_EXPECTED_REVS,
                },
            }
            result = verify.check_alembic_versions(expected)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "missing" in check.message

    def test_multiple_rows_one_matches_passes(self, verify: Any) -> None:
        """If public.alembic_version has multiple rows and at least one matches,
        the rev-history disambiguation succeeds (per ADR-INF-11).
        """
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="some_other_service_rev\n0001_create_sched_schema\n",
                stderr="",
            )
            expected = {
                "scheduler": {
                    "flavor": "in-public",
                    "expected_revs": SCHEDULER_EXPECTED_REVS,
                },
            }
            result = verify.check_alembic_versions(expected)

        assert result.passed is True
        check = result.checks[0]
        assert check.passed is True
        assert check.details["version_num"] == "0001_create_sched_schema"


# ---------------------------------------------------------------------------
# Multi-service dispatch
# ---------------------------------------------------------------------------


class TestMultiService:
    """check_alembic_versions() with all 4 services produces 4 CheckResults."""

    def test_four_services_produce_four_results(self, verify: Any) -> None:
        with patch("subprocess.run") as mock_run:
            # All four queries return a healthy version row. Use the scheduler
            # rev for the in-public query so it satisfies rev-history match.
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="memory_rev_a\n", stderr=""),
                MagicMock(returncode=0, stdout="audit_rev_b\n", stderr=""),
                MagicMock(returncode=0, stdout="progress_rev_c\n", stderr=""),
                MagicMock(
                    returncode=0,
                    stdout="0001_create_sched_schema\n",
                    stderr="",
                ),
            ]
            expected = {
                "memory": {"flavor": "in-schema", "schema": "memory"},
                "audit": {"flavor": "in-schema", "schema": "audit_state"},
                "progress": {"flavor": "in-schema", "schema": "progress"},
                "scheduler": {
                    "flavor": "in-public",
                    "expected_revs": SCHEDULER_EXPECTED_REVS,
                },
            }
            result = verify.check_alembic_versions(expected)

        assert len(result.checks) == 4
        names = {c.name for c in result.checks}
        assert names == {
            "alembic_version_present:memory",
            "alembic_version_present:audit",
            "alembic_version_present:progress",
            "alembic_version_present:scheduler",
        }
        assert result.passed is True


# ---------------------------------------------------------------------------
# Profile gating in verify_infra_topology()
# ---------------------------------------------------------------------------


class TestProfileGating:
    """verify_infra_topology() should call check_alembic_versions only on the
    correct profiles per WP-4.6 mapping.
    """

    @staticmethod
    def _stub_subprocess() -> MagicMock:
        """Return a MagicMock that returns a healthy default for every call.

        Order-independent; we don't care about exact return values, only that
        the script doesn't crash before it reaches check_alembic_versions().
        """

        def _fake_run(cmd: list[str], **_kwargs: Any) -> MagicMock:
            # docker info -> ok; docker ps -> all 4 long-running services up
            if cmd[:2] == ["docker", "info"]:
                return MagicMock(returncode=0, stdout="Docker", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return MagicMock(
                    returncode=0,
                    stdout=(
                        "vds-postgres\nvds-redis\nvds-qdrant\n"
                        "vds-memory-api\nvds-memory-worker\n"
                        "vds-scheduler-orchestrator\n"
                        "vds-multi-agent-orchestrator\n"
                    ),
                    stderr="",
                )
            if cmd[:3] == ["docker", "volume", "ls"]:
                return MagicMock(
                    returncode=0,
                    stdout="vds_postgres_data\nvds_redis_data\nvds_qdrant_data\n",
                    stderr="",
                )
            # docker exec ... psql ... \dn
            if "psql" in cmd and "\\dn" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="audit_state\nmemory\nsched\nprogress\ndbos\n",
                    stderr="",
                )
            # docker exec ... psql ... alembic_version queries — return a value
            # that satisfies both in-schema and in-public (scheduler rev).
            if "psql" in cmd and any("alembic_version" in c for c in cmd):
                return MagicMock(
                    returncode=0,
                    stdout="0001_create_sched_schema\n",
                    stderr="",
                )
            # redis-cli ping
            if "redis-cli" in cmd:
                return MagicMock(returncode=0, stdout="PONG\n", stderr="")
            # Everything else (port checks etc.)
            return MagicMock(returncode=0, stdout="", stderr="")

        m = MagicMock(side_effect=_fake_run)
        return m

    def test_infra_profile_does_not_call_alembic_check(self, verify: Any) -> None:
        """Profile 'infra' must NOT emit any alembic_version_present checks."""
        with patch("subprocess.run", new=self._stub_subprocess()):
            with patch.object(verify, "check_alembic_versions", wraps=verify.check_alembic_versions) as spy:
                result = verify.verify_infra_topology(profile="infra")

        assert spy.call_count == 0
        alembic_checks = [c for c in result.checks if c.name.startswith("alembic_version_present:")]
        assert alembic_checks == []

    def test_full_profile_calls_alembic_check_for_all_four(self, verify: Any) -> None:
        """Profile 'full' must check all 4 services."""
        with patch("subprocess.run", new=self._stub_subprocess()):
            with patch.object(verify, "check_alembic_versions", wraps=verify.check_alembic_versions) as spy:
                result = verify.verify_infra_topology(profile="full")

        assert spy.call_count == 1
        # Exactly the 4 service keys per ADR-INF-11.
        call_arg = spy.call_args[0][0]
        assert set(call_arg.keys()) == {"memory", "audit", "progress", "scheduler"}

        alembic_checks = [c for c in result.checks if c.name.startswith("alembic_version_present:")]
        assert len(alembic_checks) == 4
        assert {c.name for c in alembic_checks} == {
            "alembic_version_present:memory",
            "alembic_version_present:audit",
            "alembic_version_present:progress",
            "alembic_version_present:scheduler",
        }

    @pytest.mark.parametrize(
        "profile,expected_service",
        [
            ("memory", "memory"),
            ("scheduler", "scheduler"),
            ("audit", "audit"),
            ("progress", "progress"),
        ],
    )
    def test_single_service_profiles(self, verify: Any, profile: str, expected_service: str) -> None:
        """Each single-service profile checks exactly its own service."""
        with patch("subprocess.run", new=self._stub_subprocess()):
            result = verify.verify_infra_topology(profile=profile)

        alembic_checks = [c for c in result.checks if c.name.startswith("alembic_version_present:")]
        assert len(alembic_checks) == 1
        assert alembic_checks[0].name == f"alembic_version_present:{expected_service}"

    @pytest.mark.parametrize("profile", ["pdf", "db-query", "multi-agent"])
    def test_cli_profiles_skip_alembic_check(self, verify: Any, profile: str) -> None:
        """CLI/non-DB profiles must not trigger an alembic check."""
        with patch("subprocess.run", new=self._stub_subprocess()):
            result = verify.verify_infra_topology(profile=profile)

        alembic_checks = [c for c in result.checks if c.name.startswith("alembic_version_present:")]
        assert alembic_checks == []


# ---------------------------------------------------------------------------
# check_migration_template_drift() — WP-5.5
# ---------------------------------------------------------------------------


class TestCheckMigrationTemplateDrift:
    """check_migration_template_drift() asserts each service alembic/env.py:
    - imports from vds_platform_core.alembic
    - is between 20 and 60 LOC (post-WP-5.2 target)

    All filesystem reads are done against tmp_path synthetic files;
    no real repo access.
    """

    SERVICES = [
        "memory_orchestrator",
        "audit_orchestrator",
        "progress_report_orchestrator",
        "scheduler_orchestrator",
    ]

    def _write_env_py(
        self,
        root: Path,
        service: str,
        *,
        has_import: bool = True,
        loc: int = 30,
    ) -> None:
        """Create a synthetic env.py for the given service."""
        svc_dir = root / service / "alembic"
        svc_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        if has_import:
            lines.append("from vds_platform_core.alembic import run_migrations_online")
        else:
            lines.append("# no helper import — inline boilerplate follows")
        # Pad to target LOC
        while len(lines) < loc:
            lines.append("# filler line")
        (svc_dir / "env.py").write_text("\n".join(lines) + "\n")

    def test_all_four_services_pass_when_compliant(self, verify: Any, tmp_path: Path) -> None:
        """All 4 services with helper import + 30 LOC -> single passing result."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is True
        assert len(result.checks) == 1
        check = result.checks[0]
        assert check.name == "migration_template_drift"
        assert check.passed is True

    def test_fails_when_service_missing_helper_import(self, verify: Any, tmp_path: Path) -> None:
        """A service without vds_platform_core.alembic import -> result fails."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)
        # Override audit_orchestrator to lack the import
        self._write_env_py(tmp_path, "audit_orchestrator", has_import=False, loc=30)

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "audit_orchestrator" in check.message
        assert "import" in check.message.lower()

    def test_fails_when_service_env_py_too_large(self, verify: Any, tmp_path: Path) -> None:
        """An env.py with 170 LOC (inline boilerplate pre-WP-5.2) -> result fails."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)
        # Override progress_report_orchestrator to have bloated env.py
        self._write_env_py(tmp_path, "progress_report_orchestrator", has_import=True, loc=170)

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "progress_report_orchestrator" in check.message
        assert "LOC" in check.message or "loc" in check.message.lower() or "line" in check.message.lower()

    def test_fails_when_env_py_missing_entirely(self, verify: Any, tmp_path: Path) -> None:
        """If a service's alembic/env.py does not exist at all -> result fails."""
        # Write only 3 services
        for svc in self.SERVICES[:3]:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)
        # scheduler_orchestrator env.py absent

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "scheduler_orchestrator" in check.message

    def test_fails_when_env_py_too_small(self, verify: Any, tmp_path: Path) -> None:
        """An env.py with < 20 LOC is suspiciously truncated -> result fails."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)
        # Override memory_orchestrator to be a stub (5 LOC)
        self._write_env_py(tmp_path, "memory_orchestrator", has_import=True, loc=5)

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is False
        check = result.checks[0]
        assert check.passed is False
        assert "memory_orchestrator" in check.message

    def test_returns_verification_result_type(self, verify: Any, tmp_path: Path) -> None:
        """Return type must be VerificationResult (has .passed + .checks)."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)

        result = verify.check_migration_template_drift(tmp_path)

        assert hasattr(result, "passed")
        assert hasattr(result, "checks")
        assert isinstance(result.checks, list)

    def test_details_contain_per_service_info(self, verify: Any, tmp_path: Path) -> None:
        """On failure, details dict includes per-service diagnostics."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)
        # One service is bad
        self._write_env_py(tmp_path, "scheduler_orchestrator", has_import=False, loc=30)

        result = verify.check_migration_template_drift(tmp_path)

        assert result.passed is False
        check = result.checks[0]
        # details must contain some structured info about the failing service
        assert isinstance(check.details, dict)
        assert len(check.details) > 0

    def test_full_profile_dispatch_includes_drift_check(self, verify: Any, tmp_path: Path) -> None:
        """verify_infra_topology(profile='full') calls check_migration_template_drift."""
        for svc in self.SERVICES:
            self._write_env_py(tmp_path, svc, has_import=True, loc=30)

        def _stub_subprocess(cmd: list[str], **kwargs: Any) -> MagicMock:
            if cmd[:2] == ["docker", "info"]:
                return MagicMock(returncode=0, stdout="Docker", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return MagicMock(
                    returncode=0,
                    stdout=(
                        "vds-postgres\nvds-redis\nvds-qdrant\n"
                        "vds-memory-api\nvds-memory-worker\n"
                        "vds-scheduler-orchestrator\n"
                        "vds-multi-agent-orchestrator\n"
                    ),
                    stderr="",
                )
            if cmd[:3] == ["docker", "volume", "ls"]:
                return MagicMock(returncode=0, stdout="vds_postgres_data\nvds_redis_data\nvds_qdrant_data\n", stderr="")
            if "psql" in cmd and "\\dn" in cmd:
                return MagicMock(returncode=0, stdout="audit_state\nmemory\nsched\nprogress\ndbos\n", stderr="")
            if "psql" in cmd and any("alembic_version" in c for c in cmd):
                return MagicMock(returncode=0, stdout="0001_create_sched_schema\n", stderr="")
            if "redis-cli" in cmd:
                return MagicMock(returncode=0, stdout="PONG\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=_stub_subprocess):
            with patch.object(
                verify, "check_migration_template_drift", wraps=verify.check_migration_template_drift
            ) as spy:
                result = verify.verify_infra_topology(profile="full", repo_root=tmp_path)

        assert spy.call_count == 1
        drift_checks = [c for c in result.checks if c.name == "migration_template_drift"]
        assert len(drift_checks) == 1

    def test_infra_profile_does_not_call_drift_check(self, verify: Any, tmp_path: Path) -> None:
        """Profile 'infra' must NOT run drift check (no migrations run yet)."""

        def _stub_subprocess(cmd: list[str], **kwargs: Any) -> MagicMock:
            if cmd[:2] == ["docker", "info"]:
                return MagicMock(returncode=0, stdout="Docker", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return MagicMock(returncode=0, stdout="vds-postgres\nvds-redis\nvds-qdrant\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=_stub_subprocess):
            with patch.object(
                verify, "check_migration_template_drift", wraps=verify.check_migration_template_drift
            ) as spy:
                result = verify.verify_infra_topology(profile="infra", repo_root=tmp_path)

        assert spy.call_count == 0
        drift_checks = [c for c in result.checks if c.name == "migration_template_drift"]
        assert drift_checks == []
