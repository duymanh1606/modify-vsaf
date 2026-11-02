"""Tests for repo_ops URL parsing, clone URL building, and default paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from vds_bitbucket_orchestrator.repo_ops import (
    RepoRef,
    build_clone_url,
    default_clone_dir,
    parse_repo_identifier,
)


class TestParseRepoIdentifier:
    """URL parsing for all supported formats."""

    @pytest.mark.parametrize(
        "identifier,expected_project,expected_repo,expected_format",
        [
            # Shorthand
            ("INSURANCE-AI/ntbh-tech-standards", "INSURANCE-AI", "ntbh-tech-standards", "shorthand"),
            ("TEST/repo", "TEST", "repo", "shorthand"),
            ("my-project/my.repo", "my-project", "my.repo", "shorthand"),
            # Browse URL
            (
                "http://bitbucket.digital.vn/projects/INSURANCE-AI/repos/ntbh-tech-standards/browse",
                "INSURANCE-AI",
                "ntbh-tech-standards",
                "browse_url",
            ),
            (
                "https://bb.vn/projects/PAR/repos/merchant-billing/browse?at=refs%2Fheads%2Fmaster",
                "PAR",
                "merchant-billing",
                "browse_url",
            ),
            # Clone URL
            (
                "http://bitbucket.digital.vn/scm/INSURANCE-AI/ntbh-tech-standards.git",
                "INSURANCE-AI",
                "ntbh-tech-standards",
                "clone_url",
            ),
            (
                "https://bb.vn/scm/PAR/merchant-report.git",
                "PAR",
                "merchant-report",
                "clone_url",
            ),
            # Clone URL without .git suffix
            (
                "http://bb.vn/scm/TEST/repo",
                "TEST",
                "repo",
                "clone_url",
            ),
            # SSH URL
            (
                "ssh://git@bitbucket.digital.vn/INSURANCE-AI/ntbh-tech-standards.git",
                "INSURANCE-AI",
                "ntbh-tech-standards",
                "ssh_url",
            ),
            # SSH with port
            (
                "ssh://git@bb.vn:7999/PAR/merchant-billing.git",
                "PAR",
                "merchant-billing",
                "ssh_url",
            ),
        ],
    )
    def test_valid_identifiers(
        self,
        identifier: str,
        expected_project: str,
        expected_repo: str,
        expected_format: str,
    ) -> None:
        ref = parse_repo_identifier(identifier)
        assert ref.project_key == expected_project
        assert ref.repo_slug == expected_repo
        assert ref.source_format == expected_format

    def test_strips_whitespace(self) -> None:
        ref = parse_repo_identifier("  TEST/repo  ")
        assert ref.project_key == "TEST"
        assert ref.repo_slug == "repo"

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "not-a-valid-identifier",
            "",
            "   ",
            "http://example.com/random/path",
            "just-a-word",
            "/leading/slash",
        ],
    )
    def test_invalid_identifiers(self, invalid_input: str) -> None:
        with pytest.raises(ValueError, match="Cannot parse repository identifier"):
            parse_repo_identifier(invalid_input)


class TestBuildCloneUrl:
    """Clone URL construction with auth injection."""

    def test_with_token(self) -> None:
        ref = RepoRef(project_key="TEST", repo_slug="repo", source_format="shorthand")
        url = build_clone_url(ref, "http://bitbucket.digital.vn", token="mytoken")
        assert url == "http://x-token-auth:mytoken@bitbucket.digital.vn/scm/TEST/repo.git"

    def test_with_username(self) -> None:
        ref = RepoRef(project_key="TEST", repo_slug="repo", source_format="shorthand")
        url = build_clone_url(ref, "http://bitbucket.digital.vn", username="admin")
        assert url == "http://admin@bitbucket.digital.vn/scm/TEST/repo.git"

    def test_no_auth(self) -> None:
        ref = RepoRef(project_key="TEST", repo_slug="repo", source_format="shorthand")
        url = build_clone_url(ref, "http://bitbucket.digital.vn")
        assert url == "http://bitbucket.digital.vn/scm/TEST/repo.git"

    def test_https_scheme(self) -> None:
        ref = RepoRef(project_key="PRJ", repo_slug="my-repo", source_format="shorthand")
        url = build_clone_url(ref, "https://bb.example.com", token="tok")
        assert url == "https://x-token-auth:tok@bb.example.com/scm/PRJ/my-repo.git"

    def test_token_takes_precedence_over_username(self) -> None:
        ref = RepoRef(project_key="TEST", repo_slug="repo", source_format="shorthand")
        url = build_clone_url(ref, "http://bb.vn", username="admin", token="tok")
        assert "x-token-auth:tok@" in url
        assert "admin" not in url


class TestDefaultCloneDir:
    """Standard VDS cache path for cloned repos."""

    def test_standard_path(self) -> None:
        ref = RepoRef(project_key="INSURANCE-AI", repo_slug="ntbh-tech-standards", source_format="shorthand")
        result = default_clone_dir(ref, Path("/home/user/.vds/cache"))
        assert result == Path("/home/user/.vds/cache/repos/INSURANCE-AI-project/ntbh-tech-standards")

    def test_different_project(self) -> None:
        ref = RepoRef(project_key="PAR", repo_slug="merchant-billing", source_format="browse_url")
        result = default_clone_dir(ref, Path("/tmp/cache"))
        assert result == Path("/tmp/cache/repos/PAR-project/merchant-billing")
