"""Tests for ``verify-infra-topology.py``.

The verify-infra-topology script's filename uses a hyphen
(``verify-infra-topology.py``), which is not a valid Python module name.
Python cannot resolve ``import scripts.verify_infra_topology`` against a
hyphenated file, so we load the script via
``importlib.util.spec_from_file_location`` — mirroring the canonical pattern
established by ``test_verify_alembic.py`` (added in P4 commit 212b49a9).

Hyphenated filename is the public CLI contract per ADR-INF-8 in
``docker/ADR.md`` and is referenced from the Makefile, operator runbooks,
and the sibling ``infrastructure-evolution-skill``. Renaming would have
cross-repo blast radius; loading via importlib keeps the test suite
self-contained.
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


class TestVerifyInfraTopology:
    """Test suite for infrastructure topology verification."""

    def test_check_docker_available_success(self, verify: Any) -> None:
        """Test Docker availability check when Docker is running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Docker version 24.0.0",
                stderr="",
            )

            result = verify.check_docker_available()

            assert result.passed is True
            assert "Docker is available" in result.checks[0].message

    def test_check_docker_available_failure(self, verify: Any) -> None:
        """Test Docker availability check when Docker is not running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Cannot connect to Docker daemon",
            )

            result = verify.check_docker_available()

            assert result.passed is False
            assert "not available" in result.checks[0].message

    def test_check_containers_running_all_present(self, verify: Any) -> None:
        """Test container check when all expected containers are running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="vds-postgres\nvds-redis\nvds-qdrant\n",
                stderr="",
            )

            result = verify.check_containers_running(["vds-postgres", "vds-redis", "vds-qdrant"])

            assert result.passed is True
            assert len(result.checks) == 3
            for check in result.checks:
                assert check.passed is True

    def test_check_containers_running_some_missing(self, verify: Any) -> None:
        """Test container check when some containers are missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="vds-postgres\n",  # Only postgres is running
                stderr="",
            )

            result = verify.check_containers_running(["vds-postgres", "vds-redis", "vds-qdrant"])

            assert result.passed is False
            assert any(not c.passed for c in result.checks if "redis" in c.name)

    def test_check_postgres_schemas_all_exist(self, verify: Any) -> None:
        """Test Postgres schema check when all schemas exist."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="audit_state\nmemory\nsched\nprogress\ndbos\n",
                stderr="",
            )

            result = verify.check_postgres_schemas("postgresql://postgres@localhost:5432/vds_platform")

            assert result.passed is True
            assert len(result.checks) == 5

    def test_check_postgres_schemas_missing(self, verify: Any) -> None:
        """Test Postgres schema check when schemas are missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="audit_state\nmemory\n",  # Missing sched, progress, dbos
                stderr="",
            )

            result = verify.check_postgres_schemas("postgresql://postgres@localhost:5432/vds_platform")

            assert result.passed is False
            assert any(not c.passed for c in result.checks if "sched" in c.name)

    def test_check_redis_db_success(self, verify: Any) -> None:
        """Test Redis DB check when DB is reachable."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="PONG\n",
                stderr="",
            )

            result = verify.check_redis_db(0)

            assert result.passed is True
            assert "reachable" in result.checks[0].message

    def test_check_redis_db_failure(self, verify: Any) -> None:
        """Test Redis DB check when DB is not reachable."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Connection refused",
            )

            result = verify.check_redis_db(99)

            assert result.passed is False
            assert "NOT reachable" in result.checks[0].message

    def test_check_volumes_all_exist(self, verify: Any) -> None:
        """Test volume check when all expected volumes exist."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="vds_postgres_data\nvds_redis_data\nvds_qdrant_data\n",
                stderr="",
            )

            result = verify.check_volumes()

            assert result.passed is True
            assert len(result.checks) == 3

    def test_verify_infra_topology_infra_profile(self, verify: Any) -> None:
        """Test full topology verification with infra profile.

        Uses a callable ``side_effect`` to dispatch on command shape — mirrors
        the pattern in ``test_verify_alembic.py::_stub_subprocess``. A bare
        list-based ``side_effect`` is brittle here because the function makes
        a variable number of subprocess calls (10 Redis DBs, 4 ports, etc.)
        depending on profile.
        """

        def fake_run(cmd: list[str], **_kwargs: Any) -> MagicMock:
            if cmd[:2] == ["docker", "info"]:
                return MagicMock(returncode=0, stdout="Docker running", stderr="")
            if cmd[:2] == ["docker", "ps"]:
                return MagicMock(
                    returncode=0,
                    stdout="vds-postgres\nvds-redis\nvds-qdrant\n",
                    stderr="",
                )
            if cmd[:3] == ["docker", "volume", "ls"]:
                return MagicMock(
                    returncode=0,
                    stdout="vds_postgres_data\nvds_redis_data\nvds_qdrant_data\n",
                    stderr="",
                )
            if "psql" in cmd and "\\dn" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout="audit_state\nmemory\nsched\nprogress\ndbos\n",
                    stderr="",
                )
            if "redis-cli" in cmd:
                return MagicMock(returncode=0, stdout="PONG\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=fake_run):
            result = verify.verify_infra_topology("infra")

            # Should have multiple checks
            assert len(result.checks) > 0

    def test_verification_result_passing(self, verify: Any) -> None:
        """Test VerificationResult with all passing checks."""
        result = verify.VerificationResult()
        result.add("check1", True, "passed")
        result.add("check2", True, "passed")

        assert result.passed is True

    def test_verification_result_failing(self, verify: Any) -> None:
        """Test VerificationResult with a failing check."""
        result = verify.VerificationResult()
        result.add("check1", True, "passed")
        result.add("check2", False, "failed")

        assert result.passed is False

    def test_check_result_dataclass(self, verify: Any) -> None:
        """Test CheckResult dataclass."""
        check = verify.CheckResult(
            name="test_check",
            passed=True,
            message="Test passed",
            details={"key": "value"},
        )

        assert check.name == "test_check"
        assert check.passed is True
        assert check.message == "Test passed"
        assert check.details == {"key": "value"}
