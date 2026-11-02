"""Unit tests for vds_agent_core.skills.executor."""

from __future__ import annotations

import importlib
import subprocess
from typing import Any
from unittest.mock import patch

import pytest
from vds_agent_core.skills.executor import (
    SkillExecutor,
    SubprocessRunner,
)

# Canonical patch target for shutil.which inside the executor module.
_WHICH_TARGET = "vds_agent_core.skills.executor.shutil.which"
# A fixed absolute path returned by the which mock in happy-path tests.
_VDS_CLI_PATH = "/usr/local/bin/vds-cli"


class MockRunner:
    """Test double for CommandRunner."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.calls: list[dict[str, Any]] = []

    def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        self.calls.append({"cmd": cmd, "kwargs": kwargs})
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class TestSubprocessRunner:
    def test_instantiation(self) -> None:
        runner = SubprocessRunner()
        assert runner is not None

    def test_conforms_to_protocol(self) -> None:
        runner = SubprocessRunner()
        assert hasattr(runner, "run")
        assert callable(runner.run)


class TestCommandRunnerProtocol:
    def test_structural_conformance(self) -> None:
        """Any object with a run() method satisfies CommandRunner."""
        runner = MockRunner()
        # Protocol is structural -- just verify it has the right shape
        assert hasattr(runner, "run")
        result = runner.run(["echo", "hello"])
        assert isinstance(result, subprocess.CompletedProcess)

    def test_mock_runner_is_valid_command_runner(self) -> None:
        """MockRunner can be used wherever CommandRunner is expected."""
        mock = MockRunner(stdout="output", returncode=0)
        executor = SkillExecutor(runner=mock)
        assert executor._runner is mock


class TestSkillExecutorInit:
    def test_default_runner_is_subprocess(self) -> None:
        executor = SkillExecutor()
        assert isinstance(executor._runner, SubprocessRunner)

    def test_custom_runner_injected(self) -> None:
        mock = MockRunner()
        executor = SkillExecutor(runner=mock)
        assert executor._runner is mock

    def test_none_runner_uses_default(self) -> None:
        executor = SkillExecutor(runner=None)
        assert isinstance(executor._runner, SubprocessRunner)


class TestVdsCLIExec:
    def test_success_returns_stdout(self) -> None:
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stdout="hello world\n", returncode=0)
            executor = SkillExecutor(runner=mock)
            result = executor.vds_cli_exec(["--help"])
        assert result == "hello world\n"

    def test_failure_returns_stderr(self) -> None:
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stderr="error: unknown command\n", returncode=1)
            executor = SkillExecutor(runner=mock)
            result = executor.vds_cli_exec(["bad-cmd"])
        assert "error" in result

    def test_cmd_uses_which_resolved_path(self) -> None:
        # FR-11: command is [<abs-path>, *args], no longer ["uv", "run", "vds-cli", ...]
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stdout="ok", returncode=0)
            executor = SkillExecutor(runner=mock)
            executor.vds_cli_exec(["memory", "health"])
        assert mock.calls[0]["cmd"] == [_VDS_CLI_PATH, "memory", "health"]

    def test_records_tool_usage(self) -> None:
        SkillExecutor.reset_usage()
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stdout="ok", returncode=0)
            executor = SkillExecutor(runner=mock)
            executor.vds_cli_exec(["--version"])
        usage = SkillExecutor.consume_usage()
        assert len(usage) == 1
        assert usage[0]["tool"] == "vds_cli_exec"
        assert usage[0]["success"] is True


class TestRecordToolUsage:
    def test_record_and_consume(self) -> None:
        SkillExecutor.reset_usage()
        SkillExecutor.record_tool_usage({"tool": "test_tool", "action": "run"})
        usage = SkillExecutor.consume_usage()
        assert len(usage) == 1
        assert usage[0]["tool"] == "test_tool"

    def test_consume_clears_usage(self) -> None:
        SkillExecutor.reset_usage()
        SkillExecutor.record_tool_usage({"tool": "x"})
        SkillExecutor.consume_usage()
        assert SkillExecutor.consume_usage() == []

    def test_reset_clears_usage(self) -> None:
        SkillExecutor.record_tool_usage({"tool": "x"})
        SkillExecutor.reset_usage()
        assert SkillExecutor.consume_usage() == []


class TestVdsCLIExecException:
    def test_exception_returns_error_string(self) -> None:
        class _RaisingRunner:
            def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
                raise RuntimeError("subprocess exploded")

        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            executor = SkillExecutor(runner=_RaisingRunner())
            result = executor.vds_cli_exec(["memory", "health"])
        assert "subprocess exploded" in result

    def test_exception_records_failed_usage(self) -> None:
        SkillExecutor.reset_usage()

        class _RaisingRunner:
            def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
                raise OSError("no such file")

        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            executor = SkillExecutor(runner=_RaisingRunner())
            executor.vds_cli_exec(["--version"])
        usage = SkillExecutor.consume_usage()
        assert len(usage) == 1
        assert usage[0]["success"] is False
        assert "no such file" in usage[0]["error"]

    def test_failure_records_duration_ms(self) -> None:
        SkillExecutor.reset_usage()
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stderr="oops", returncode=1)
            executor = SkillExecutor(runner=mock)
            executor.vds_cli_exec(["bad"])
        usage = SkillExecutor.consume_usage()
        assert "duration_ms" in usage[0]
        assert isinstance(usage[0]["duration_ms"], int)

    def test_success_records_args(self) -> None:
        SkillExecutor.reset_usage()
        with patch(_WHICH_TARGET, return_value=_VDS_CLI_PATH):
            mock = MockRunner(stdout="ok", returncode=0)
            executor = SkillExecutor(runner=mock)
            executor.vds_cli_exec(["memory", "search", "foo"])
        usage = SkillExecutor.consume_usage()
        assert usage[0]["args"] == ["memory", "search", "foo"]


class TestGrepaiSearch:
    def test_success_with_path(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout='[{"file": "a.py"}]', stderr=""
            )
            SkillExecutor.reset_usage()
            result = SkillExecutor._grepai_search("auth pattern", path="/some/repo")
        assert result["success"] is True
        assert result["results"] == [{"file": "a.py"}]
        assert result["path"] == "/some/repo"

    def test_success_empty_output(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is True
        assert result["results"] == []

    def test_failure_nonzero_returncode(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="grepai error")
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is False
        assert "grepai error" in result["error"]

    def test_json_parse_error(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="not-json", stderr="")
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is False
        assert "parse" in result["error"].lower()

    def test_timeout_expired(self) -> None:
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="grepai", timeout=60)):
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is False
        assert "timed out" in result["error"]

    def test_file_not_found(self) -> None:
        with patch("subprocess.run", side_effect=FileNotFoundError("grepai not found")):
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_generic_exception(self) -> None:
        with patch("subprocess.run", side_effect=ValueError("unexpected")):
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is False
        assert "unexpected" in result["error"]

    def test_no_path_emits_deprecation_warning(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
            with pytest.warns(DeprecationWarning, match="deprecated"):
                result = SkillExecutor._grepai_search("query")
        assert "warning" in result

    def test_records_tool_usage_on_success(self) -> None:
        SkillExecutor.reset_usage()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
            SkillExecutor._grepai_search("query", path="/repo")
        usage = SkillExecutor.consume_usage()
        assert len(usage) == 1
        assert usage[0]["tool"] == "_grepai_search"
        assert usage[0]["scoped"] is True

    def test_result_dict_from_object_output(self) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout='{"results": [{"file": "b.py"}]}', stderr=""
            )
            result = SkillExecutor._grepai_search("query", path="/repo")
        assert result["success"] is True
        assert result["results"] == [{"file": "b.py"}]


# ---------------------------------------------------------------------------
# FR-11 / T-11: shutil.which-based vds-cli dispatch
# ---------------------------------------------------------------------------


class TestVdsCLIExecFR11:
    """Tests for FR-11: shutil.which-based vds-cli dispatch (spec v0.5.0)."""

    def test_vds_cli_exec_uses_shutil_which_absolute_path(self) -> None:
        """Hit branch: shutil.which returns a path -- command uses that path directly."""
        with patch(_WHICH_TARGET, return_value="/absolute/path/to/vds-cli"):
            mock = MockRunner(stdout="ok", returncode=0)
            executor = SkillExecutor(runner=mock)
            executor.vds_cli_exec(["status"])
        assert mock.calls[0]["cmd"] == ["/absolute/path/to/vds-cli", "status"]

    def test_vds_cli_exec_raises_runtime_error_when_not_on_path(self) -> None:
        """Miss branch: shutil.which returns None -- RuntimeError with install hint."""
        with patch(_WHICH_TARGET, return_value=None):
            mock = MockRunner(stdout="", returncode=0)
            executor = SkillExecutor(runner=mock)
            with pytest.raises(RuntimeError) as exc_info:
                executor.vds_cli_exec(["status"])
        error_msg = str(exc_info.value)
        assert "uv tool install --editable" in error_msg
        assert "PATH" in error_msg

    def test_executor_module_imports_with_shutil_which_returning_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Import safety: shutil.which is called inside the method, not at module import time."""
        import vds_agent_core.skills.executor as executor_mod

        monkeypatch.setattr("shutil.which", lambda _name: None)
        # Reload to confirm module-level code does not call shutil.which
        reloaded = importlib.reload(executor_mod)
        assert reloaded is not None
        assert hasattr(reloaded, "SkillExecutor")
