"""smoke_deploy_lib — Python helper for scripts/smoke-test-deploy.sh.

Implements the runbook step-runner, artifact writing, and short-circuit
logic used by the smoke test. The Bash wrapper delegates JSON artifact
writing and result aggregation to this module.

Stdlib-only per ADR-INF-8.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Runbook definition — v2.12.2 §Post-Merge Live Deploy order
# ---------------------------------------------------------------------------

RUNBOOK: list[str] = [
    "make build-cli",
    "make run-audit-migrate",
    "make run-progress-migrate",
    "make up-memory",
    "make up-multi-agent",
    "make up-scheduler",
    "make verify",
    # Step 8 (P6 WP-6.3): alembic downgrade regression suite.
    # Exercises the surgical-no-op 0001.downgrade() pattern (ADR-INF-11
    # §Schema-Drop-Safe Downgrade Pattern). Requires Docker daemon.
    # Skip cleanly with: SKIP_DOWNGRADE_TESTS=1 bash scripts/smoke-test-deploy.sh
    "uv run --project scheduler_orchestrator pytest scheduler_orchestrator/tests/test_alembic_downgrade.py -m docker -v --timeout=120",
]


def _run_step(cmd: str, cwd: Path | None = None, timeout: float = 600.0) -> dict[str, Any]:
    """Run a single make target; return step record with timing + exit code.

    timeout (seconds, default 600 = 10 min): caps any single step. A hung
    Docker daemon or stuck health-check would otherwise block the smoke
    script forever; the cap turns that into a recorded failure with
    exit_code=124 (matching GNU timeout convention) so CI can move on.
    """
    t0 = time.monotonic()
    parts = cmd.split()
    try:
        proc = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            timeout=timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124  # GNU timeout convention
        stdout = (
            (exc.stdout or b"").decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = f"TIMEOUT after {timeout}s — {exc}"
    except FileNotFoundError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
    duration = round(time.monotonic() - t0, 3)
    return {
        "command": cmd,
        "exit_code": exit_code,
        "duration_s": duration,
        "stdout": stdout[-2000:] if stdout else "",
        "stderr": stderr[-2000:] if stderr else "",
    }


def run_smoke(
    *,
    artifact_dir: Path,
    repo_root: Path,
    git_sha: str,
    target: str = "live",
) -> dict[str, Any]:
    """Execute the v2.12.2 runbook and write a JSON artifact.

    Parameters
    ----------
    artifact_dir:
        Directory where the smoke-<timestamp>-<sha>.json artifact is written.
        Created automatically if absent.
    repo_root:
        Repository root — make targets are invoked from here.
    git_sha:
        Short git SHA embedded in artifact filename for traceability.
    target:
        ``'live'`` (default) or ``'ephemeral'`` — recorded in artifact.

    Returns
    -------
    dict
        The artifact payload (same data written to disk).
    """
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_name = f"smoke-{timestamp}-{git_sha}.json"
    artifact_path = artifact_dir / artifact_name

    steps: list[dict[str, Any]] = []
    overall_passed = True

    skip_downgrade = os.environ.get("SKIP_DOWNGRADE_TESTS", "0").strip() == "1"

    for cmd in RUNBOOK:
        # Step 8 opt-out: alembic downgrade regression tests require Docker.
        # Operator sets SKIP_DOWNGRADE_TESTS=1 when Docker is unavailable.
        if skip_downgrade and "test_alembic_downgrade" in cmd:
            steps.append(
                {
                    "command": cmd,
                    "exit_code": 0,
                    "duration_s": 0.0,
                    "stdout": "SKIPPED (SKIP_DOWNGRADE_TESTS=1)",
                    "stderr": "",
                }
            )
            continue

        step = _run_step(cmd, cwd=repo_root)
        steps.append(step)
        if step["exit_code"] != 0:
            overall_passed = False
            # Short-circuit: write partial artifact and stop
            break

    payload: dict[str, Any] = {
        "passed": overall_passed,
        "git_sha": git_sha,
        "timestamp": timestamp,
        "target": target,
        "steps": steps,
    }

    artifact_path.write_text(json.dumps(payload, indent=2))

    return payload


# ---------------------------------------------------------------------------
# CLI entry point (used by smoke-test-deploy.sh)
# ---------------------------------------------------------------------------


def _cli() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run v2.12.2 Post-Merge Live Deploy runbook and emit JSON artifact")
    parser.add_argument(
        "--artifact-dir",
        required=True,
        help="Directory to write smoke-<timestamp>-<sha>.json",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for make invocations (default: .)",
    )
    parser.add_argument(
        "--git-sha",
        required=True,
        help="Short git SHA for artifact filename",
    )
    parser.add_argument(
        "--target",
        choices=["live", "ephemeral"],
        default="live",
        help="Deployment target (default: live)",
    )
    args = parser.parse_args()

    result = run_smoke(
        artifact_dir=Path(args.artifact_dir),
        repo_root=Path(args.repo_root),
        git_sha=args.git_sha,
        target=args.target,
    )
    # Print artifact path to stdout for the Bash caller to capture
    artifact_dir = Path(args.artifact_dir)
    artifacts = sorted(artifact_dir.glob(f"smoke-*-{args.git_sha}.json"))
    if artifacts:
        print(str(artifacts[-1]))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(_cli())
