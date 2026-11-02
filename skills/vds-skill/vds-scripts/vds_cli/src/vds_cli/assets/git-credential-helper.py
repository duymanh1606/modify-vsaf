#!/usr/bin/env python3
"""Git credential helper for VDS workflows.

Canonical install path: $HOME/.vds/bin/git-credential-vds
Canonical source: WHO-project/vds-scripts/vds_cli/src/vds_cli/assets/git-credential-helper.py

Spec: who-ecosystem-alignment Phase 5 — FR-20 (host-filtered emission),
      FR-21 (lockout-prevention with cooldown state file), FR-25 (logic
      non-overlap policy).

Per FR-25 AC-25.1, this helper MUST NOT import from any path requiring the
vds-scripts venv to be active. Git invokes it in a bare shell context with
no venv activation; even stdlib-only modules inside venv-installed packages
are unreachable. Stdlib-only imports are enforced by a unit test in
vds_cli/tests/test_git_credential_helper.py.

Per FR-25 AC-25.2, the dotenv parsing logic below is a deliberate duplicate
of vds_cli_common.env._parse_env_file (see
vds_cli_common/src/vds_cli_common/env.py:23-42). The token-vs-basic
preference logic is a deliberate duplicate of
BitbucketSettings.auth_attempts (see
bitbucket_orchestrator/src/vds_bitbucket_orchestrator/config.py).

Git speaks HTTP basic auth and nothing else, so this helper emits the
username-plus-token shape. That is also the shape Bitbucket Server accepts,
and the reason auth_attempts falls back to it after a Bearer 401. Audited
under AC-25.4 when that fallback was added: no change was needed here.

Both duplications are required by the no-venv constraint and are kept in
sync per AC-25.4: PRs touching either source-of-truth MUST audit and update
this file in the same change.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# AC-21.5: thresholds are module-level constants, NOT env-configurable, to keep
# the operator surface narrow. Power users may edit these directly if absolutely
# required, but the default 3 / 60s / 300s is tuned for Bitbucket DC.
FAILURE_THRESHOLD = 3
FAILURE_WINDOW_SEC = 60
COOLDOWN_SEC = 300

# AC-21.7: state file mode. Mandatory.
STATE_FILE_MODE = 0o600

# Default host allowlist per FR-20 AC-20.1. Extensible via VDS_BITBUCKET_HOSTS
# in ~/.vds/.env (NEVER from shell env, per AC-20.6).
ALLOWLIST_DEFAULT = frozenset({"bitbucket.digital.vn"})


def _home() -> Path:
    """Resolve HOME — git invokes the helper with HOME set in the environment."""
    return Path(os.environ.get("HOME", str(Path.home())))


def _env_file() -> Path:
    return _home() / ".vds" / ".env"


def _state_file() -> Path:
    return _home() / ".vds" / ".git-credential-helper-cooldown.json"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Stdlib-only dotenv parser. Mirrors vds_cli_common.env._parse_env_file."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def _is_configured(value: str | None) -> bool:
    """AC-19.5: configured iff non-empty after whitespace strip."""
    return bool(value and value.strip())


def _read_stdin_kv() -> dict[str, str]:
    """Read git's key=value stdin protocol."""
    info: dict[str, str] = {}
    try:
        data = sys.stdin.read()
    except Exception:
        return info
    for line in data.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip()] = v.strip()
    return info


def _allowlist(env: dict[str, str]) -> frozenset[str]:
    """AC-20.6: read VDS_BITBUCKET_HOSTS ONLY from env file dict, never shell env."""
    extra = env.get("VDS_BITBUCKET_HOSTS", "").strip()
    hosts = set(ALLOWLIST_DEFAULT)
    if extra:
        hosts.update(h.strip() for h in extra.split(",") if h.strip())
    return frozenset(hosts)


def _load_state() -> dict:
    """AC-21.4: state file is human-inspectable JSON. Returns empty if missing/malformed."""
    path = _state_file()
    if not path.exists():
        return {"failures": [], "cooldown_until": 0}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"failures": [], "cooldown_until": 0}


def _save_state(state: dict) -> None:
    """AC-21.7: write state file with mode 0600. Best-effort (AC-21 silent on failure)."""
    path = _state_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
        os.chmod(path, STATE_FILE_MODE)
    except OSError:
        pass


def _in_cooldown(state: dict, now: float) -> bool:
    return float(state.get("cooldown_until", 0)) > now


def _record_failure(state: dict, now: float) -> dict:
    """Append failure timestamp; trip cooldown if threshold met within window."""
    failures = [float(t) for t in state.get("failures", []) if now - float(t) <= FAILURE_WINDOW_SEC]
    failures.append(now)
    if len(failures) >= FAILURE_THRESHOLD:
        return {"failures": [], "cooldown_until": now + COOLDOWN_SEC}
    return {"failures": failures, "cooldown_until": float(state.get("cooldown_until", 0))}


def _reset_state() -> dict:
    return {"failures": [], "cooldown_until": 0}


def _emit(username: str, password: str) -> None:
    """AC-20.5: ONLY username= and password= to stdout. No stderr, no logs."""
    sys.stdout.write(f"username={username}\n")
    sys.stdout.write(f"password={password}\n")


def cmd_get() -> int:
    git_info = _read_stdin_kv()
    host = git_info.get("host", "")

    file_env = _parse_env_file(_env_file())
    allowed = _allowlist(file_env)

    # FR-20 AC-20.1+AC-20.2: silent fall-through for non-allowlisted hosts.
    if host not in allowed:
        return 0

    state = _load_state()
    now = time.time()
    if _in_cooldown(state, now):
        # AC-21.6: stderr notice with INTEGER countdown only — no credential content.
        # This is the sole permitted stderr emission per AC-20.5 carve-out.
        remaining = int(float(state["cooldown_until"]) - now)
        sys.stderr.write(f"in cooldown until {remaining}s — falling through to other helpers\n")
        return 0

    # AC-19.5 + AC-20.3 + AC-25.2: token preferred over basic when both configured
    # (whitespace-stripped). Mirrors the basic-with-token entry of
    # BitbucketSettings.auth_attempts.
    username = file_env.get("VDS_USERNAME", "").strip()
    token = file_env.get("BITBUCKET_TOKEN", "").strip()
    password = file_env.get("VDS_PASSWORD", "").strip()

    if _is_configured(username) and _is_configured(token):
        _emit(username, token)
        return 0
    if _is_configured(username) and _is_configured(password):
        _emit(username, password)
        return 0
    return 1  # no creds configured → let git prompt user


def cmd_erase() -> int:
    """Git rejected creds. Record failure for cooldown tracking (FR-21)."""
    git_info = _read_stdin_kv()
    host = git_info.get("host", "")
    file_env = _parse_env_file(_env_file())
    if host in _allowlist(file_env):
        state = _record_failure(_load_state(), time.time())
        _save_state(state)
    return 0


def cmd_store() -> int:
    """Git accepted creds. Reset cooldown state (AC-21.3)."""
    git_info = _read_stdin_kv()
    host = git_info.get("host", "")
    file_env = _parse_env_file(_env_file())
    if host in _allowlist(file_env):
        _save_state(_reset_state())
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    action = sys.argv[1]
    if action == "get":
        return cmd_get()
    if action == "erase":
        return cmd_erase()
    if action == "store":
        return cmd_store()
    return 0


if __name__ == "__main__":
    sys.exit(main())
