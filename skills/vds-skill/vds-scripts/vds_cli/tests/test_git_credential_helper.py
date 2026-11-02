"""Unit tests for the canonical git credential helper.

Spec: who-ecosystem-alignment Phase 5 v0.7.0 — TSK-5.22.

Per AC-25.1 the helper must NOT be importable in a venv-requiring way; tests
invoke it via subprocess.run (NEVER via import) so the test runtime mirrors
git's bare-shell invocation context.

Each test sets HOME to tmp_path via subprocess env, so the helper reads the
test's tmp .vds/.env rather than the developer's real one (avoids flakiness).
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ASSET_PATH = Path(__file__).parent.parent / "src" / "vds_cli" / "assets" / "git-credential-helper.py"


def _run(
    action: str, stdin: str, home: Path, *, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the helper as git would, with HOME isolated to tmp."""
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(ASSET_PATH), action],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


def _write_env(home: Path, content: str) -> None:
    env_dir = home / ".vds"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text(content, encoding="utf-8")


def _read_state(home: Path) -> dict:
    state_file = home / ".vds" / ".git-credential-helper-cooldown.json"
    return json.loads(state_file.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# (a) AC-20.1, AC-20.2 — allowlist-miss returns no output, exit 0
# ---------------------------------------------------------------------------
def test_a_allowlist_miss_returns_no_output(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    result = _run("get", "protocol=https\nhost=github.com\n\n", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# (b) AC-20.3, FR-19 — token preferred over basic when both present
# ---------------------------------------------------------------------------
def test_b_token_preference_over_basic(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=user\nVDS_PASSWORD=basicpw\nBITBUCKET_TOKEN=tokenval\n")
    result = _run("get", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    assert result.returncode == 0
    assert "username=user\n" in result.stdout
    assert "password=tokenval\n" in result.stdout
    assert "basicpw" not in result.stdout


# ---------------------------------------------------------------------------
# (c) AC-21.1 — erase increments failures
# ---------------------------------------------------------------------------
def test_c_erase_increments_failures(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    _run("erase", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    state = _read_state(tmp_path)
    assert len(state["failures"]) == 1


# ---------------------------------------------------------------------------
# (d) AC-21.2 — 3 failures in 60s triggers cooldown
# ---------------------------------------------------------------------------
def test_d_three_failures_trigger_cooldown(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    for _ in range(3):
        _run("erase", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    state = _read_state(tmp_path)
    assert state["cooldown_until"] > time.time()
    assert state["failures"] == []


# ---------------------------------------------------------------------------
# (e) AC-21.3 — store resets state
# ---------------------------------------------------------------------------
def test_e_store_resets_state(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    for _ in range(3):
        _run("erase", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    _run("store", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    state = _read_state(tmp_path)
    assert state["cooldown_until"] == 0
    assert state["failures"] == []


# ---------------------------------------------------------------------------
# (f) AC-20.4 — dotenv parser handles export, quotes, comments, blank lines
# ---------------------------------------------------------------------------
def test_f_dotenv_variants(tmp_path: Path) -> None:
    content = (
        "# leading comment\n"
        "\n"
        "export VDS_USERNAME=quser\n"
        "VDS_PASSWORD='single-quoted'\n"
        'BITBUCKET_TOKEN="double-quoted-tok"\n'
        "# trailing comment\n"
    )
    _write_env(tmp_path, content)
    result = _run("get", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    assert result.returncode == 0
    assert "username=quser\n" in result.stdout
    assert "password=double-quoted-tok\n" in result.stdout  # token wins over basic


# ---------------------------------------------------------------------------
# (g) AC-20.5, NFR-12 — stderr never contains credential substrings
# ---------------------------------------------------------------------------
def test_g_no_stderr_credential_disclosure(tmp_path: Path) -> None:
    secret_pw = "supersecret-pw-XYZ-7777"
    secret_tok = "tok-leak-canary-9999"
    _write_env(tmp_path, f"VDS_USERNAME=u\nVDS_PASSWORD={secret_pw}\nBITBUCKET_TOKEN={secret_tok}\n")
    result = _run("get", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    assert result.returncode == 0
    assert secret_pw not in result.stderr
    assert secret_tok not in result.stderr


# ---------------------------------------------------------------------------
# (h) AC-21.4 — state file is human-inspectable JSON with correct schema
# ---------------------------------------------------------------------------
def test_h_state_file_schema(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    for _ in range(3):
        _run("erase", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    state = _read_state(tmp_path)
    assert "cooldown_until" in state
    assert "failures" in state
    assert isinstance(state["failures"], list)
    assert isinstance(state["cooldown_until"], (int, float))


# ---------------------------------------------------------------------------
# (i) AC-21.6 — cooldown stderr notice matches r"in cooldown until \d+s"
# ---------------------------------------------------------------------------
def test_i_cooldown_stderr_notice_format(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    # Pre-populate cooldown state
    state_file = tmp_path / ".vds" / ".git-credential-helper-cooldown.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"failures": [], "cooldown_until": time.time() + 240}))
    result = _run("get", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""  # cooldown means silent fall-through
    assert re.search(r"in cooldown until \d+s", result.stderr) is not None


# ---------------------------------------------------------------------------
# (j) AC-25.1 — every Import/ImportFrom resolves to a stdlib module
# ---------------------------------------------------------------------------
def test_j_stdlib_only_imports() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    non_stdlib: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in sys.stdlib_module_names:
                    non_stdlib.append(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top not in sys.stdlib_module_names:
                non_stdlib.append(top)
    assert non_stdlib == [], f"Helper imports non-stdlib modules: {non_stdlib}"


# ---------------------------------------------------------------------------
# (k) AC-25.5 — module docstring present and cites FR-25
# ---------------------------------------------------------------------------
def test_k_module_docstring_cites_fr25() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree)
    assert docstring is not None and docstring.strip(), "Helper missing module docstring"
    assert "FR-25" in docstring, f"Module docstring must cite FR-25; got: {docstring[:200]}..."


# ---------------------------------------------------------------------------
# (l) AC-21.7 — state file mode is 0o600 after a write
# ---------------------------------------------------------------------------
def test_l_state_file_mode_0600(tmp_path: Path) -> None:
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    _run("erase", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    state_file = tmp_path / ".vds" / ".git-credential-helper-cooldown.json"
    mode = state_file.stat().st_mode & 0o777
    assert mode == 0o600, f"State file mode should be 0o600, got {oct(mode)}"


# ---------------------------------------------------------------------------
# (m) AC-19.5 — whitespace-only token treated as absent (basic-auth fallback)
# ---------------------------------------------------------------------------
def test_m_whitespace_token_treated_as_absent(tmp_path: Path) -> None:
    _write_env(tmp_path, 'VDS_USERNAME=u\nVDS_PASSWORD=basicpw\nBITBUCKET_TOKEN="   "\n')
    result = _run("get", "protocol=https\nhost=bitbucket.digital.vn\n\n", tmp_path)
    assert result.returncode == 0
    # Whitespace token is treated as absent; helper falls back to basic auth.
    assert "password=basicpw\n" in result.stdout


# ---------------------------------------------------------------------------
# (n) AC-20.6 — VDS_BITBUCKET_HOSTS only honored from .env, never shell env
# ---------------------------------------------------------------------------
def test_n_allowlist_only_from_env_file(tmp_path: Path) -> None:
    # .env does NOT extend allowlist
    _write_env(tmp_path, "VDS_USERNAME=u\nVDS_PASSWORD=p\n")
    # Shell env attempts to extend — must be ignored
    result = _run(
        "get",
        "protocol=https\nhost=evil.example.com\n\n",
        tmp_path,
        extra_env={"VDS_BITBUCKET_HOSTS": "evil.example.com"},
    )
    assert result.returncode == 0
    assert result.stdout == "", "Helper must NOT read VDS_BITBUCKET_HOSTS from shell env"
