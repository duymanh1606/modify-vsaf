"""Tests for vds_bitbucket_orchestrator.parsers — Phase 4 FR-P1 (TSK-P1.1).

Covers:
- HTTP clone URL extraction (happy path, SSH fallback, missing links)
- Default branch parsing (dict-style, string-style, missing with sentinel,
  custom sentinel value, empty dict displayId)
"""

from __future__ import annotations

import pytest
from vds_bitbucket_orchestrator.parsers import (
    BitbucketBranchInfo,
    parse_clone_url,
    parse_default_branch,
)

# ---------------------------------------------------------------------------
# Fixtures — representative Bitbucket Server REST API response shapes
# ---------------------------------------------------------------------------


def _repo_dict(
    *,
    clone_links: list[dict] | None = None,
    default_branch: dict | str | None = "UNSET",
) -> dict:
    """Build a minimal Bitbucket repo dict for tests."""
    d: dict = {"slug": "my-repo", "project": {"key": "PROJ"}}
    if clone_links is not None:
        d["links"] = {"clone": clone_links}
    if default_branch != "UNSET" and default_branch is not None:
        d["defaultBranch"] = default_branch
    return d


# ===================================================================
# parse_clone_url tests
# ===================================================================


class TestParseCloneUrl:
    """parse_clone_url() extraction from links.clone array."""

    def test_http_clone_url(self) -> None:
        repo = _repo_dict(
            clone_links=[
                {"name": "ssh", "href": "ssh://git@bitbucket/proj/repo.git"},
                {"name": "http", "href": "https://bitbucket/scm/proj/repo.git"},
            ],
        )
        assert parse_clone_url(repo) == "https://bitbucket/scm/proj/repo.git"

    def test_ssh_fallback_when_no_http(self) -> None:
        repo = _repo_dict(
            clone_links=[
                {"name": "ssh", "href": "ssh://git@bitbucket/proj/repo.git"},
            ],
        )
        assert parse_clone_url(repo) == "ssh://git@bitbucket/proj/repo.git"

    def test_missing_links_returns_none(self) -> None:
        repo = _repo_dict(clone_links=None)
        assert parse_clone_url(repo) is None

    def test_empty_clone_list(self) -> None:
        repo = _repo_dict(clone_links=[])
        assert parse_clone_url(repo) is None

    def test_clone_entry_with_empty_href(self) -> None:
        repo = _repo_dict(
            clone_links=[
                {"name": "http", "href": ""},
                {"name": "ssh", "href": "ssh://git@bitbucket/proj/repo.git"},
            ],
        )
        # Empty http href → falls back to SSH
        assert parse_clone_url(repo) == "ssh://git@bitbucket/proj/repo.git"

    def test_clone_entry_missing_href_key(self) -> None:
        repo = _repo_dict(clone_links=[{"name": "http"}])
        assert parse_clone_url(repo) is None

    def test_http_preferred_over_ssh(self) -> None:
        repo = _repo_dict(
            clone_links=[
                {"name": "http", "href": "https://bitbucket/scm/proj/repo.git"},
                {"name": "ssh", "href": "ssh://git@bitbucket/proj/repo.git"},
            ],
        )
        assert parse_clone_url(repo) == "https://bitbucket/scm/proj/repo.git"

    def test_links_key_is_none(self) -> None:
        repo: dict = {"slug": "r", "links": None}
        assert parse_clone_url(repo) is None

    def test_clone_key_is_none(self) -> None:
        repo: dict = {"slug": "r", "links": {"clone": None}}
        assert parse_clone_url(repo) is None

    def test_name_case_insensitive(self) -> None:
        repo = _repo_dict(
            clone_links=[
                {"name": "HTTP", "href": "https://bitbucket/scm/proj/repo.git"},
            ],
        )
        assert parse_clone_url(repo) == "https://bitbucket/scm/proj/repo.git"


# ===================================================================
# parse_default_branch tests
# ===================================================================


class TestParseDefaultBranchDictStyle:
    """defaultBranch is a dict (most common Bitbucket Server response)."""

    def test_dict_with_display_id_and_ref(self) -> None:
        repo = _repo_dict(
            default_branch={
                "displayId": "release",
                "id": "refs/heads/release",
                "latestCommit": "abc123",
            },
        )
        info = parse_default_branch(repo)
        assert info == BitbucketBranchInfo(
            display_id="release",
            ref="refs/heads/release",
            missing=False,
        )

    def test_dict_with_display_id_no_id_falls_back_to_latest_commit(self) -> None:
        repo = _repo_dict(
            default_branch={
                "displayId": "main",
                "latestCommit": "refs/heads/main",
            },
        )
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.ref == "refs/heads/main"
        assert info.missing is False

    def test_dict_with_empty_display_id_returns_missing(self) -> None:
        repo = _repo_dict(
            default_branch={"displayId": "", "id": "refs/heads/something"},
        )
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.ref == "refs/heads/something"
        assert info.missing is True

    def test_dict_with_none_display_id_returns_missing(self) -> None:
        repo = _repo_dict(
            default_branch={"displayId": None, "id": None},
        )
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.ref is None
        assert info.missing is True

    def test_empty_dict_returns_missing(self) -> None:
        repo = _repo_dict(default_branch={})
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.ref is None
        assert info.missing is True


class TestParseDefaultBranchStringStyle:
    """defaultBranch is a plain string."""

    def test_string_branch_name(self) -> None:
        repo = _repo_dict(default_branch="develop")
        info = parse_default_branch(repo)
        assert info == BitbucketBranchInfo(
            display_id="develop",
            ref=None,
            missing=False,
        )

    def test_string_with_whitespace(self) -> None:
        repo = _repo_dict(default_branch="  main  ")
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.missing is False

    def test_empty_string_returns_missing(self) -> None:
        repo = _repo_dict(default_branch="")
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.missing is True

    def test_whitespace_only_string_returns_missing(self) -> None:
        repo = _repo_dict(default_branch="   ")
        info = parse_default_branch(repo)
        assert info.display_id == "main"
        assert info.missing is True


class TestParseDefaultBranchMissing:
    """defaultBranch is absent or None."""

    def test_no_default_branch_key(self) -> None:
        repo: dict = {"slug": "r"}
        info = parse_default_branch(repo)
        assert info == BitbucketBranchInfo(
            display_id="main",
            ref=None,
            missing=True,
        )

    def test_default_branch_is_none(self) -> None:
        repo = _repo_dict(default_branch=None)
        info = parse_default_branch(repo)
        assert info.missing is True
        assert info.display_id == "main"


class TestParseDefaultBranchCustomSentinel:
    """Custom missing_sentinel parameter."""

    def test_custom_sentinel_release(self) -> None:
        repo: dict = {"slug": "r"}
        info = parse_default_branch(repo, missing_sentinel="release")
        assert info.display_id == "release"
        assert info.missing is True

    def test_custom_sentinel_not_used_when_branch_present(self) -> None:
        repo = _repo_dict(default_branch="develop")
        info = parse_default_branch(repo, missing_sentinel="release")
        assert info.display_id == "develop"
        assert info.missing is False


class TestBitbucketBranchInfoFrozen:
    """BitbucketBranchInfo immutability contract."""

    def test_frozen_dataclass(self) -> None:
        info = BitbucketBranchInfo(display_id="main", ref=None, missing=False)
        with pytest.raises(AttributeError):
            info.display_id = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = BitbucketBranchInfo(display_id="main", ref=None, missing=True)
        b = BitbucketBranchInfo(display_id="main", ref=None, missing=True)
        assert a == b

    def test_hashable(self) -> None:
        info = BitbucketBranchInfo(display_id="main", ref=None, missing=False)
        assert hash(info) is not None
        # Can be used in sets/dicts
        assert info in {info}
