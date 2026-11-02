import asyncio
from pathlib import Path

import pytest
from vds_git_orchestrator import orchestrator as orchestrator_module
from vds_git_orchestrator.manifest import Manifest, ManifestFilters, Repository
from vds_git_orchestrator.orchestrator import GitOperation, orchestrate_repositories


@pytest.mark.parametrize(
    "message",
    [
        "fatal: bad object 1234",
        "error: invalid index-pack output",
        "pack has 3 unresolved deltas",
        "reference is not a tree: deadbeef",
        "object file is empty",
        "loose object 1234 is corrupt",
        "missing necessary objects",
        "fatal: fetch-pack: invalid index-pack output",
        "could not parse commit 1234",
        "index file corrupt",
        "broken link from 1234 to 5678",
        "directory exists but is not a git repository",
    ],
)
def test_is_corruption_error_detects_patterns(message: str) -> None:
    assert orchestrator_module._is_corruption_error(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "Could not read from remote repository.",
        "fatal: Authentication failed",
        "fatal: repository not found",
    ],
)
def test_is_corruption_error_ignores_non_corruption(message: str) -> None:
    assert orchestrator_module._is_corruption_error(message) is False


def test_is_local_workspace_repo_detects_local_project(tmp_path: Path) -> None:
    repo = Repository(
        name="local-repo",
        path=tmp_path / "local-repo",
        project="local",
        branch="main",
        tags=set(),
    )
    assert orchestrator_module._is_local_workspace_repo(repo) is True


def test_is_local_workspace_repo_detects_local_tag(tmp_path: Path) -> None:
    repo = Repository(
        name="tagged-local-repo",
        path=tmp_path / "tagged-local-repo",
        project="insurance",
        branch="main",
        tags={"local"},
    )
    assert orchestrator_module._is_local_workspace_repo(repo) is True


@pytest.mark.asyncio
async def test_pull_repo_recovery_retries_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="corrupt-repo",
        path=tmp_path / "corrupt-repo",
        project="insurance",
        branch="release",
        tags=set(),
    )

    run_calls: list[list[str]] = []
    recover_calls: list[str] = []

    async def fake_run_git(target_repo: Repository, args: list[str]):  # type: ignore[no-untyped-def]
        # Non-pull commands (e.g. rev-parse for upstream tracking) should succeed silently
        if args and args[0] != "pull":
            return 0, "", ""
        run_calls.append(args)
        if len(run_calls) == 1:
            return 1, "", "fatal: bad object"
        return 0, "Fast-forward", ""

    async def fake_recover_repo(target_repo: Repository, run_id: str):  # type: ignore[no-untyped-def]
        recover_calls.append(target_repo.name)
        return True, "recovered"

    monkeypatch.setattr(orchestrator_module, "_run_git", fake_run_git)
    monkeypatch.setattr(orchestrator_module, "_recover_repo", fake_recover_repo)

    result = await orchestrator_module._pull_repo(repo, dry_run=False, run_id="run")

    assert result.success is True
    assert len(run_calls) == 2
    assert recover_calls == ["corrupt-repo"]


@pytest.mark.asyncio
async def test_pull_repo_local_repo_skips_destructive_recovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="local-repo",
        path=tmp_path / "local-repo",
        project="local",
        branch="main",
        tags={"local"},
    )

    async def fake_run_git(target_repo: Repository, args: list[str]):  # type: ignore[no-untyped-def]
        return 1, "", "Directory exists but is not a git repository"

    async def fail_recover_repo(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("local sync must not trigger destructive recovery")

    monkeypatch.setattr(orchestrator_module, "_run_git", fake_run_git)
    monkeypatch.setattr(orchestrator_module, "_recover_repo", fail_recover_repo)

    result = await orchestrator_module._pull_repo(repo, dry_run=False, run_id="run")

    assert result.success is False
    assert "not a git repository" in (result.message or "").lower()


@pytest.mark.asyncio
async def test_pull_repo_dry_run_skips_recovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="dry-repo",
        path=tmp_path / "dry-repo",
        project="insurance",
        branch="release",
        tags=set(),
    )

    async def fail_call(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("dry-run should not invoke git or recovery")

    monkeypatch.setattr(orchestrator_module, "_run_git", fail_call)
    monkeypatch.setattr(orchestrator_module, "_recover_repo", fail_call)

    result = await orchestrator_module._pull_repo(repo, dry_run=True, run_id="dry")

    assert result.success is True
    assert result.message == "dry-run"


class _FakeProcess:
    def __init__(self, returncode: int, stderr: bytes) -> None:
        self.returncode = returncode
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return b"", self._stderr


@pytest.mark.asyncio
async def test_verify_credentials_raises_on_401(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="auth-repo",
        path=tmp_path / "auth-repo",
        project="insurance",
        branch="release",
        tags=set(),
    )

    async def fake_create_subprocess_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _FakeProcess(1, b"HTTP 401 Unauthorized")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    with pytest.raises(RuntimeError, match="Authentication failed"):
        await orchestrator_module._verify_credentials(repo)


@pytest.mark.asyncio
async def test_verify_credentials_raises_on_403(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="auth-repo",
        path=tmp_path / "auth-repo",
        project="insurance",
        branch="release",
        tags=set(),
    )

    async def fake_create_subprocess_exec(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _FakeProcess(1, b"403 Forbidden")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    with pytest.raises(RuntimeError, match="Authentication failed"):
        await orchestrator_module._verify_credentials(repo)


@pytest.mark.asyncio
async def test_orchestrate_preflight_aborts_on_auth_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="auth-preflight",
        path=tmp_path / "auth-preflight",
        project="insurance",
        branch="release",
        tags=set(),
    )

    manifest = Manifest([repo])

    async def fake_check_network(*args, **kwargs):  # type: ignore[no-untyped-def]
        return True, "ok"

    async def fake_verify_credentials(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("Authentication failed for http://example")

    async def fail_pre_clone(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("pre-clone should not run after auth failure")

    monkeypatch.setattr(orchestrator_module, "_check_network_connectivity", fake_check_network)
    monkeypatch.setattr(orchestrator_module, "_verify_credentials", fake_verify_credentials)
    monkeypatch.setattr(orchestrator_module, "_ensure_all_repos_cloned", fail_pre_clone)

    with pytest.raises(RuntimeError, match="Authentication failed"):
        await orchestrate_repositories(
            manifest=manifest,
            operation=GitOperation.PULL,
            filters=ManifestFilters(),
            concurrency=1,
            dry_run=False,
            run_id="auth",
            retries=0,
        )


@pytest.mark.asyncio
async def test_run_git_executes_once_without_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    (repo_path / ".git").mkdir(parents=True)
    repo = Repository(
        name="single-call",
        path=repo_path,
        project="insurance",
        branch="release",
        tags=set(),
    )

    calls: list[list[str]] = []

    async def fake_run_process(command: list[str], cwd: Path):  # type: ignore[no-untyped-def]
        calls.append(command)
        return 0, "ok", ""

    monkeypatch.setattr(orchestrator_module, "_run_process", fake_run_process)

    returncode, stdout, stderr = await orchestrator_module._run_git(repo, ["status", "--short"])

    assert returncode == 0
    assert stdout == "ok"
    assert stderr == ""
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_run_git_retries_once_after_index_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_path = tmp_path / "repo"
    git_dir = repo_path / ".git"
    git_dir.mkdir(parents=True)
    lock_path = git_dir / "index.lock"
    lock_path.write_text("stale lock", encoding="utf-8")

    repo = Repository(
        name="lock-retry",
        path=repo_path,
        project="insurance",
        branch="release",
        tags=set(),
    )

    attempts = 0

    async def fake_run_process(command: list[str], cwd: Path):  # type: ignore[no-untyped-def]
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            message = f"error: Unable to create '{lock_path}': File exists."
            return 1, "", message
        return 0, "ok", ""

    monkeypatch.setattr(orchestrator_module, "_run_process", fake_run_process)

    returncode, stdout, stderr = await orchestrator_module._run_git(repo, ["status", "--short"])

    assert attempts == 2
    assert returncode == 0
    assert stdout == "ok"
    assert stderr == ""
    assert lock_path.exists() is False


@pytest.mark.asyncio
async def test_pull_repo_overwrite_local_with_remote(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="force-sync",
        path=tmp_path / "force-sync",
        project="insurance",
        branch="release",
        tags=set(),
    )

    rev_parse_calls = 0
    commands: list[list[str]] = []

    async def fake_run_git(target_repo: Repository, args: list[str]):  # type: ignore[no-untyped-def]
        nonlocal rev_parse_calls
        commands.append(args)

        if args == ["fetch", "--all", "--prune"]:
            return 0, "", ""
        if args == ["show-ref", "--verify", "refs/remotes/origin/release"]:
            return 0, "refs/remotes/origin/release", ""
        if args == ["rev-parse", "HEAD"]:
            rev_parse_calls += 1
            if rev_parse_calls == 1:
                return 0, "abc123\n", ""
            return 0, "def456\n", ""
        if args == ["checkout", "-B", "release", "origin/release"]:
            return 0, "Switched to and reset branch 'release'", ""
        if args == ["reset", "--hard", "origin/release"]:
            return 0, "HEAD is now at def456 sync", ""
        return 1, "", f"unexpected args: {args}"

    monkeypatch.setattr(orchestrator_module, "_run_git", fake_run_git)

    result = await orchestrator_module._pull_repo(
        repo,
        dry_run=False,
        run_id="force-sync",
        overwrite_local_with_remote=True,
    )

    assert result.success is True
    assert result.updated is True
    assert "overwrite-local enabled" in (result.message or "")
    assert ["fetch", "--all", "--prune"] in commands
    assert ["checkout", "-B", "release", "origin/release"] in commands
    assert ["reset", "--hard", "origin/release"] in commands
