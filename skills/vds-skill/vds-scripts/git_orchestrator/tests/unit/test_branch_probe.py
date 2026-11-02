"""Tests for vds_git_orchestrator.branch_probe — Phase 4 FR-P2 (TSK-P2.1).

Covers:
- probe_branch_candidates: happy path, partial matches, none found, timeout,
  error, empty URL, unsupported scheme
- probe_branch_hints: HEAD symref parsing, branch discovery, sample limiting,
  timeout, error
- _build_ls_remote_command: auth injection (both set, neither set, partial)
- get_branch_candidates: canonical vs legacy ordering via env var
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from vds_bitbucket_orchestrator.parsers import BitbucketBranchInfo, parse_default_branch
from vds_git_orchestrator.branch_probe import (
    _LEGACY_GIT_ORCHESTRATOR_ORDER,
    BRANCH_CANDIDATES,
    BranchHintResult,
    BranchProbeResult,
    _build_ls_remote_command,
    get_branch_candidates,
    probe_branch_candidates,
    probe_branch_hints,
)

# ---------------------------------------------------------------------------
# Helpers to mock asyncio.create_subprocess_exec
# ---------------------------------------------------------------------------


def _make_mock_process(stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Create a mock async process with given output."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout.encode(), stderr.encode()))
    proc.returncode = returncode
    proc.kill = AsyncMock()
    return proc


# ===================================================================
# _build_ls_remote_command — auth injection tests
# ===================================================================


class TestBuildLsRemoteCommand:
    """Auth injection in _build_ls_remote_command."""

    def test_auth_both_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_USERNAME", "user")
        monkeypatch.setenv("VDS_PASSWORD", "pass")
        cmd = _build_ls_remote_command(remote_url="https://bitbucket/repo.git")
        assert "-c" in cmd
        # Find the config value after -c
        c_idx = cmd.index("-c")
        assert cmd[c_idx + 1].startswith("http.extraHeader=Authorization: Basic ")

    def test_auth_neither_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        cmd = _build_ls_remote_command(remote_url="https://bitbucket/repo.git")
        assert "-c" not in cmd

    def test_auth_partial_only_username(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_USERNAME", "user")
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        cmd = _build_ls_remote_command(remote_url="https://bitbucket/repo.git")
        # Partial credentials should NOT inject auth
        assert "-c" not in cmd

    def test_auth_partial_only_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.setenv("VDS_PASSWORD", "pass")
        cmd = _build_ls_remote_command(remote_url="https://bitbucket/repo.git")
        assert "-c" not in cmd

    def test_branch_candidates_appended(self) -> None:
        cmd = _build_ls_remote_command(
            remote_url="https://bitbucket/repo.git",
            branch_candidates=("main", "release"),
        )
        assert "refs/heads/main" in cmd
        assert "refs/heads/release" in cmd

    def test_symref_flag(self) -> None:
        cmd = _build_ls_remote_command(
            remote_url="https://bitbucket/repo.git",
            include_symref=True,
        )
        assert "--symref" in cmd

    def test_no_symref_by_default(self) -> None:
        cmd = _build_ls_remote_command(remote_url="https://bitbucket/repo.git")
        assert "--symref" not in cmd


# ===================================================================
# probe_branch_candidates tests
# ===================================================================


class TestProbeBranchCandidates:
    """probe_branch_candidates() async probing."""

    @pytest.mark.asyncio
    async def test_happy_path_all_candidates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        stdout = (
            "abc123\trefs/heads/main\n"
            "def456\trefs/heads/release\n"
            "ghi789\trefs/heads/master\n"
            "jkl012\trefs/heads/staging\n"
        )
        proc = _make_mock_process(stdout=stdout)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_candidates("https://bitbucket/repo.git")
        assert result.deterministic is True
        assert result.available_branches == ["main", "release", "master", "staging"]
        assert result.error is None

    @pytest.mark.asyncio
    async def test_partial_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        stdout = "abc123\trefs/heads/release\n"
        proc = _make_mock_process(stdout=stdout)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_candidates("https://bitbucket/repo.git")
        assert result.deterministic is True
        assert result.available_branches == ["release"]

    @pytest.mark.asyncio
    async def test_none_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        proc = _make_mock_process(stdout="")
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_candidates("https://bitbucket/repo.git")
        assert result.deterministic is True
        assert result.available_branches == []

    @pytest.mark.asyncio
    async def test_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        proc = _make_mock_process()
        # First call raises TimeoutError (caught by wait_for handler),
        # second call succeeds (cleanup after process.kill()).
        proc.communicate = AsyncMock(side_effect=[TimeoutError, (b"", b"")])
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_candidates("https://bitbucket/repo.git", timeout=1.0)
        assert result.deterministic is False
        assert result.error == "ls_remote_timeout"

    @pytest.mark.asyncio
    async def test_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        proc = _make_mock_process(stderr="fatal: repo not found", returncode=128)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_candidates("https://bitbucket/repo.git")
        assert result.deterministic is False
        assert "fatal: repo not found" in (result.error or "")

    @pytest.mark.asyncio
    async def test_empty_url(self) -> None:
        result = await probe_branch_candidates("")
        assert result.deterministic is False
        assert result.error == "missing_remote_url"

    @pytest.mark.asyncio
    async def test_unsupported_scheme(self) -> None:
        result = await probe_branch_candidates("ftp://example.com/repo.git")
        assert result.deterministic is False
        assert "unsupported_remote_scheme" in (result.error or "")


# ===================================================================
# probe_branch_hints tests
# ===================================================================


class TestProbeBranchHints:
    """probe_branch_hints() async discovery."""

    @pytest.mark.asyncio
    async def test_symref_head_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        stdout = (
            "ref: refs/heads/main\tHEAD\n"
            "abc123\trefs/heads/main\n"
            "def456\trefs/heads/develop\n"
            "ghi789\trefs/heads/feature/foo\n"
        )
        proc = _make_mock_process(stdout=stdout)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_hints("https://bitbucket/repo.git")
        assert result.deterministic is True
        assert result.default_branch == "main"
        assert "main" in result.discovered_branches
        assert "develop" in result.discovered_branches
        assert result.discovered_branch_count == 3

    @pytest.mark.asyncio
    async def test_sample_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        branches = "\n".join(f"abc{i}\trefs/heads/branch-{i}" for i in range(20))
        proc = _make_mock_process(stdout=branches)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_hints("https://bitbucket/repo.git", sample_limit=3)
        assert len(result.discovered_branches) == 3
        assert result.discovered_branch_count == 20

    @pytest.mark.asyncio
    async def test_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        proc = _make_mock_process()
        proc.communicate = AsyncMock(side_effect=[TimeoutError, (b"", b"")])
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_hints("https://bitbucket/repo.git", timeout=1.0)
        assert result.deterministic is False
        assert result.error == "ls_remote_timeout"

    @pytest.mark.asyncio
    async def test_empty_url(self) -> None:
        result = await probe_branch_hints("")
        assert result.deterministic is False
        assert result.error == "missing_remote_url"

    @pytest.mark.asyncio
    async def test_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        proc = _make_mock_process(stderr="permission denied", returncode=1)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_hints("https://bitbucket/repo.git")
        assert result.deterministic is False
        assert "permission denied" in (result.error or "")

    @pytest.mark.asyncio
    async def test_no_head_symref(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_USERNAME", raising=False)
        monkeypatch.delenv("VDS_PASSWORD", raising=False)
        stdout = "abc123\trefs/heads/main\ndef456\trefs/heads/develop\n"
        proc = _make_mock_process(stdout=stdout)
        with patch("vds_git_orchestrator.branch_probe.asyncio.create_subprocess_exec", return_value=proc):
            result = await probe_branch_hints("https://bitbucket/repo.git")
        assert result.default_branch is None
        assert len(result.discovered_branches) == 2


# ===================================================================
# get_branch_candidates — canonical vs legacy ordering
# ===================================================================


class TestGetBranchCandidates:
    """get_branch_candidates() env var routing."""

    def test_canonical_order_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("VDS_SYNC_BRANCH_ORDER", raising=False)
        assert get_branch_candidates() == BRANCH_CANDIDATES

    def test_legacy_order_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_SYNC_BRANCH_ORDER", "legacy")
        assert get_branch_candidates() == _LEGACY_GIT_ORCHESTRATOR_ORDER

    def test_legacy_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_SYNC_BRANCH_ORDER", "LEGACY")
        assert get_branch_candidates() == _LEGACY_GIT_ORCHESTRATOR_ORDER

    def test_non_legacy_value_returns_canonical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VDS_SYNC_BRANCH_ORDER", "something_else")
        assert get_branch_candidates() == BRANCH_CANDIDATES


# ===================================================================
# Branch order rollback — TSK-P2.5 cross-package contracts
# ===================================================================


class TestBranchOrderRollback:
    """Verify VDS_SYNC_BRANCH_ORDER=legacy preserves pre-Phase-4 behavior per consumer."""

    def test_legacy_order_audit(self) -> None:
        """Audit's pre-Phase-4 order was already main-first (canonical).

        The constant audit now imports (BRANCH_CANDIDATES) must equal the
        canonical order so audit behavior is unchanged regardless of the
        legacy env var.
        """
        assert BRANCH_CANDIDATES == ("main", "release", "master", "staging")

    def test_legacy_order_sync(self) -> None:
        """Sync's pre-Phase-4 sentinel was ``"release"`` (``_DEFAULT_BRANCH``).

        Verify that ``parse_default_branch`` with ``missing_sentinel="release"``
        reproduces the old sync behavior when the Bitbucket API returns no
        default branch.
        """
        result = parse_default_branch({}, missing_sentinel="release")
        assert result == BitbucketBranchInfo(display_id="release", ref=None, missing=True)


# ===================================================================
# Dataclass contracts
# ===================================================================


class TestDataclassContracts:
    """Frozen dataclass immutability."""

    def test_branch_probe_result_frozen(self) -> None:
        result = BranchProbeResult(deterministic=True, available_branches=["main"])
        with pytest.raises(AttributeError):
            result.deterministic = False  # type: ignore[misc]

    def test_branch_hint_result_frozen(self) -> None:
        result = BranchHintResult(deterministic=True, default_branch="main")
        with pytest.raises(AttributeError):
            result.deterministic = False  # type: ignore[misc]
