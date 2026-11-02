from pathlib import Path

import pytest
from vds_git_orchestrator.manifest import Manifest, ManifestFilters, Repository
from vds_git_orchestrator.orchestrator import GitOperation, orchestrate_repositories


@pytest.mark.asyncio
async def test_orchestrate_repositories_dry_run_skips_hooks(tmp_path: Path) -> None:
    repo_dir = tmp_path / "dry-run"
    repo_dir.mkdir()
    repo = Repository(
        name="dry-run-repo",
        path=repo_dir,
        project="lep",
        branch="release",
        tags=set(),
        hooks={
            "pre_pull": ["touch pre.txt"],
            "post_pull": ["touch post.txt"],
        },
    )

    manifest = Manifest([repo])
    summary = await orchestrate_repositories(
        manifest=manifest,
        operation=GitOperation.PULL,
        filters=ManifestFilters(),
        concurrency=2,
        dry_run=True,
        run_id="test",
    )

    assert summary.total == 1
    assert summary.successes == 1
    assert summary.failures == 0
    assert summary.serial_retries == 0
    assert summary.results["dry-run-repo"].message == "dry-run"
    assert not (repo_dir / "pre.txt").exists()
    assert not (repo_dir / "post.txt").exists()


def _success_git_result() -> tuple[int, str, str]:
    return 0, "Fast-forward", ""


@pytest.mark.asyncio
async def test_orchestrate_repositories_runs_hooks_on_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_dir = tmp_path / "real-run"
    repo_dir.mkdir()

    pre_marker = repo_dir / "pre.marker"
    post_marker = repo_dir / "post.marker"

    repo = Repository(
        name="real-run-repo",
        path=repo_dir,
        project="insurance",
        branch="release",
        tags=set(),
        hooks={
            "pre_pull": [f"touch {pre_marker.name}"],
            "post_pull": [f"touch {post_marker.name}"],
        },
    )

    # Patch _run_git to avoid invoking the real git binary.
    from vds_git_orchestrator import orchestrator as orchestrator_module

    async def fake_run_git(*args, **kwargs):  # type: ignore[no-untyped-def]
        return _success_git_result()

    monkeypatch.setattr(orchestrator_module, "_run_git", fake_run_git)

    manifest = Manifest([repo])
    summary = await orchestrate_repositories(
        manifest=manifest,
        operation=GitOperation.PULL,
        filters=ManifestFilters(),
        concurrency=1,
        dry_run=False,
        run_id="run",
        retries=0,
    )

    assert summary.total == 1
    assert summary.successes == 1
    assert summary.updates == 1
    assert summary.serial_retries == 0
    assert pre_marker.exists()
    assert post_marker.exists()


@pytest.mark.asyncio
async def test_orchestrate_repositories_serial_retry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_dir = tmp_path / "net"
    repo_dir.mkdir()

    repo = Repository(
        name="net-repo",
        path=repo_dir,
        project="lep",
        branch="release",
        tags=set(),
    )

    from vds_git_orchestrator import orchestrator as orchestrator_module

    attempts = {repo.name: 0}

    async def fake_run_git(target_repo: Repository, args: list[str]):  # type: ignore[no-untyped-def]
        # Non-pull commands (e.g. rev-parse for upstream tracking) should succeed silently
        if args and args[0] != "pull":
            return 0, "", ""
        idx = attempts.setdefault(target_repo.name, 0)
        attempts[target_repo.name] = idx + 1
        if idx == 0:
            return 1, "", "Failed to connect to server"
        return 0, "Already up to date", ""

    monkeypatch.setattr(orchestrator_module, "_run_git", fake_run_git)

    manifest = Manifest([repo])
    summary = await orchestrate_repositories(
        manifest=manifest,
        operation=GitOperation.PULL,
        filters=ManifestFilters(),
        concurrency=2,
        dry_run=False,
        run_id="serial",
        retries=0,
    )

    assert summary.total == 1
    assert summary.successes == 1
    assert summary.failures == 0
    assert summary.serial_retries == 1
    # two attempts: first parallel, second serial fallback
    assert attempts[repo.name] == 2


@pytest.mark.asyncio
async def test_clone_dry_run(tmp_path: Path) -> None:
    repo = Repository(
        name="service-a",
        path=tmp_path / "service-a",
        project="lep",
        branch="release",
        tags=set(),
    )

    manifest = Manifest([repo])
    summary = await orchestrate_repositories(
        manifest=manifest,
        operation=GitOperation.CLONE,
        filters=ManifestFilters(),
        concurrency=2,
        dry_run=True,
        run_id="clone-dry",
    )

    assert summary.total == 1
    assert summary.successes == 1
    assert summary.results["service-a"].message == "dry-run"
    assert summary.serial_retries == 0
    assert not repo.absolute_path.exists()


@pytest.mark.asyncio
async def test_clone_executes_git(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = Repository(
        name="service-a",
        path=tmp_path / "service-a",
        project="lep",
        branch="release",
        tags=set(),
    )

    calls: list[tuple[list[str], Path]] = []

    from vds_git_orchestrator import orchestrator as orchestrator_module

    async def fake_run_process(command: list[str], cwd: Path):  # type: ignore[no-untyped-def]
        calls.append((command, cwd))
        repo.absolute_path.mkdir(parents=True, exist_ok=True)
        return 0, "cloned", ""

    monkeypatch.setattr(orchestrator_module, "_run_process", fake_run_process)

    manifest = Manifest([repo])
    summary = await orchestrate_repositories(
        manifest=manifest,
        operation=GitOperation.CLONE,
        filters=ManifestFilters(),
        concurrency=1,
        dry_run=False,
        run_id="clone",
    )

    assert summary.successes == 1
    assert summary.updates == 1
    assert summary.serial_retries == 0
    assert repo.absolute_path.parent.exists()
    # first argument should be git clone
    assert calls
    assert calls[0][0][0] == "git"
    assert "clone" in calls[0][0]
