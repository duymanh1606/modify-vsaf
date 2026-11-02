"""Lifecycle tests for vds_cli.env_git_helper.

Spec: who-ecosystem-alignment Phase 5 v0.7.0 — TSK-5.27.

Per .claude/rules/common/testing.md, no real `git config --global` mutations.
Mock boundaries explicit (NOT generic 'subprocess mocking'):
- `subprocess.run` patched at module level for git config + self-probe
- `pathlib.Path.home` monkeypatched for filesystem isolation
- All file ops happen inside tmp_path
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from vds_cli import env_git_helper as egh


class MockSubprocessRun:
    """Records subprocess.run calls; routes by command shape."""

    def __init__(self, git_config_value: str = "") -> None:
        self.calls: list[tuple[list[str], dict]] = []
        self.git_config_value = git_config_value

    def __call__(self, args, **kwargs) -> subprocess.CompletedProcess:
        self.calls.append((list(args), dict(kwargs)))
        # `git config --global --get credential.helper` → return configured value
        if isinstance(args, list) and "config" in args and "--get" in args:
            stdout = (self.git_config_value + "\n") if self.git_config_value else ""
            rc = 0 if self.git_config_value else 1
            return subprocess.CompletedProcess(args=args, returncode=rc, stdout=stdout, stderr="")
        # Self-probe (helper invocation): pretend allowlist-miss success
        if isinstance(args, list) and args and str(args[0]).endswith("git-credential-vds"):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")
        # Default: success
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


@pytest.fixture
def mock_run(monkeypatch: pytest.MonkeyPatch) -> MockSubprocessRun:
    runner = MockSubprocessRun()
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", runner)
    return runner


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    (tmp_path / ".vds").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _matching_signature_content() -> str:
    """Pre-FR-24 helper signature per AC-24.6 (contains VDS_USERNAME + def cmd_get)."""
    return "# legacy helper\nimport os\ndef cmd_get():\n    return os.environ.get('VDS_USERNAME')\n"


# ---------------------------------------------------------------------------
# (a) AC-23.2(e), AC-24.4 — install removes pre-FR-24 file artifacts
# ---------------------------------------------------------------------------
def test_a_install_removes_pre_fr24_artifacts(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    # Place stub artifacts that match the AC-24.6 signature
    legacy_main = fake_home / ".vds" / "git_credential_helper.py"
    legacy_bak = fake_home / ".vds" / "git_credential_helper.py.bak"
    legacy_main.write_text(_matching_signature_content(), encoding="utf-8")
    legacy_bak.write_text(_matching_signature_content(), encoding="utf-8")

    result = egh.install()

    assert not legacy_main.exists(), "Should remove signature-matching .py legacy"
    assert not legacy_bak.exists(), "Should remove signature-matching .bak legacy"
    assert legacy_main in result.removed
    assert legacy_bak in result.removed


# ---------------------------------------------------------------------------
# (b) AC-24.6 — install preserves user-authored file (signature mismatch)
# ---------------------------------------------------------------------------
def test_b_install_preserves_user_file_when_signature_mismatch(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    user_file = fake_home / ".vds" / "git_credential_helper.py"
    user_file.write_text("# my unrelated script\nprint('hello')\n", encoding="utf-8")

    result = egh.install()

    assert user_file.exists(), "User file MUST be preserved when signature mismatches"
    assert user_file in result.preserved
    assert user_file not in result.removed


# ---------------------------------------------------------------------------
# (c) AC-24.5 — install migrates legacy state file
# ---------------------------------------------------------------------------
def test_c_install_migrates_legacy_state_file(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    legacy_state = fake_home / ".vds" / ".git_helper_state.json"
    new_state = fake_home / ".vds" / ".git-credential-helper-cooldown.json"
    payload = {"failures": [1234.5, 1235.0], "cooldown_until": 0}
    legacy_state.write_text(json.dumps(payload), encoding="utf-8")

    result = egh.install()

    assert not legacy_state.exists(), "Legacy state must be removed after migration"
    assert new_state.exists(), "New state must exist after migration"
    assert json.loads(new_state.read_text()) == payload
    assert result.migrated_state == new_state


# ---------------------------------------------------------------------------
# (d) AC-23.7 — install creates ~/.vds/bin/ with mode 0o700
# ---------------------------------------------------------------------------
def test_d_install_creates_bin_dir_with_0700(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    egh.install()
    bin_dir = fake_home / ".vds" / "bin"
    assert bin_dir.is_dir()
    mode = bin_dir.stat().st_mode & 0o777
    assert mode == 0o700, f"~/.vds/bin/ mode must be 0o700, got {oct(mode)}"


# ---------------------------------------------------------------------------
# (e) AC-23.7 — installed binary is mode 0o700, NOT 0o755
# ---------------------------------------------------------------------------
def test_e_install_binary_is_0700(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    result = egh.install()
    assert result.target.exists()
    mode = result.target.stat().st_mode & 0o777
    assert mode == 0o700, f"Installed binary mode must be 0o700, got {oct(mode)}"


# ---------------------------------------------------------------------------
# (f) AC-23.8 — all subprocess.run calls in install use shell=False with list args
# ---------------------------------------------------------------------------
def test_f_install_uses_shell_false_and_list_args(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    egh.install()
    assert mock_run.calls, "install must invoke subprocess.run at least once"
    for args, kwargs in mock_run.calls:
        assert isinstance(args, list), f"args must be list, got {type(args).__name__}: {args}"
        assert kwargs.get("shell", False) is False, f"shell must be False, got {kwargs.get('shell')!r}"


# ---------------------------------------------------------------------------
# (g) AC-23.3 — verify exit 0 on clean install
# ---------------------------------------------------------------------------
def test_g_verify_exit_0_on_clean_install(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    egh.install.__wrapped__ if hasattr(egh.install, "__wrapped__") else None
    # First install (with mock_run for the install step)
    install_runner = MockSubprocessRun()
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", install_runner)
    result = egh.install()
    # Now swap to a verify-mock that reports the correct configured path
    verify_runner = MockSubprocessRun(git_config_value=str(result.target.resolve()))
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", verify_runner)

    exit_code, checks = egh.verify()
    assert exit_code == 0, f"verify should pass; checks: {checks}"
    assert all(c.ok for c in checks)


# ---------------------------------------------------------------------------
# (h) AC-23.3 — verify exit 1 when git config points to wrong path
# ---------------------------------------------------------------------------
def test_h_verify_exit_1_on_wrong_git_config(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_runner = MockSubprocessRun()
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", install_runner)
    egh.install()
    # git config points to a different unrelated helper
    bad_runner = MockSubprocessRun(git_config_value="/usr/local/bin/something-else")
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", bad_runner)

    exit_code, checks = egh.verify()
    assert exit_code == 1
    assert any(c.name == "Git config" and not c.ok for c in checks)


# ---------------------------------------------------------------------------
# (i) AC-23.3 — verify exit 1 when binary is non-executable
# ---------------------------------------------------------------------------
def test_i_verify_exit_1_on_non_executable_binary(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_runner = MockSubprocessRun()
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", install_runner)
    result = egh.install()
    # Strip exec bits
    import os as _os

    _os.chmod(result.target, 0o644)
    runner = MockSubprocessRun(git_config_value=str(result.target.resolve()))
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", runner)

    exit_code, checks = egh.verify()
    assert exit_code == 1
    assert any(c.name == "Executable" and not c.ok for c in checks)


# ---------------------------------------------------------------------------
# (j) AC-21.4 + AC-23.3 — verify --reset-cooldown clears state file
# ---------------------------------------------------------------------------
def test_j_verify_reset_cooldown_clears_state(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    state_file = fake_home / ".vds" / ".git-credential-helper-cooldown.json"
    state_file.write_text(
        json.dumps({"failures": [1.0, 2.0, 3.0], "cooldown_until": 9_999_999_999}),
        encoding="utf-8",
    )
    runner = MockSubprocessRun()
    monkeypatch.setattr("vds_cli.env_git_helper.subprocess.run", runner)

    _exit_code, checks = egh.verify(reset_cooldown=True)

    cleared = json.loads(state_file.read_text())
    assert cleared == {"failures": [], "cooldown_until": 0}
    assert any(c.name == "Cooldown reset" and c.ok for c in checks)


# ---------------------------------------------------------------------------
# (k) AC-23.4 — remove is idempotent when nothing is installed
# ---------------------------------------------------------------------------
def test_k_remove_idempotent_when_nothing_installed(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    # No install — bin dir missing entirely
    result = egh.remove()
    assert result["deleted_binary"] is False
    assert result["deleted_state"] is False
    # No exception raised → success


# ---------------------------------------------------------------------------
# (l) AC-23.4 — remove --purge deletes state file
# ---------------------------------------------------------------------------
def test_l_remove_purge_deletes_state_file(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    state_file = fake_home / ".vds" / ".git-credential-helper-cooldown.json"
    state_file.write_text(json.dumps({"failures": [], "cooldown_until": 0}), encoding="utf-8")

    result = egh.remove(purge=True)

    assert not state_file.exists(), "State file must be deleted by --purge"
    assert result["deleted_state"] is True


# ---------------------------------------------------------------------------
# (m) AC-23.5 — status() reports installed/missing/broken correctly
# ---------------------------------------------------------------------------
def test_m_status_reports_three_states(fake_home: Path, mock_run: MockSubprocessRun) -> None:
    # Missing: nothing installed
    state, hint = egh.status()
    assert state == "missing"
    assert "vds-cli env install-git-helper" in hint

    # Installed: install + check
    egh.install()
    state, hint = egh.status()
    assert state == "installed"
    assert hint == ""

    # Broken: chmod 0o644
    import os as _os

    _os.chmod(fake_home / ".vds" / "bin" / "git-credential-vds", 0o644)
    state, hint = egh.status()
    assert state == "broken"
    assert "vds-cli env install-git-helper" in hint
