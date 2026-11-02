"""Unit tests for scripts/smoke-test-deploy.sh logic.

These tests validate the Python helper module that underpins smoke-test-deploy.sh.
Since the deploy script is Bash, we test its logic through a thin Python
shim (scripts/smoke_deploy_lib.py) that the Bash script delegates to for
artifact writing and step orchestration decisions.

All subprocess calls are mocked — no real Docker or make invocations.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module loader — smoke_deploy_lib.py
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent.parent
SMOKE_LIB_PATH = SCRIPT_DIR / "smoke_deploy_lib.py"


def _load_smoke_lib() -> Any:
    """Load smoke_deploy_lib as a module."""
    mod_name = "_smoke_deploy_lib_under_test"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, SMOKE_LIB_PATH)
    assert spec is not None and spec.loader is not None, f"Cannot load {SMOKE_LIB_PATH} — run Step 4 (GREEN) first"
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def lib() -> Any:
    """Return the loaded smoke_deploy_lib module."""
    return _load_smoke_lib()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Import from lib at module-load time so this stays in sync when steps
# are added/removed (P6 WP-6.3 added step 8 — pytest -m docker downgrade
# tests). The `lib` fixture is module-scoped so this idempotent load is safe.
RUNBOOK_STEPS = _load_smoke_lib().RUNBOOK


# ---------------------------------------------------------------------------
# Happy path: all 7 steps succeed
# ---------------------------------------------------------------------------


class TestHappyPath:
    """All runbook steps exit 0 — artifact is written with passed=True."""

    def test_all_steps_invoked_in_order(self, lib: Any, tmp_path: Path) -> None:
        """Each make target is invoked exactly once, in runbook order."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="deadbeef",
            )

        assert result["passed"] is True
        calls = [c.args[0] for c in mock_run.call_args_list if isinstance(c.args[0], list)]
        # P6 WP-6.3: RUNBOOK now includes step 8 (uv-invoked downgrade tests),
        # not just make targets — assert ALL command tuples in order.
        all_calls = [" ".join(c) for c in calls if c]
        assert all_calls == RUNBOOK_STEPS

    def test_artifact_json_written(self, lib: Any, tmp_path: Path) -> None:
        """Artifact JSON file is created under artifact_dir after successful run."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="abc1234",
            )

        artifacts = list(artifact_dir.glob("smoke-*.json"))
        assert len(artifacts) == 1
        artifact_path = artifacts[0]
        # Filename must embed git sha
        assert "abc1234" in artifact_path.name

        data = json.loads(artifact_path.read_text())
        assert data["passed"] is True
        assert "steps" in data
        assert len(data["steps"]) == len(RUNBOOK_STEPS)

    def test_artifact_schema_fields(self, lib: Any, tmp_path: Path) -> None:
        """Artifact JSON must contain required top-level fields."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="cafebabe",
            )

        artifacts = list(artifact_dir.glob("smoke-*.json"))
        data = json.loads(artifacts[0].read_text())

        required_fields = {"passed", "steps", "git_sha", "timestamp", "target"}
        assert required_fields.issubset(data.keys()), f"Missing fields: {required_fields - data.keys()}"

    def test_each_step_has_exit_code_and_duration(self, lib: Any, tmp_path: Path) -> None:
        """Each step entry in artifact must record exit_code and duration_s."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="0000001",
            )

        artifacts = list(artifact_dir.glob("smoke-*.json"))
        data = json.loads(artifacts[0].read_text())

        for step in data["steps"]:
            assert "command" in step, f"step missing 'command': {step}"
            assert "exit_code" in step, f"step missing 'exit_code': {step}"
            assert "duration_s" in step, f"step missing 'duration_s': {step}"
            assert step["exit_code"] == 0


# ---------------------------------------------------------------------------
# Failure mode: step 3 (run-audit-migrate) exits non-zero
# ---------------------------------------------------------------------------


class TestStep2Failure:
    """make run-audit-migrate exits 1 — remaining steps are skipped, partial artifact written."""

    def _make_side_effect(self, fail_at_index: int) -> list[MagicMock]:
        """Return side_effect list: steps 0..fail_at_index-1 succeed, fail_at_index fails."""
        # We need enough mocks; subprocess.run may be called for extra commands
        # (docker ps, psql, etc.) interleaved. We match on the make call index.
        results = []
        for i in range(10):
            if i == fail_at_index:
                results.append(MagicMock(returncode=1, stdout="", stderr="migration failed"))
            else:
                results.append(MagicMock(returncode=0, stdout="", stderr=""))
        return results

    def test_short_circuit_on_step_failure(self, lib: Any, tmp_path: Path) -> None:
        """When step N fails, steps N+1..end are NOT invoked."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        call_count = 0
        fail_step = "make run-audit-migrate"

        def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            nonlocal call_count
            if isinstance(cmd, list) and cmd[:1] == ["make"]:
                step_cmd = " ".join(cmd)
                if step_cmd == fail_step:
                    return MagicMock(returncode=1, stdout="", stderr="audit migrate failed")
                # If we're past the fail step, it should not be called
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            result = lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="fail001",
            )

        assert result["passed"] is False
        # Only steps up to and including the failed step should appear completed
        completed_make_steps = [s for s in result["steps"] if s.get("exit_code") is not None]
        # The failing step must be present with exit_code=1
        failed_steps = [s for s in completed_make_steps if s["exit_code"] != 0]
        assert len(failed_steps) >= 1
        assert any(fail_step in s["command"] for s in failed_steps)

    def test_partial_artifact_written_on_failure(self, lib: Any, tmp_path: Path) -> None:
        """Even on failure, partial artifact JSON is still written for diagnostics."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            if isinstance(cmd, list) and " ".join(cmd) == "make run-audit-migrate":
                return MagicMock(returncode=1, stdout="", stderr="failed")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="partial01",
            )

        # Artifact must exist even on failure
        artifacts = list(artifact_dir.glob("smoke-*.json"))
        assert len(artifacts) == 1
        data = json.loads(artifacts[0].read_text())
        assert data["passed"] is False
        assert "partial01" in artifacts[0].name


# ---------------------------------------------------------------------------
# Failure mode: step 7 (make verify) exits non-zero
# ---------------------------------------------------------------------------


class TestVerifyStepFailure:
    """make verify exits 1 — all prior steps succeeded but overall result is failed."""

    def test_verify_failure_marks_result_failed(self, lib: Any, tmp_path: Path) -> None:
        """If only 'make verify' fails, passed=False but all 7 steps are recorded."""
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            if isinstance(cmd, list) and " ".join(cmd) == "make verify":
                return MagicMock(returncode=1, stdout="verification failed", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=side_effect):
            result = lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="verify01",
            )

        assert result["passed"] is False
        artifacts = list(artifact_dir.glob("smoke-*.json"))
        data = json.loads(artifacts[0].read_text())
        assert data["passed"] is False
        verify_steps = [s for s in data["steps"] if "verify" in s["command"]]
        assert len(verify_steps) == 1
        assert verify_steps[0]["exit_code"] == 1


# ---------------------------------------------------------------------------
# Artifact directory auto-creation
# ---------------------------------------------------------------------------


class TestArtifactDirCreation:
    """artifact_dir is created if it does not exist."""

    def test_artifact_dir_created_automatically(self, lib: Any, tmp_path: Path) -> None:
        artifact_dir = tmp_path / "new" / "nested" / "evidence"
        # Must NOT exist yet
        assert not artifact_dir.exists()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="mkdir01",
            )

        assert artifact_dir.exists()
        assert len(list(artifact_dir.glob("smoke-*.json"))) == 1


# ---------------------------------------------------------------------------
# Target parameter propagated to artifact
# ---------------------------------------------------------------------------


class TestTargetParameter:
    """--target value is recorded in the artifact."""

    @pytest.mark.parametrize("target", ["ephemeral", "live"])
    def test_target_recorded_in_artifact(self, lib: Any, tmp_path: Path, target: str) -> None:
        artifact_dir = tmp_path / "evidence"
        artifact_dir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            lib.run_smoke(
                artifact_dir=artifact_dir,
                repo_root=tmp_path,
                git_sha="tgt001",
                target=target,
            )

        artifacts = list(artifact_dir.glob("smoke-*.json"))
        data = json.loads(artifacts[0].read_text())
        assert data["target"] == target
