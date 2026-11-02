"""Skill executor — runs VDS CLI tools with injectable CommandRunner.

Extracted from audit_orchestrator.agents.skill_executor (FR-5.3, Wave 3).
audit_orchestrator.agents.skill_executor is now a re-export shim.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import warnings
from contextvars import ContextVar
from typing import Any, Protocol

from structlog import get_logger

logger = get_logger()

_tool_usage_var: ContextVar[list[dict[str, Any]] | None] = ContextVar("tool_usage", default=None)


def _record_tool_usage(entry: dict[str, Any]) -> None:
    usage = list(_tool_usage_var.get() or [])
    usage.append(entry)
    _tool_usage_var.set(usage)


def _consume_tool_usage() -> list[dict[str, Any]]:
    usage = list(_tool_usage_var.get() or [])
    _tool_usage_var.set([])
    return usage


class CommandRunner(Protocol):
    """Injectable command runner for skill execution."""

    def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess: ...


class SubprocessRunner:
    """Default CommandRunner using subprocess."""

    def run(self, cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, **kwargs)


class SkillExecutor:
    """Executes VDS AgentSkills with injectable CommandRunner.

    Uses SubprocessRunner by default. Pass a custom CommandRunner for testing
    or alternative execution environments.
    """

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner or SubprocessRunner()

    def vds_cli_exec(self, args: list[str]) -> str:
        """Execute arbitrary vds-cli command.

        Resolves vds-cli via shutil.which (FR-11 / spec v0.5.0). Fails fast
        if not on PATH — no uv run fallback (modern-only posture).
        """
        start = time.monotonic()
        vds_cli_path = shutil.which("vds-cli")
        if vds_cli_path is None:
            raise RuntimeError(
                "vds-cli not found on PATH. "
                "Install with: uv tool install --editable ./WHO-project/vds-scripts/vds_cli "
                "and verify PATH contract (see scripts/README.md#path-contract-for-vds-cli)."
            )
        cmd = [vds_cli_path, *args]
        try:
            result = self._runner.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            success = result.returncode == 0
            _record_tool_usage(
                {
                    "tool": "vds_cli_exec",
                    "args": args,
                    "success": success,
                    "duration_ms": duration_ms,
                }
            )
            return result.stdout if success else result.stderr
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            _record_tool_usage(
                {
                    "tool": "vds_cli_exec",
                    "args": args,
                    "success": False,
                    "error": str(e),
                    "duration_ms": duration_ms,
                }
            )
            return str(e)

    @staticmethod
    def record_tool_usage(entry: dict[str, Any]) -> None:
        """Record tool usage for internal scanners or helpers."""
        _record_tool_usage(entry)

    @staticmethod
    def consume_usage() -> list[dict[str, Any]]:
        """Return and clear tool usage for the current context."""
        return _consume_tool_usage()

    @staticmethod
    def reset_usage() -> None:
        """Clear tool usage for the current context."""
        _tool_usage_var.set([])

    @classmethod
    def _grepai_search(
        cls,
        query: str,
        path: str | None = None,
        *,
        limit: int = 10,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        """Execute grepai semantic code search as a private compatibility helper.

        DEPRECATED: This method is deprecated for security scanning.
        Use SecurityPatternScanner for scoped security pattern detection.

        Phase 23 Refinement (FR-1.4):
        - If path is not provided, a deprecation warning is issued
        - When path is provided, it is passed to grepai CLI for scoped searches
        """
        start = time.monotonic()
        result: dict[str, Any] = {
            "success": False,
            "results": [],
            "query": query,
            "path": path,
            "limit": limit,
        }

        if path is None:
            warnings.warn(
                "grepai_search() without explicit path is deprecated. "
                "Use SecurityPatternScanner for scoped security scanning.",
                DeprecationWarning,
                stacklevel=2,
            )
            logger.warning("grepai_search_unscoped_deprecated", query=query)
            result["warning"] = (
                "Unscoped grepai search is deprecated. Results may include files from the entire monorepo."
            )

        try:
            cmd = ["grepai", "search", query, "--json", "--compact"]
            if path is not None:
                cmd.extend(["--path", path])
            cmd.extend(["--limit", str(limit)])

            proc_result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            duration_ms = int((time.monotonic() - start) * 1000)

            if proc_result.returncode == 0:
                try:
                    output = json.loads(proc_result.stdout) if proc_result.stdout.strip() else []
                    result["success"] = True
                    result["results"] = output if isinstance(output, list) else output.get("results", [])
                except json.JSONDecodeError:
                    result["error"] = "Failed to parse grepai JSON output"
                    result["raw_output"] = proc_result.stdout[:500]
            else:
                result["error"] = proc_result.stderr or "grepai command failed"
                result["returncode"] = proc_result.returncode

            _record_tool_usage(
                {
                    "tool": "_grepai_search",
                    "query": query,
                    "path": path,
                    "limit": limit,
                    "success": result["success"],
                    "results_count": len(result.get("results", [])),
                    "duration_ms": duration_ms,
                    "scoped": path is not None,
                }
            )

        except subprocess.TimeoutExpired:
            duration_ms = int((time.monotonic() - start) * 1000)
            result["error"] = "grepai search timed out after 60 seconds"
            _record_tool_usage(
                {
                    "tool": "_grepai_search",
                    "query": query,
                    "success": False,
                    "error": "timeout",
                    "duration_ms": duration_ms,
                    "scoped": path is not None,
                }
            )
            logger.warning("grepai_search_timeout", query=query, path=path)

        except FileNotFoundError:
            duration_ms = int((time.monotonic() - start) * 1000)
            result["error"] = "grepai command not found - is grepai installed?"
            _record_tool_usage(
                {
                    "tool": "_grepai_search",
                    "query": query,
                    "success": False,
                    "error": "grepai_not_found",
                    "duration_ms": duration_ms,
                    "scoped": path is not None,
                }
            )
            logger.warning("grepai_not_found", query=query)

        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            result["error"] = str(e)
            _record_tool_usage(
                {
                    "tool": "_grepai_search",
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "duration_ms": duration_ms,
                    "scoped": path is not None,
                }
            )
            logger.warning("grepai_search_error", query=query, path=path, error=str(e))

        return result
