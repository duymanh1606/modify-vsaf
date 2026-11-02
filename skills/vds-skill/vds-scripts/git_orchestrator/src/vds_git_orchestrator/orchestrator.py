from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from base64 import b64encode
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from .manifest import Manifest, ManifestFilters, Repository

logger = logging.getLogger(__name__)

# Canonical fallback branch order for clone/pull when the primary branch is missing.
_FALLBACK_BRANCHES = ("release", "master", "main", "staging")


async def _run_hook(repo: Repository, command: str) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=str(repo.absolute_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, stdout.decode(), stderr.decode()


class GitOperation(StrEnum):
    FETCH = "fetch"
    PULL = "pull"
    STATUS = "status"
    CLONE = "clone"
    BRANCH = "branch"
    CHECKOUT = "checkout"
    ADD = "add"
    COMMIT = "commit"
    PUSH = "push"
    LOG = "log"
    DIFF = "diff"
    STASH = "stash"
    TAG = "tag"
    REMOTE = "remote"


@dataclass
class RepoResult:
    repo: Repository
    success: bool
    updated: bool = False
    message: str | None = None


@dataclass
class RunSummary:
    total: int
    successes: int
    updates: int
    failures: int
    results: dict[str, RepoResult]
    serial_retries: int = 0

    @classmethod
    def from_results(cls, results: dict[str, RepoResult], serial_retries: int = 0) -> RunSummary:
        successes = sum(1 for result in results.values() if result.success)
        updates = sum(1 for result in results.values() if result.updated)
        failures = len(results) - successes
        return cls(
            total=len(results),
            successes=successes,
            updates=updates,
            failures=failures,
            results=results,
            serial_retries=serial_retries,
        )

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "successes": self.successes,
            "updates": self.updates,
            "failures": self.failures,
            "serial_retries": self.serial_retries,
            "results": {
                name: {
                    "project": result.repo.project,
                    "path": str(result.repo.absolute_path),
                    "branch": result.repo.branch,
                    "success": result.success,
                    "updated": result.updated,
                    "message": result.message,
                }
                for name, result in self.results.items()
            },
        }


def _is_corruption_error(message: str) -> bool:
    """Check if the git error message indicates repository corruption."""
    lowered = message.lower()
    patterns = (
        "bad object",
        "invalid index-pack output",
        "pack has",  # matches "pack has X unresolved deltas" (necessary regex context)
        "did not send all necessary objects",
        "reference is not a tree",
        "object file is empty",
        "loose object",  # matches "loose object ... is corrupt" (necessary regex context)
        "missing necessary objects",
        "fatal: fetch-pack: invalid index-pack output",
        "could not parse commit",
        "index file corrupt",
        "broken link",
        "directory exists but is not a git repository",
    )
    return any(pattern in lowered for pattern in patterns)


def _is_local_workspace_repo(repo: Repository) -> bool:
    """Return True when the repo comes from --local sync source."""
    if repo.project == "local":
        return True
    return "local" in repo.tags


def _is_remote_ref_conflict_error(message: str) -> bool:
    """Detect remote-tracking ref conflicts caused by stale local refs."""
    lowered = message.lower()
    if "cannot lock ref 'refs/remotes/origin/" not in lowered:
        return False
    return "exists; cannot create" in lowered or (" is at " in lowered and " but expected " in lowered)


async def _recover_repo(repo: Repository, run_id: str) -> tuple[bool, str]:
    """Perform destructive recovery (move to backup + re-clone)."""
    timestamp = int(time.time())
    base_backup_path = repo.absolute_path.parent / f"{repo.name}.corrupted.{timestamp}"
    backup_path = base_backup_path
    if backup_path.exists():
        suffix = 1
        while backup_path.exists():
            backup_path = repo.absolute_path.parent / f"{base_backup_path.name}.{suffix}"
            suffix += 1

    logger.warning(
        "corruption-recovery-start",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "backup_path": str(backup_path),
            "run_id": run_id,
        },
    )

    try:
        if repo.absolute_path.exists():
            shutil.move(str(repo.absolute_path), str(backup_path))
    except Exception as e:
        return False, f"Could not move corrupted repo: {e}"

    # Auto-clone (Logic: ensure_repo checks existence, if missing it clones)
    return await _ensure_repo_directory(repo)


def _get_git_config_value(_key: str, default: str, env_key: str | None = None) -> str:
    """Get git config value from environment variable or use default.

    Environment variables are loaded through the shared VDS env path/config layer.
    """
    if env_key:
        env_value = os.environ.get(env_key)
        if env_value:
            return env_value
    return default


def _build_git_command(_repo: Repository, args: list[str]) -> list[str]:
    """Build git command with authentication and network configuration.

    All network settings are configurable via environment variables in the shared VDS env file:
    - VDS_GIT_HTTP_TIMEOUT: HTTP timeout in seconds (default: 300)
    - VDS_GIT_HTTP_POST_BUFFER: POST buffer size in bytes (default: 524288000 = 500MB)
    - VDS_GIT_HTTP_LOW_SPEED_LIMIT: Minimum speed in bytes/sec (default: 1000 = 1KB/s)
    - VDS_GIT_HTTP_LOW_SPEED_TIME: Time at low speed before abort in seconds (default: 300)
    """
    cmd = ["git"]
    username = os.environ.get("VDS_USERNAME")
    password = os.environ.get("VDS_PASSWORD")
    if username and password:
        token = b64encode(f"{username}:{password}".encode()).decode()
        header = f"Authorization: Basic {token}"
        cmd.extend(["-c", f"http.extraHeader={header}"])

    # Network timeout and retry settings (all configurable via environment variables)
    http_timeout = _get_git_config_value("http.timeout", "300", "VDS_GIT_HTTP_TIMEOUT")
    http_post_buffer = _get_git_config_value("http.postBuffer", "524288000", "VDS_GIT_HTTP_POST_BUFFER")
    http_low_speed_limit = _get_git_config_value("http.lowSpeedLimit", "1000", "VDS_GIT_HTTP_LOW_SPEED_LIMIT")
    http_low_speed_time = _get_git_config_value("http.lowSpeedTime", "300", "VDS_GIT_HTTP_LOW_SPEED_TIME")

    cmd.extend(["-c", f"http.timeout={http_timeout}"])
    cmd.extend(["-c", f"http.postBuffer={http_post_buffer}"])
    cmd.extend(["-c", f"http.lowSpeedLimit={http_low_speed_limit}"])
    cmd.extend(["-c", f"http.lowSpeedTime={http_low_speed_time}"])
    cmd.extend(args)
    return cmd


async def _ensure_repo_directory(repo: Repository) -> tuple[bool, str]:
    """
    Ensure the repository directory exists. If it doesn't, attempt to clone it.

    Returns:
        tuple[bool, str]: (success, message)
    """
    if repo.absolute_path.exists():
        # Check if it's actually a git repository
        if (repo.absolute_path / ".git").exists():
            return True, "exists"
        # Directory exists but not a git repo - this is an error state
        return False, f"Directory exists but is not a git repository: {repo.absolute_path}"

    # Directory doesn't exist - try to clone it
    logger.info(
        "auto-clone",
        extra={"repo": repo.name, "project": repo.project, "path": str(repo.absolute_path)},
    )

    # Create parent directories (must exist before running git clone)
    try:
        repo.absolute_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure parent directory actually exists (check after creation)
        if not repo.absolute_path.parent.exists():
            return False, f"Failed to create parent directory: {repo.absolute_path.parent}"
    except Exception as e:
        return False, f"Failed to create parent directory: {e}"

    # Attempt to clone
    remote = _remote_url(repo)
    branch_args = ["--branch", repo.branch] if repo.branch else []
    command = _build_git_command(repo, ["clone", *branch_args, remote, str(repo.absolute_path)])
    returncode, stdout, stderr = await _run_process(command, repo.absolute_path.parent)

    if returncode != 0 and branch_args:
        # If branch-specific clone failed, try without branch (clone default branch)
        logger.warning(
            "clone-with-branch-failed",
            extra={
                "repo": repo.name,
                "project": repo.project,
                "branch": repo.branch,
                "stderr": stderr,
            },
        )
        command = _build_git_command(repo, ["clone", remote, str(repo.absolute_path)])
        returncode, stdout, stderr = await _run_process(command, repo.absolute_path.parent)

    if returncode == 0:
        return True, "auto-cloned"
    return False, f"Auto-clone failed: {stderr or stdout}"


async def _run_git(repo: Repository, args: list[str]) -> tuple[int, str, str]:
    """
    Run a git command for the given repository with VDS defaults applied.

    This helper also contains targeted self-healing for common failure modes
    that are safe to fix automatically:

    - Missing repository directories: automatically attempts to clone the repo
    - Stale `.git/index.lock` files left behind by crashed git processes:
      we delete the lock file inside the repo and retry the command once.
    """
    # Ensure the repository directory exists (auto-clone if missing)
    if not repo.absolute_path.exists() or not (repo.absolute_path / ".git").exists():
        success, message = await _ensure_repo_directory(repo)
        if not success:
            # Return error if auto-clone failed
            return 1, "", message

    command = _build_git_command(repo, args)
    returncode, stdout, stderr = await _run_process(command, repo.absolute_path)

    # Handle stale index.lock left by a crashed git process.
    # Example stderr:
    #   error: Unable to create '/path/to/repo/.git/index.lock': File exists.
    #   Another git process seems to be running in this repository...
    text = (stderr or "") + (stdout or "")
    if returncode != 0 and ".git/index.lock" in text and "File exists" in text:
        lock_path = repo.absolute_path / ".git" / "index.lock"
        try:
            if lock_path.exists():
                logger.warning(
                    "Removing stale index.lock",
                    extra={
                        "repo": repo.name,
                        "project": repo.project,
                        "lock_path": str(lock_path),
                    },
                )
                lock_path.unlink()
        except Exception:
            # If we cannot safely remove the lock, surface the original error.
            return returncode, stdout, stderr

        # Retry the exact same git command once after removing the lock.
        return await _run_process(command, repo.absolute_path)

    # Handle stale/conflicting remote-tracking refs:
    # fatal: cannot lock ref 'refs/remotes/origin/<...>': '<...>' exists; cannot create '<...>'
    if returncode != 0 and args and args[0] in {"fetch", "pull"} and _is_remote_ref_conflict_error(text):
        logger.warning(
            "remote-ref-conflict-detected",
            extra={
                "repo": repo.name,
                "project": repo.project,
                "args": args,
                "error": text.strip(),
            },
        )
        prune_command = _build_git_command(repo, ["remote", "prune", "origin"])
        prune_rc, prune_stdout, prune_stderr = await _run_process(prune_command, repo.absolute_path)
        if prune_rc == 0:
            logger.info(
                "remote-ref-conflict-pruned",
                extra={"repo": repo.name, "project": repo.project},
            )
            return await _run_process(command, repo.absolute_path)
        logger.warning(
            "remote-ref-conflict-prune-failed",
            extra={
                "repo": repo.name,
                "project": repo.project,
                "stdout": prune_stdout.strip(),
                "stderr": prune_stderr.strip(),
            },
        )

    return returncode, stdout, stderr


async def _run_process(command: list[str], cwd: os.PathLike[str]) -> tuple[int, str, str]:
    """
    Run a process with the given command and working directory.

    Note: The cwd directory must exist before calling this function.
    """
    cwd_path = Path(cwd)
    if not cwd_path.exists():
        return (
            1,
            "",
            f"Working directory does not exist: {cwd_path}",
        )

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, stdout.decode(), stderr.decode()


def _remote_base() -> str:
    """Get Bitbucket base URL from environment or use default.

    Default: http://bitbucket.digital.vn/

    Environment variable priority (FR-21.1.1):
    1. VDS_BITBUCKET_URL (primary - recommended)
    2. VDS_BITBUCKET_HTTP_BASE (legacy alias)
    3. BITBUCKET_BASE_URL (legacy alias)

    Can be configured via the shared VDS env file
    """
    # Check env vars in priority order
    base = (
        os.environ.get("VDS_BITBUCKET_URL")
        or os.environ.get("VDS_BITBUCKET_HTTP_BASE")
        or os.environ.get("BITBUCKET_BASE_URL")
        or "http://bitbucket.digital.vn/"
    ).rstrip("/")
    # Ensure base doesn't end with /scm (we add that in _remote_url)
    if base.endswith("/scm"):
        base = base[:-4]
    return base


def _remote_url(repo: Repository) -> str:
    """Construct git remote URL from base URL, project, and repo name.

    Format: {base}/scm/{project}/{repo}.git
    Example: http://bitbucket.digital.vn/scm/insurance/insurance-policy-business.git
    """
    base = _remote_base()
    return f"{base}/scm/{repo.project}/{repo.name}.git"


async def _pull_repo(
    repo: Repository,
    dry_run: bool,
    run_id: str,
    overwrite_local_with_remote: bool = False,
    allow_recovery: bool = True,
    recovery_tracker: dict[str, bool] | None = None,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info("pull", extra={"repo": repo.name, "project": repo.project, "run_id": run_id})

    if overwrite_local_with_remote:
        return await _pull_repo_overwrite_local_with_remote(repo, run_id=run_id)

    # Fix upstream tracking if it differs from the manifest branch.
    # Handles repos cloned tracking `master` when the remote default changed to `release` (or vice-versa).
    upstream_rc, upstream_out, _ = await _run_git(repo, ["rev-parse", "--abbrev-ref", "@{upstream}"])
    if upstream_rc == 0:
        current_upstream = upstream_out.strip()  # e.g. "origin/master"
        expected_upstream = f"origin/{repo.branch}"
        if current_upstream and current_upstream != expected_upstream:
            logger.info(
                "fix-upstream-tracking",
                extra={
                    "repo": repo.name,
                    "run_id": run_id,
                    "from": current_upstream,
                    "to": expected_upstream,
                },
            )
            await _run_git(repo, ["branch", f"--set-upstream-to={expected_upstream}"])

    returncode, stdout, stderr = await _run_git(repo, ["pull", "--ff-only"])

    # Success on first attempt – standard fast‑forward pull.
    if returncode == 0:
        updated = any(line for line in stdout.splitlines() if "Fast-forward" in line)
        return RepoResult(repo=repo, success=True, updated=updated, message=stdout.strip())

    message = (stderr.strip() or stdout.strip() or "").strip()

    # Detect branch-not-found errors that warrant a fallback attempt.
    msg_lower = message.lower()
    branch_missing = (
        ("no such ref was fetched" in message)
        or ("couldn't find remote ref" in msg_lower)
        or ("remote ref did not resolve" in msg_lower)
    )

    if branch_missing:
        # Build fallback candidates: every branch in the canonical list that
        # differs from the manifest branch (which already failed).
        fallback_candidates = [b for b in _FALLBACK_BRANCHES if b != repo.branch]

        for fb_branch in fallback_candidates:
            logger.info(
                "pull-fallback-trying",
                extra={
                    "repo": repo.name,
                    "project": repo.project,
                    "run_id": run_id,
                    "primary_branch": repo.branch,
                    "branch": fb_branch,
                },
            )
            fb_code, fb_stdout, _fb_stderr = await _run_git(repo, ["pull", "--ff-only", "origin", fb_branch])

            if fb_code == 0:
                fb_updated = any(line for line in fb_stdout.splitlines() if "Fast-forward" in line)
                return RepoResult(
                    repo=repo,
                    success=True,
                    updated=fb_updated,
                    message=(fb_stdout.strip() or f"pulled from origin/{fb_branch}"),
                )

        # All fallback branches exhausted — report last error.
        return RepoResult(repo=repo, success=False, message=message)

    # Unhandled failure – surface the original git error.
    # Check for corruption and attempt recovery once
    allow_recovery = allow_recovery and not (recovery_tracker or {}).get("attempted", False)
    if allow_recovery and _is_corruption_error(message) and not _is_local_workspace_repo(repo):
        logger.warning(
            "corruption-detected",
            extra={"repo": repo.name, "run_id": run_id, "error": message},
        )
        if not dry_run:
            if recovery_tracker is not None:
                recovery_tracker["attempted"] = True
            recovered, rec_msg = await _recover_repo(repo, run_id)
            if recovered:
                # Retry pull on fresh clone (disable further recovery to prevent loop)
                return await _pull_repo(repo, dry_run, run_id, allow_recovery=False, recovery_tracker=recovery_tracker)
            else:
                message = f"{message} | Recovery failed: {rec_msg}"

    return RepoResult(repo=repo, success=False, message=message)


async def _resolve_remote_branch(repo: Repository) -> tuple[str | None, str | None]:
    """Resolve the best available origin branch (manifest branch first, then fallbacks)."""
    candidates: list[str] = []
    if repo.branch:
        candidates.append(repo.branch)
    for fallback in _FALLBACK_BRANCHES:
        if fallback not in candidates:
            candidates.append(fallback)

    last_error = ""
    for candidate in candidates:
        returncode, stdout, stderr = await _run_git(
            repo,
            ["show-ref", "--verify", f"refs/remotes/origin/{candidate}"],
        )
        if returncode == 0:
            return candidate, None
        last_error = (stderr.strip() or stdout.strip() or last_error).strip()

    if not candidates:
        return None, "No candidate branches available for remote resolution."
    suffix = f" ({last_error})" if last_error else ""
    return None, f"No matching remote branch found in origin for candidates: {', '.join(candidates)}{suffix}"


async def _pull_repo_overwrite_local_with_remote(repo: Repository, run_id: str) -> RepoResult:
    """Force local working branch to match remote branch by hard-resetting to origin/<branch>."""
    logger.info(
        "pull-overwrite-local-enabled",
        extra={"repo": repo.name, "project": repo.project, "run_id": run_id, "manifest_branch": repo.branch},
    )

    fetch_rc, fetch_stdout, fetch_stderr = await _run_git(repo, ["fetch", "--all", "--prune"])
    if fetch_rc != 0:
        fetch_message = (fetch_stderr.strip() or fetch_stdout.strip() or "git fetch failed").strip()
        return RepoResult(repo=repo, success=False, message=fetch_message)

    target_branch, branch_error = await _resolve_remote_branch(repo)
    if not target_branch:
        return RepoResult(repo=repo, success=False, message=branch_error or "Unable to resolve origin branch.")

    before_sha = ""
    before_rc, before_stdout, _ = await _run_git(repo, ["rev-parse", "HEAD"])
    if before_rc == 0:
        before_sha = before_stdout.strip()

    checkout_rc, checkout_stdout, checkout_stderr = await _run_git(
        repo,
        ["checkout", "-B", target_branch, f"origin/{target_branch}"],
    )
    if checkout_rc != 0:
        checkout_message = (checkout_stderr.strip() or checkout_stdout.strip() or "git checkout failed").strip()
        return RepoResult(repo=repo, success=False, message=checkout_message)

    reset_rc, reset_stdout, reset_stderr = await _run_git(repo, ["reset", "--hard", f"origin/{target_branch}"])
    if reset_rc != 0:
        reset_message = (reset_stderr.strip() or reset_stdout.strip() or "git reset --hard failed").strip()
        return RepoResult(repo=repo, success=False, message=reset_message)

    after_sha = ""
    after_rc, after_stdout, _ = await _run_git(repo, ["rev-parse", "HEAD"])
    if after_rc == 0:
        after_sha = after_stdout.strip()

    updated = bool(before_sha and after_sha and before_sha != after_sha)
    message_parts = [f"synced local branch to origin/{target_branch} (overwrite-local enabled)"]
    if repo.branch != target_branch:
        message_parts.append(f"manifest branch '{repo.branch}' not found on origin; used '{target_branch}'")
    reset_message = reset_stdout.strip()
    if reset_message:
        message_parts.append(reset_message)
    return RepoResult(repo=repo, success=True, updated=updated, message=" | ".join(message_parts))


async def _fetch_repo(
    repo: Repository,
    dry_run: bool,
    run_id: str,
    allow_recovery: bool = True,
    recovery_tracker: dict[str, bool] | None = None,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info("fetch", extra={"repo": repo.name, "project": repo.project, "run_id": run_id})
    returncode, stdout, stderr = await _run_git(repo, ["fetch", "--all", "--prune"])

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    message = (stderr.strip() or stdout.strip() or "").strip()

    allow_recovery = allow_recovery and not (recovery_tracker or {}).get("attempted", False)
    if allow_recovery and _is_corruption_error(message) and not _is_local_workspace_repo(repo):
        logger.warning(
            "corruption-detected",
            extra={"repo": repo.name, "run_id": run_id, "error": message},
        )
        if not dry_run:
            if recovery_tracker is not None:
                recovery_tracker["attempted"] = True
            recovered, rec_msg = await _recover_repo(repo, run_id)
            if recovered:
                # Retry fetch on fresh clone
                return await _fetch_repo(repo, dry_run, run_id, allow_recovery=False, recovery_tracker=recovery_tracker)
            else:
                message = f"{message} | Recovery failed: {rec_msg}"

    return RepoResult(repo=repo, success=False, message=message)


async def _status_repo(repo: Repository, _run_id: str) -> RepoResult:
    returncode, stdout, stderr = await _run_git(repo, ["status", "--short"])
    if returncode == 0:
        message = stdout.strip() or "clean"
        updated = bool(stdout.strip())
        return RepoResult(repo=repo, success=True, updated=updated, message=message)

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _clone_repo(repo: Repository, dry_run: bool, run_id: str) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    if repo.absolute_path.exists():
        return RepoResult(repo=repo, success=True, updated=False, message="exists")

    repo.absolute_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("clone", extra={"repo": repo.name, "project": repo.project, "run_id": run_id})

    remote = _remote_url(repo)

    # Build ordered list: primary branch first, then fallback candidates (skipping duplicates).
    branches_to_try: list[str] = []
    if repo.branch:
        branches_to_try.append(repo.branch)
    for fb in _FALLBACK_BRANCHES:
        if fb not in branches_to_try:
            branches_to_try.append(fb)

    last_error = ""
    for branch in branches_to_try:
        # Clean up any partial clone left by a previous attempt
        if repo.absolute_path.exists():
            shutil.rmtree(repo.absolute_path, ignore_errors=True)

        if branch != branches_to_try[0]:
            logger.info(
                "clone-fallback-trying",
                extra={
                    "repo": repo.name,
                    "project": repo.project,
                    "run_id": run_id,
                    "branch": branch,
                    "primary_branch": branches_to_try[0],
                },
            )

        command = _build_git_command(repo, ["clone", "--branch", branch, remote, str(repo.absolute_path)])
        returncode, stdout, stderr = await _run_process(command, repo.absolute_path.parent)

        if returncode == 0:
            msg = f"cloned (branch={branch})" if branch != branches_to_try[0] else "cloned"
            return RepoResult(repo=repo, success=True, updated=True, message=msg)

        last_error = (stderr.strip() or stdout.strip() or "").strip()

    # All named branches exhausted — last resort: clone without --branch (remote HEAD).
    if repo.absolute_path.exists():
        shutil.rmtree(repo.absolute_path, ignore_errors=True)

    logger.info(
        "clone-fallback-default-branch",
        extra={"repo": repo.name, "project": repo.project, "run_id": run_id},
    )
    command = _build_git_command(repo, ["clone", remote, str(repo.absolute_path)])
    returncode, stdout, stderr = await _run_process(command, repo.absolute_path.parent)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=True, message="cloned (default branch)")

    return RepoResult(repo=repo, success=False, message=last_error or stderr.strip() or stdout.strip())


async def _branch_repo(
    repo: Repository,
    action: str,
    branch_name: str | None,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "branch",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "action": action,
            "run_id": run_id,
        },
    )

    if action == "list":
        returncode, stdout, stderr = await _run_git(repo, ["branch", "-a"])
    elif action == "create" and branch_name:
        returncode, stdout, stderr = await _run_git(repo, ["branch", branch_name])
    elif action == "delete" and branch_name:
        returncode, stdout, stderr = await _run_git(repo, ["branch", "-d", branch_name])
    else:
        return RepoResult(repo=repo, success=False, message=f"Invalid branch action: {action}")

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _checkout_repo(
    repo: Repository,
    branch_or_path: str,
    create: bool,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "checkout",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "target": branch_or_path,
            "run_id": run_id,
        },
    )

    args = ["checkout"]
    if create:
        args.append("-b")
    args.append(branch_or_path)

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=True, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _add_repo(
    repo: Repository,
    paths: list[str],
    all_files: bool,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "add",
        extra={"repo": repo.name, "project": repo.project, "run_id": run_id},
    )

    args = ["add"]
    if all_files:
        args.append(".")
    else:
        args.extend(paths)

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=True, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _commit_repo(
    repo: Repository,
    message: str,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "commit",
        extra={"repo": repo.name, "project": repo.project, "run_id": run_id},
    )

    returncode, stdout, stderr = await _run_git(repo, ["commit", "-m", message])

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=True, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _push_repo(
    repo: Repository,
    branch: str | None,
    remote: str | None,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "push",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "branch": branch,
            "run_id": run_id,
        },
    )

    args = ["push"]
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=True, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _log_repo(
    repo: Repository,
    limit: int | None,
    oneline: bool,
    run_id: str,
) -> RepoResult:
    logger.info("log", extra={"repo": repo.name, "project": repo.project, "run_id": run_id})

    args = ["log"]
    if oneline:
        args.append("--oneline")
    if limit:
        args.extend(["-n", str(limit)])

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _diff_repo(
    repo: Repository,
    paths: list[str],
    staged: bool,
    run_id: str,
) -> RepoResult:
    logger.info("diff", extra={"repo": repo.name, "project": repo.project, "run_id": run_id})

    args = ["diff"]
    if staged:
        args.append("--staged")
    args.extend(paths)

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _stash_repo(
    repo: Repository,
    action: str,
    message: str | None,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "stash",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "action": action,
            "run_id": run_id,
        },
    )

    args = ["stash"]
    if action == "list":
        args.append("list")
    elif action == "save" and message:
        args.extend(["save", message])
    elif action == "pop":
        args.append("pop")
    elif action == "apply":
        args.append("apply")
    elif action == "drop":
        args.append("drop")
    else:
        return RepoResult(repo=repo, success=False, message=f"Invalid stash action: {action}")

    returncode, stdout, stderr = await _run_git(repo, args)

    if returncode == 0:
        updated = action in ("pop", "apply", "drop")
        return RepoResult(repo=repo, success=True, updated=updated, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _tag_repo(
    repo: Repository,
    action: str,
    tag_name: str | None,
    message: str | None,
    dry_run: bool,
    run_id: str,
) -> RepoResult:
    if dry_run:
        return RepoResult(repo=repo, success=True, updated=False, message="dry-run")

    logger.info(
        "tag",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "action": action,
            "run_id": run_id,
        },
    )

    if action == "list":
        returncode, stdout, stderr = await _run_git(repo, ["tag", "-l"])
    elif action == "create" and tag_name:
        args = ["tag"]
        if message:
            args.extend(["-a", tag_name, "-m", message])
        else:
            args.append(tag_name)
        returncode, stdout, stderr = await _run_git(repo, args)
    elif action == "delete" and tag_name:
        returncode, stdout, stderr = await _run_git(repo, ["tag", "-d", tag_name])
    else:
        return RepoResult(repo=repo, success=False, message=f"Invalid tag action: {action}")

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _remote_repo(
    repo: Repository,
    action: str,
    name: str | None,
    url: str | None,
    run_id: str,
) -> RepoResult:
    logger.info(
        "remote",
        extra={
            "repo": repo.name,
            "project": repo.project,
            "action": action,
            "run_id": run_id,
        },
    )

    if action == "list":
        returncode, stdout, stderr = await _run_git(repo, ["remote", "-v"])
    elif action == "add" and name and url:
        returncode, stdout, stderr = await _run_git(repo, ["remote", "add", name, url])
    elif action == "remove" and name:
        returncode, stdout, stderr = await _run_git(repo, ["remote", "remove", name])
    else:
        return RepoResult(repo=repo, success=False, message=f"Invalid remote action: {action}")

    if returncode == 0:
        return RepoResult(repo=repo, success=True, updated=False, message=stdout.strip())

    return RepoResult(repo=repo, success=False, message=stderr.strip() or stdout.strip())


async def _operate_repo(
    repo: Repository,
    operation: GitOperation,
    dry_run: bool,
    run_id: str,
    **kwargs,
) -> RepoResult:
    if operation == GitOperation.PULL:
        return await _pull_repo(
            repo,
            dry_run=dry_run,
            run_id=run_id,
            overwrite_local_with_remote=bool(kwargs.get("overwrite_local_with_remote", False)),
            recovery_tracker=kwargs.get("recovery_tracker"),
        )
    if operation == GitOperation.FETCH:
        return await _fetch_repo(
            repo,
            dry_run=dry_run,
            run_id=run_id,
            recovery_tracker=kwargs.get("recovery_tracker"),
        )
    if operation == GitOperation.STATUS:
        return await _status_repo(repo, run_id=run_id)
    if operation == GitOperation.CLONE:
        return await _clone_repo(repo, dry_run=dry_run, run_id=run_id)
    if operation == GitOperation.BRANCH:
        return await _branch_repo(
            repo,
            kwargs.get("action", "list"),
            kwargs.get("branch_name"),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.CHECKOUT:
        return await _checkout_repo(
            repo,
            kwargs.get("branch_or_path", "main"),
            kwargs.get("create", False),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.ADD:
        return await _add_repo(
            repo,
            kwargs.get("paths", []),
            kwargs.get("all_files", False),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.COMMIT:
        return await _commit_repo(
            repo,
            kwargs.get("message", ""),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.PUSH:
        return await _push_repo(
            repo,
            kwargs.get("branch"),
            kwargs.get("remote"),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.LOG:
        return await _log_repo(
            repo,
            kwargs.get("limit"),
            kwargs.get("oneline", False),
            run_id=run_id,
        )
    if operation == GitOperation.DIFF:
        return await _diff_repo(
            repo,
            kwargs.get("paths", []),
            kwargs.get("staged", False),
            run_id=run_id,
        )
    if operation == GitOperation.STASH:
        return await _stash_repo(
            repo,
            kwargs.get("action", "list"),
            kwargs.get("message"),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.TAG:
        return await _tag_repo(
            repo,
            kwargs.get("action", "list"),
            kwargs.get("tag_name"),
            kwargs.get("message"),
            dry_run=dry_run,
            run_id=run_id,
        )
    if operation == GitOperation.REMOTE:
        return await _remote_repo(
            repo,
            kwargs.get("action", "list"),
            kwargs.get("name"),
            kwargs.get("url"),
            run_id=run_id,
        )
    raise ValueError(f"Unsupported operation: {operation}")


async def _find_repo_by_remote_url(repo: Repository, search_root: Path) -> Path | None:
    """Find if a repository exists at a different path by checking remote URLs.

    This handles cases where repos were renamed or moved to different folders.
    Returns the path if found, None otherwise.
    """
    remote_url = _remote_url(repo)

    # Search in common project directories
    project_dirs = [
        search_root / f"{repo.project.upper()}-project",
        search_root / repo.project.upper(),
        search_root / repo.project,
    ]

    for project_dir in project_dirs:
        if not project_dir.exists():
            continue

        # Search recursively for .git directories
        for git_dir in project_dir.rglob(".git"):
            if not git_dir.is_dir():
                continue

            repo_path = git_dir.parent
            # Check if this is a git repo and has the same remote URL
            try:
                # Use basic git command (no need for full _build_git_command here)
                command = ["git", "remote", "get-url", "origin"]
                returncode, stdout, _ = await _run_process(command, repo_path)
                if returncode == 0 and remote_url.strip() in stdout.strip():
                    return repo_path
            except Exception:
                continue

    return None


async def _ensure_all_repos_cloned(
    repositories: list[Repository],
    concurrency: int,
    dry_run: bool,
    run_id: str,
) -> dict[str, RepoResult]:
    """
    Ensure all repositories from the manifest are cloned locally.

    This runs before git operations to ensure local directories match remote repo list.
    Handles:
    - New repositories (clone if missing)
    - Renamed/moved repositories (detect by remote URL, clone at new path)
    - Ensures local folders match remote project structure
    """
    if dry_run:
        return {}

    results: dict[str, RepoResult] = {}
    semaphore = asyncio.Semaphore(concurrency)

    # Determine search root (VDS root directory where project folders are)
    # Use the first repo's path to infer the VDS root
    search_root = Path("/")
    if repositories:
        first_repo = repositories[0]
        repo_path = first_repo.absolute_path
        # Walk up from repo path to find VDS root (contains project directories)
        current = repo_path
        for _ in range(10):  # Limit depth to avoid infinite loops
            if current.exists():
                # Check if this looks like VDS root (has project directories)
                if any((current / f"{p.upper()}-project").exists() for p in ["lep", "insurance", "saving", "ekyc"]):
                    search_root = current
                    break
                # Also check if we're at a known project directory level
                if current.name.endswith("-project") and current.parent.exists():
                    search_root = current.parent
                    break
            if current.parent == current:  # Reached filesystem root
                break
            current = current.parent

    async def clone_if_needed(repo: Repository) -> None:
        async with semaphore:
            # Check if repo exists at expected path and is already a valid git repository.
            # Accept both standard `.git/` directories and gitdir pointer files so
            # worktrees and alternate checkout layouts are not treated as missing.
            git_marker = repo.absolute_path / ".git"
            if repo.absolute_path.exists() and (git_marker.is_dir() or git_marker.is_file()):
                return  # Already cloned at correct location

            # Check if repo exists at a different path (renamed/moved)
            existing_path = await _find_repo_by_remote_url(repo, search_root)
            if existing_path and existing_path != repo.absolute_path:
                logger.warning(
                    "repo-moved",
                    extra={
                        "repo": repo.name,
                        "project": repo.project,
                        "old_path": str(existing_path),
                        "new_path": str(repo.absolute_path),
                        "run_id": run_id,
                    },
                )
                # Note: We don't move repos automatically - user should handle this manually
                # But we'll clone at the new location if needed
                # The old location will remain (orphaned) until manually cleaned up

            # Attempt to clone at the expected path
            logger.info(
                "pre-clone",
                extra={
                    "repo": repo.name,
                    "project": repo.project,
                    "path": str(repo.absolute_path),
                    "run_id": run_id,
                },
            )
            result = await _clone_repo(repo, dry_run=False, run_id=run_id)
            results[repo.name] = result

    # Clone all missing repos in parallel
    await asyncio.gather(*[clone_if_needed(repo) for repo in repositories])
    return results


async def _check_network_connectivity(base_url: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Check network connectivity to Bitbucket server.

    Args:
        base_url: Base URL for Bitbucket (e.g., "http://bitbucket.digital.vn")
        timeout: Timeout in seconds for the connectivity check

    Returns:
        Tuple of (is_connected, message)
    """
    try:
        # Extract hostname from URL
        if "://" in base_url:
            hostname = base_url.split("://")[1].split("/", maxsplit=1)[0]
        else:
            hostname = base_url.split("/", maxsplit=1)[0]

        # Use asyncio to create a connection test
        # Try to connect to port 80 (HTTP) or 443 (HTTPS)
        port = 443 if base_url.startswith("https://") else 80

        logger.info(
            "network-check-start",
            extra={
                "hostname": hostname,
                "port": port,
                "base_url": base_url,
            },
        )

        # Create a simple TCP connection test
        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()

            logger.info(
                "network-check-success",
                extra={
                    "hostname": hostname,
                    "port": port,
                    "base_url": base_url,
                },
            )
            return True, f"Successfully connected to {hostname}:{port}"
        except TimeoutError:
            logger.warning(
                "network-check-timeout",
                extra={
                    "hostname": hostname,
                    "port": port,
                    "timeout": timeout,
                    "base_url": base_url,
                },
            )
            return False, f"Connection timeout to {hostname}:{port} (timeout: {timeout}s)"
        except OSError as e:
            logger.warning(
                "network-check-failed",
                extra={
                    "hostname": hostname,
                    "port": port,
                    "error": str(e),
                    "base_url": base_url,
                },
            )
            return False, f"Failed to connect to {hostname}:{port}: {e}"
    except Exception as e:
        logger.exception(
            "network-check-error",
            extra={
                "base_url": base_url,
                "error": str(e),
            },
        )
        return False, f"Network check error: {e}"


def _get_retry_config() -> tuple[int, float]:
    """Get retry configuration from environment variables or use defaults.

    Returns:
        tuple[int, float]: (retries, backoff_multiplier)

    Environment variables (from the shared VDS env file):
    - VDS_GIT_RETRIES: Number of retries (default: 2)
    - VDS_GIT_BACKOFF: Backoff multiplier (default: 1.5)
    """
    retries = 2
    backoff = 1.5

    retries_env = os.environ.get("VDS_GIT_RETRIES")
    if retries_env:
        try:
            retries = int(retries_env)
            retries = max(retries, 0)
        except ValueError:
            pass

    backoff_env = os.environ.get("VDS_GIT_BACKOFF")
    if backoff_env:
        try:
            backoff = float(backoff_env)
            backoff = max(backoff, 1.0)
        except ValueError:
            pass

    return retries, backoff


async def _verify_credentials(repo: Repository) -> None:
    """Verify git credentials by attempting a lightweight ls-remote.

    Raises:
        RuntimeError: If authentication fails (401/403).
    """
    remote = _remote_url(repo)
    # Check HEAD ref - lightweight, doesn't download objects
    command = _build_git_command(repo, ["ls-remote", remote, "HEAD"])

    # Run with a short timeout to fail fast
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

        if process.returncode != 0:
            err_msg = stderr.decode().lower()
            if "401" in err_msg or "403" in err_msg or "authentication failed" in err_msg:
                raise RuntimeError(
                    f"Authentication failed for {remote}. Check VDS_USERNAME/VDS_PASSWORD in the shared VDS env file"
                )
            # Other errors (e.g. repo not found) might not be global auth issues,
            # so we log warning but don't abort everything.
            logger.warning(
                "auth-check-warning",
                extra={"repo": repo.name, "error": stderr.decode().strip()},
            )

    except TimeoutError:
        logger.warning("auth-check-timeout", extra={"repo": repo.name})
    except RuntimeError:
        raise
    except Exception as e:
        # Don't block everything if the check itself crashes unexpectedly
        logger.warning("auth-check-error", extra={"error": str(e)})


async def orchestrate_repositories(
    manifest: Manifest,
    operation: GitOperation,
    filters: ManifestFilters,
    concurrency: int,
    dry_run: bool,
    run_id: str,
    retries: int | None = None,
    backoff: float | None = None,
    allow_serial_recovery: bool = True,
    **operation_kwargs,
) -> RunSummary:
    """Orchestrate git operations across multiple repositories.

    Args:
        retries: Number of retries (default: from VDS_GIT_RETRIES env var or 2)
        backoff: Backoff multiplier (default: from VDS_GIT_BACKOFF env var or 1.5)
    """
    # Get retry configuration from environment or use provided/default values
    if retries is None or backoff is None:
        env_retries, env_backoff = _get_retry_config()
        retries = retries if retries is not None else env_retries
        backoff = backoff if backoff is not None else env_backoff

    repositories = manifest.filter(filters)

    # Log operation start with configuration
    logger.info(
        "operation-start",
        extra={
            "operation": operation.value,
            "repo_count": len(repositories),
            "concurrency": concurrency,
            "retries": retries,
            "backoff": backoff,
            "dry_run": dry_run,
            "run_id": run_id,
            "filters": {
                "project": filters.project,
                "name_match": filters.name_match,
                "include_tags": sorted(filters.include_tags) if filters.include_tags else [],
                "exclude_tags": sorted(filters.exclude_tags) if filters.exclude_tags else [],
            },
        },
    )

    # Check network connectivity before proceeding (only for operations that need network)
    network_required_operations = {
        GitOperation.PULL,
        GitOperation.FETCH,
        GitOperation.CLONE,
        GitOperation.PUSH,
    }
    if not dry_run and operation in network_required_operations and repositories:
        base_url = _remote_base()
        is_connected, message = await _check_network_connectivity(base_url, timeout=5.0)
        if not is_connected:
            logger.warning(
                "network-check-failed-proceeding",
                extra={
                    "base_url": base_url,
                    "connectivity_message": message,
                    "operation": operation.value,
                    "repo_count": len(repositories),
                    "run_id": run_id,
                    "note": "Proceeding with operations despite connectivity check failure. Individual operations will retry.",
                },
            )
        else:
            logger.info(
                "network-check-passed",
                extra={
                    "base_url": base_url,
                    "connectivity_message": message,
                    "operation": operation.value,
                    "run_id": run_id,
                },
            )

        # Pre-flight Auth Check (TSK-004)
        # Verify credentials using the first repository to fail fast if auth is broken
        if repositories:
            logger.info("auth-check-start", extra={"run_id": run_id})
            try:
                await _verify_credentials(repositories[0])
                logger.info("auth-check-passed", extra={"run_id": run_id})
            except RuntimeError as e:
                logger.exception("auth-check-failed", extra={"error": str(e), "run_id": run_id})
                # Re-raise to abort the operation
                raise

    # Step 1: Ensure all repos from manifest are cloned locally
    # This ensures local folders match remote repo list before starting operations
    if operation != GitOperation.CLONE:  # Skip pre-clone if operation is clone itself
        logger.info(
            "pre-clone-check",
            extra={
                "repo_count": len(repositories),
                "run_id": run_id,
                "operation": operation.value,
            },
        )
        pre_clone_results = await _ensure_all_repos_cloned(repositories, concurrency, dry_run, run_id)
        # Log pre-clone results but don't fail the operation if some clones fail
        # (they'll be handled by auto-clone in _run_git if needed)
        cloned_count = sum(1 for r in pre_clone_results.values() if r.success)
        failed_count = len(pre_clone_results) - cloned_count
        if cloned_count > 0 or failed_count > 0:
            logger.info(
                "pre-clone-complete",
                extra={
                    "cloned": cloned_count,
                    "failed": failed_count,
                    "total": len(repositories),
                    "run_id": run_id,
                    "operation": operation.value,
                },
            )

    results: dict[str, RepoResult] = {}

    semaphore = asyncio.Semaphore(concurrency)
    serial_retries = 0

    async def worker(repo: Repository) -> None:
        async with semaphore:
            attempt = 0
            delay = 1.0
            result: RepoResult
            recovery_tracker = {"attempted": False}
            while True:
                attempt += 1
                try:
                    # pre hooks
                    if not dry_run:
                        pre_key = {
                            GitOperation.PULL: "pre_pull",
                            GitOperation.FETCH: "pre_fetch",
                            GitOperation.STATUS: "pre_status",
                            GitOperation.BRANCH: "pre_branch",
                            GitOperation.CHECKOUT: "pre_checkout",
                            GitOperation.ADD: "pre_add",
                            GitOperation.COMMIT: "pre_commit",
                            GitOperation.PUSH: "pre_push",
                            GitOperation.STASH: "pre_stash",
                            GitOperation.TAG: "pre_tag",
                        }.get(operation)
                        if pre_key:
                            for command in repo.hooks.get(pre_key, []):
                                rc, h_stdout, h_stderr = await _run_hook(repo, command)
                                if rc != 0:
                                    results[repo.name] = RepoResult(
                                        repo=repo,
                                        success=False,
                                        message=h_stderr.strip() or h_stdout.strip() or f"hook failed: {command}",
                                    )
                                    return
                    result = await _operate_repo(
                        repo,
                        operation=operation,
                        dry_run=dry_run,
                        run_id=run_id,
                        recovery_tracker=recovery_tracker,
                        **operation_kwargs,
                    )
                except Exception as exc:  # pragma: no cover - fallback safety
                    logger.exception("operation-failed", extra={"repo": repo.name, "run_id": run_id})
                    result = RepoResult(repo=repo, success=False, message=str(exc))

                if result.success or attempt > retries:
                    results[repo.name] = result
                    if result.success and not dry_run:
                        post_key = {
                            GitOperation.PULL: "post_pull",
                            GitOperation.FETCH: "post_fetch",
                            GitOperation.STATUS: "post_status",
                            GitOperation.BRANCH: "post_branch",
                            GitOperation.CHECKOUT: "post_checkout",
                            GitOperation.ADD: "post_add",
                            GitOperation.COMMIT: "post_commit",
                            GitOperation.PUSH: "post_push",
                            GitOperation.STASH: "post_stash",
                            GitOperation.TAG: "post_tag",
                        }.get(operation)
                        if post_key:
                            for command in repo.hooks.get(post_key, []):
                                rc, h_stdout, h_stderr = await _run_hook(repo, command)
                                if rc != 0:
                                    logger.warning(
                                        "hook-failed",
                                        extra={
                                            "repo": repo.name,
                                            "hook": command,
                                            "run_id": run_id,
                                        },
                                    )
                    break

                logger.warning(
                    "retrying",
                    extra={
                        "repo": repo.name,
                        "project": repo.project,
                        "run_id": run_id,
                        "attempt": attempt,
                    },
                )
                await asyncio.sleep(delay)
                delay *= backoff

    async with asyncio.TaskGroup() as tg:
        for repo in repositories:
            tg.create_task(worker(repo))

    if allow_serial_recovery and not dry_run and concurrency > 1:
        fallback_repos = [
            repo
            for repo in repositories
            if not results[repo.name].success and _is_network_error(results[repo.name].message or "")
        ]
        if fallback_repos:
            logger.warning(
                "serial-retry",
                extra={
                    "run_id": run_id,
                    "repos": [r.name for r in fallback_repos],
                },
            )
            serial_retries = len(fallback_repos)
            fallback_manifest = Manifest(fallback_repos)
            fallback_summary = await orchestrate_repositories(
                manifest=fallback_manifest,
                operation=operation,
                filters=ManifestFilters(),
                concurrency=1,
                dry_run=False,
                run_id=run_id,
                retries=retries,
                backoff=backoff,
                allow_serial_recovery=False,
                **operation_kwargs,
            )
            results.update(fallback_summary.results)

    return RunSummary.from_results(results, serial_retries=serial_retries)


def _is_network_error(message: str) -> bool:
    lowered = message.lower()
    patterns = (
        "failed to connect",
        "couldn't connect",
        "could not connect",
        "timeout",
        "timed out",
        "connection refused",
        "could not resolve host",
    )
    return any(pattern in lowered for pattern in patterns)
