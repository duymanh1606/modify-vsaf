"""Tests for repo_ops clone_repo function."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from vds_bitbucket_orchestrator.repo_ops import RepoRef, clone_repo


@pytest.fixture
def ref() -> RepoRef:
    return RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")


class TestCloneRepo:
    """Git clone/pull subprocess tests."""

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_fresh_clone(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "repos" / "TEST-project" / "test-repo"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target)

        assert result.operation == "clone"
        assert result.ref == ref
        cmd = mock_run.call_args[0][0]
        assert "clone" in cmd
        assert "http://bb.vn/scm/TEST/test-repo.git" in cmd

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_pull_when_exists(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "existing-repo"
        target.mkdir(parents=True)
        (target / ".git").mkdir()
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target)

        assert result.operation == "pull"
        cmd = mock_run.call_args[0][0]
        assert "pull" in cmd
        assert "--ff-only" in cmd

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_shallow_clone(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "shallow-repo"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target, shallow=True)

        cmd = mock_run.call_args[0][0]
        assert "--depth" in cmd
        assert "1" in cmd

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_clone_with_branch(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "branched-repo"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target, branch="develop")

        assert result.branch == "develop"
        cmd = mock_run.call_args[0][0]
        assert "--branch" in cmd
        assert "develop" in cmd

    @patch("vds_bitbucket_orchestrator.repo_ops.shutil.rmtree")
    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_force_reclone(self, mock_run, mock_rmtree, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "existing-repo"
        target.mkdir(parents=True)
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        result = clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target, force_reclone=True)

        assert result.operation == "reclone"
        mock_rmtree.assert_called_once_with(target)

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_clone_failure_raises(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "fail-repo"
        mock_run.return_value.returncode = 128
        mock_run.return_value.stderr = "fatal: repository not found"

        with pytest.raises(RuntimeError, match="git clone failed"):
            clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target)

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_pull_failure_raises(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "existing-repo"
        target.mkdir(parents=True)
        (target / ".git").mkdir()
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "fatal: not a git repository"

        with pytest.raises(RuntimeError, match="git pull failed"):
            clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target)

    @patch("vds_bitbucket_orchestrator.repo_ops.subprocess.run")
    def test_creates_parent_directories(self, mock_run, ref: RepoRef, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested" / "path" / "repo"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        clone_repo(ref, "http://bb.vn/scm/TEST/test-repo.git", target)

        assert target.parent.exists()
