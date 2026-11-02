import os
import subprocess
from pathlib import Path

import pytest
from vds_git_orchestrator.manifest import Manifest, ManifestFilters, Repository
from vds_git_orchestrator.orchestrator import GitOperation, orchestrate_repositories


def _create_remote_repo(base: Path, project: str, name: str) -> None:
    # Match _remote_url logic: base/scm/project/name.git
    remote_path = base / "scm" / project / f"{name}.git"
    remote_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", str(remote_path)], check=True, stdout=subprocess.DEVNULL)

    seed = base.parent / "seed"
    subprocess.run(["git", "init", "-b", "release", str(seed)], check=True, stdout=subprocess.DEVNULL)
    readme = seed / "README.md"
    readme.write_text("seed repo")

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "VDS Bot",
        "GIT_AUTHOR_EMAIL": "vds@example.com",
        "GIT_COMMITTER_NAME": "VDS Bot",
        "GIT_COMMITTER_EMAIL": "vds@example.com",
    }

    subprocess.run(["git", "-C", str(seed), "add", "README.md"], check=True, env=env, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(seed), "commit", "-m", "seed"], check=True, env=env, stdout=subprocess.DEVNULL)
    subprocess.run(
        ["git", "-C", str(seed), "remote", "add", "origin", str(remote_path)], check=True, stdout=subprocess.DEVNULL
    )
    subprocess.run(
        ["git", "-C", str(seed), "push", "origin", "release"], check=True, env=env, stdout=subprocess.DEVNULL
    )


@pytest.mark.asyncio
async def test_clone_against_local_bare_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    remote_root = tmp_path / "remote"
    _create_remote_repo(remote_root, "lep", "service-a")

    monkeypatch.setenv("VDS_BITBUCKET_HTTP_BASE", remote_root.as_uri())
    monkeypatch.delenv("VDS_USERNAME", raising=False)
    monkeypatch.delenv("VDS_PASSWORD", raising=False)

    workspace = tmp_path / "workspace"
    repo = Repository(
        name="service-a",
        path=workspace / "service-a",
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
        dry_run=False,
        run_id="integration",
    )

    assert summary.total == 1
    assert summary.successes == 1
    assert summary.updates == 1
    assert (workspace / "service-a/.git").exists()

    # Ensure the release branch was checked out
    result = subprocess.run(
        ["git", "-C", str(workspace / "service-a"), "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "release"
