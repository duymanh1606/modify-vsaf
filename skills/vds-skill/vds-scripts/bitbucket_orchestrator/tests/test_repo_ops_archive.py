"""Tests for repo_ops archive functions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from vds_bitbucket_orchestrator.repo_ops import (
    ArchiveResult,
    RepoRef,
    archive_repo,
    download_rest_archive,
)


@pytest.fixture
def ref() -> RepoRef:
    return RepoRef(project_key="TEST", repo_slug="test-repo", source_format="shorthand")


class TestDownloadRestArchive:
    """REST archive download via BitbucketClient."""

    def test_success(self, ref: RepoRef, tmp_path: Path) -> None:
        output = tmp_path / "test-repo.zip"
        client = MagicMock()

        def write_archive(proj, repo, fd, **kwargs):
            fd.write(b"PK\x03\x04fake-zip-content")

        client.download_archive.side_effect = write_archive

        result = download_rest_archive(client, ref, output)

        assert result is not None
        assert result.method == "rest_api"
        assert result.format == "zip"
        assert result.size_bytes > 0
        assert output.exists()

    def test_returns_none_on_failure(self, ref: RepoRef, tmp_path: Path) -> None:
        output = tmp_path / "test-repo.zip"
        client = MagicMock()
        client.download_archive.side_effect = RuntimeError("404 Not Found")

        result = download_rest_archive(client, ref, output)

        assert result is None
        assert not output.exists()

    def test_returns_none_on_empty_archive(self, ref: RepoRef, tmp_path: Path) -> None:
        output = tmp_path / "test-repo.zip"
        client = MagicMock()
        # download_archive writes nothing → empty file
        client.download_archive.side_effect = lambda *a, **kw: None

        result = download_rest_archive(client, ref, output)

        assert result is None

    def test_passes_format_and_at(self, ref: RepoRef, tmp_path: Path) -> None:
        from unittest.mock import ANY

        output = tmp_path / "test-repo.tar.gz"
        client = MagicMock()

        def write_archive(_proj, _repo, fd, **_kwargs):
            fd.write(b"fake-tar-gz")

        client.download_archive.side_effect = write_archive

        download_rest_archive(client, ref, output, format="tar.gz", at="develop")

        client.download_archive.assert_called_once_with(
            "TEST",
            "test-repo",
            ANY,
            at="develop",
            format="tar.gz",
            path=None,
        )


class TestArchiveRepo:
    """Full archive workflow: REST-first with fallback."""

    @patch("vds_bitbucket_orchestrator.repo_ops.download_rest_archive")
    def test_rest_success_skips_clone(self, mock_rest, ref: RepoRef, tmp_path: Path) -> None:
        output = tmp_path / "out.zip"
        mock_rest.return_value = ArchiveResult(
            archive_path=output,
            format="zip",
            size_bytes=100,
            method="rest_api",
            ref=ref,
        )
        client = MagicMock()

        result = archive_repo(
            ref=ref,
            client=client,
            clone_url="http://bb/scm/TEST/test-repo.git",
            cache_root=tmp_path / "cache",
            output_path=output,
        )

        assert result.method == "rest_api"
        mock_rest.assert_called_once()

    @patch("vds_bitbucket_orchestrator.repo_ops.clone_repo")
    @patch("vds_bitbucket_orchestrator.repo_ops.download_rest_archive")
    def test_rest_failure_falls_back_to_clone_zip(
        self,
        mock_rest,
        mock_clone,
        ref: RepoRef,
        tmp_path: Path,
    ) -> None:
        output = tmp_path / "out.zip"
        mock_rest.return_value = None  # REST failed

        # Create a fake cloned repo
        clone_dir = tmp_path / "cache" / "repos" / "TEST-project" / "test-repo"
        clone_dir.mkdir(parents=True)
        (clone_dir / ".git").mkdir()
        (clone_dir / "README.md").write_text("hello")
        (clone_dir / ".git" / "config").write_text("gitconfig")

        mock_clone.return_value = MagicMock(path=clone_dir)

        result = archive_repo(
            ref=ref,
            client=MagicMock(),
            clone_url="http://bb/scm/TEST/test-repo.git",
            cache_root=tmp_path / "cache",
            output_path=output,
        )

        assert result.method == "local_zip"
        assert output.exists()
        assert result.size_bytes > 0

    @patch("vds_bitbucket_orchestrator.repo_ops.download_rest_archive")
    def test_include_git_skips_rest(self, mock_rest, ref: RepoRef, tmp_path: Path) -> None:
        """When include_git=True, REST path is skipped since it never includes .git/."""
        output = tmp_path / "out.zip"

        # Create fake repo
        clone_dir = tmp_path / "cache" / "repos" / "TEST-project" / "test-repo"
        clone_dir.mkdir(parents=True)
        (clone_dir / ".git").mkdir()
        (clone_dir / ".git" / "HEAD").write_text("ref: refs/heads/master")
        (clone_dir / "file.txt").write_text("content")

        with patch("vds_bitbucket_orchestrator.repo_ops.clone_repo") as mock_clone:
            mock_clone.return_value = MagicMock(path=clone_dir)

            result = archive_repo(
                ref=ref,
                client=MagicMock(),
                clone_url="http://bb/scm/TEST/test-repo.git",
                cache_root=tmp_path / "cache",
                output_path=output,
                include_git=True,
            )

        mock_rest.assert_not_called()
        assert result.method == "local_zip"
