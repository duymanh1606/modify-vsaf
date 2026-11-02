"""Unit tests for multi-writer instruction sync engine."""

import errno
import json
from pathlib import Path

import pytest
from vds_cli.docs_sync import (
    DocsSyncEngine,
    HttpCentralStateBackend,
    LocalJsonCentralStateBackend,
    SyncConfig,
    SyncError,
    _atomic_write_text,
    _build_backend,
)
from vds_cli.sync_api import (
    ConfluencePropertySyncApiClient,
    SyncApiDocument,
    SyncApiTransientError,
    VdsAiMemorySyncApiClient,
)

from vds_cli import docs_sync


def _write_targets(repo_root: Path, *, agents: str, claude: str, copilot: str) -> None:
    (repo_root / ".github").mkdir(parents=True, exist_ok=True)
    (repo_root / "AGENTS.md").write_text(agents, encoding="utf-8")
    (repo_root / "CLAUDE.md").write_text(claude, encoding="utf-8")
    (repo_root / ".github" / "copilot-instructions.md").write_text(copilot, encoding="utf-8")


def _config(repo_root: Path) -> SyncConfig:
    return SyncConfig(
        repo_root=repo_root,
        reconcile_interval_seconds=60,
        debounce_ms=100,
        log_json=False,
    )


@pytest.mark.parametrize(
    ("edited_relpath", "updated"),
    [
        ("AGENTS.md", "# Shared instructions\n\n- updated from AGENTS\n"),
        ("CLAUDE.md", "# Shared instructions\n\n- updated from CLAUDE\n"),
        (
            ".github/copilot-instructions.md",
            "# Shared instructions\n\n- updated from copilot file\n",
        ),
    ],
)
def test_any_source_file_edit_converges_all_targets(
    tmp_path: Path,
    edited_relpath: str,
    updated: str,
) -> None:
    """Editing any of the 3 source files should converge all targets."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)

    engine = DocsSyncEngine(config=_config(tmp_path))
    startup_result = engine.run_once(reason="startup")
    assert startup_result in {"synced", "fanout", "noop"}

    (tmp_path / edited_relpath).write_text(updated, encoding="utf-8")

    result = engine.run_once(reason="event")
    assert result == "synced"

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == updated
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == updated
    assert (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8") == updated


def test_divergent_local_edits_emit_conflict_artifact(tmp_path: Path) -> None:
    """Divergent concurrent edits should produce conflict artifact and avoid overwrite."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)

    engine = DocsSyncEngine(config=_config(tmp_path))
    engine.run_once(reason="startup")

    agents_update = "# Shared instructions\n\n- AGENTS edit\n"
    claude_update = "# Shared instructions\n\n- CLAUDE edit\n"
    (tmp_path / "AGENTS.md").write_text(agents_update, encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(claude_update, encoding="utf-8")

    result = engine.run_once(reason="event")
    assert result == "conflict"

    conflicts = list((tmp_path / ".vds-sync" / "conflicts").glob(".sync-conflict-*.md"))
    assert conflicts, "Expected conflict artifact file"

    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == agents_update
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == claude_update


def test_watch_backend_auto_prefers_watchfiles_when_available(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Auto backend should select watchfiles when module callable is available."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)
    engine = DocsSyncEngine(config=_config(tmp_path))

    monkeypatch.setattr("vds_cli.docs_sync._load_watchfiles_watch", lambda: lambda *a, **k: iter(()))

    assert engine._resolve_watch_backend() == "watchfiles"


def test_revision_mismatch_non_overlapping_changes_merge_and_sync(tmp_path: Path) -> None:
    """Revision mismatch should auto-merge safely when edits do not overlap."""
    base = "A\nB\nC\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)
    engine = DocsSyncEngine(config=_config(tmp_path))
    engine.run_once(reason="startup")

    backend = engine.backend
    assert isinstance(backend, LocalJsonCentralStateBackend)
    central = backend.pull()
    assert central is not None
    backend.push_if_match(
        content="A\nB_REMOTE\nC\n",
        source_file="AGENTS.md",
        expected_revision=central.revision,
    )

    (tmp_path / "CLAUDE.md").write_text("A\nB\nC_LOCAL\n", encoding="utf-8")
    result = engine.run_once(reason="event")

    assert result == "synced"
    expected = "A\nB_REMOTE\nC_LOCAL\n"
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == expected
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == expected
    assert (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8") == expected


def test_revision_mismatch_conflicting_changes_emits_conflict_artifact(tmp_path: Path) -> None:
    """Revision mismatch with overlapping edits should not auto-merge."""
    base = "A\nB\nC\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)
    engine = DocsSyncEngine(config=_config(tmp_path))
    engine.run_once(reason="startup")

    backend = engine.backend
    assert isinstance(backend, LocalJsonCentralStateBackend)
    central = backend.pull()
    assert central is not None
    backend.push_if_match(
        content="A\nB_REMOTE\nC\n",
        source_file="AGENTS.md",
        expected_revision=central.revision,
    )

    (tmp_path / "CLAUDE.md").write_text("A\nB_LOCAL\nC\n", encoding="utf-8")
    result = engine.run_once(reason="event")
    assert result == "conflict"

    conflicts = list((tmp_path / ".vds-sync" / "conflicts").glob(".sync-conflict-*.md"))
    assert conflicts, "Expected conflict artifact file for unresolved merge"


def test_periodic_reconcile_recovers_when_central_changes_without_local_event(tmp_path: Path) -> None:
    """Periodic reconcile should fan out central changes even without local file-change event."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)

    engine = DocsSyncEngine(config=_config(tmp_path))
    engine.run_once(reason="startup")

    backend = engine.backend
    assert isinstance(backend, LocalJsonCentralStateBackend)
    central = backend.pull()
    assert central is not None

    updated = "# Shared instructions\n\n- central update only\n"
    backend.push_if_match(
        content=updated,
        source_file="AGENTS.md",
        expected_revision=central.revision,
    )

    result = engine.run_once(reason="periodic")
    assert result == "fanout"
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == updated
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == updated
    assert (tmp_path / ".github" / "copilot-instructions.md").read_text(encoding="utf-8") == updated


def test_build_backend_vds_ai_memory_contract_uses_env_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """HTTP backend should resolve concrete VDS AI Memory env contracts."""
    monkeypatch.setenv("VDS_AI_MEMORY_BASE_URL", "https://memory.example")
    monkeypatch.setenv("VDS_AI_MEMORY_API_KEY", "mem-token")
    config = SyncConfig(
        repo_root=tmp_path,
        central_backend="http",
        central_contract="vds-ai-memory",
        central_memory_id="memory-123",
        log_json=False,
    )

    backend = _build_backend(config)
    assert isinstance(backend, HttpCentralStateBackend)
    assert isinstance(backend.client, VdsAiMemorySyncApiClient)
    assert backend.client.base_url == "https://memory.example"
    assert backend.client.memory_id == "memory-123"
    assert backend.client.auth_token == "mem-token"


def test_build_backend_confluence_contract_uses_standard_env_credentials(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Confluence contract should use VDS credential policy from env."""
    monkeypatch.setenv("CONFLUENCE_INTERNAL_URL", "https://confluence.internal")
    monkeypatch.setenv("VDS_USERNAME", "sync-user")
    monkeypatch.setenv("VDS_PASSWORD", "sync-pass")
    config = SyncConfig(
        repo_root=tmp_path,
        central_backend="http",
        central_contract="confluence-property",
        central_confluence_page_id="12345",
        central_confluence_server="internal",
        log_json=False,
    )

    backend = _build_backend(config)
    assert isinstance(backend, HttpCentralStateBackend)
    assert isinstance(backend.client, ConfluencePropertySyncApiClient)
    assert backend.client.base_url == "https://confluence.internal"
    assert backend.client.page_id == "12345"
    assert backend.client.username == "sync-user"


def test_build_backend_vds_ai_memory_contract_requires_memory_id(tmp_path: Path, monkeypatch) -> None:
    """Memory contract must reject missing memory identifiers."""
    monkeypatch.setenv("VDS_AI_MEMORY_BASE_URL", "https://memory.example")
    config = SyncConfig(
        repo_root=tmp_path,
        central_backend="http",
        central_contract="vds-ai-memory",
        log_json=False,
    )

    with pytest.raises(SyncError):
        _build_backend(config)


def test_http_backend_retries_transient_pull_then_succeeds(monkeypatch) -> None:
    """HTTP backend should retry transient pull failures with bounded backoff."""

    class _TransientPullClient:
        def __init__(self) -> None:
            self.calls = 0

        def pull_document(self):
            self.calls += 1
            if self.calls < 3:
                raise SyncApiTransientError("temporary network failure")
            return SyncApiDocument(
                content="canonical",
                revision="3",
                content_hash="abc123",
                source_file="AGENTS.md",
                updated_at="2026-03-01T00:00:00Z",
            )

    delays: list[float] = []
    monkeypatch.setattr(docs_sync.time, "sleep", delays.append)

    backend = HttpCentralStateBackend(
        client=_TransientPullClient(),
        retry_attempts=3,
        retry_base_delay_seconds=0.05,
        retry_max_delay_seconds=0.1,
    )
    document = backend.pull()
    assert document is not None
    assert document.revision == "3"
    assert delays == [0.05, 0.1]


def test_http_backend_exhausts_retry_budget_on_transient_pull(monkeypatch) -> None:
    """HTTP backend should raise SyncError after retry budget is exhausted."""

    class _AlwaysTransientClient:
        def pull_document(self):
            raise SyncApiTransientError("still unavailable")

    monkeypatch.setattr(docs_sync.time, "sleep", lambda _delay: None)
    backend = HttpCentralStateBackend(
        client=_AlwaysTransientClient(),
        retry_attempts=2,
        retry_base_delay_seconds=0.01,
        retry_max_delay_seconds=0.02,
    )

    with pytest.raises(SyncError, match="Failed pulling central state via HTTP"):
        backend.pull()


def test_sync_logs_include_source_hash_and_write_outcomes(tmp_path: Path) -> None:
    """Sync log events should include source hash and fan-out write outcomes."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)
    engine = DocsSyncEngine(config=_config(tmp_path))
    engine.run_once(reason="startup")

    updated = "# Shared instructions\n\n- updated from CLAUDE\n"
    (tmp_path / "CLAUDE.md").write_text(updated, encoding="utf-8")
    result = engine.run_once(reason="event")
    assert result == "synced"

    log_lines = (tmp_path / ".vds-sync" / "watch-agents.log.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in log_lines if line.strip()]
    sync_event = next(
        entry for entry in reversed(entries) if entry.get("event") == "sync" and entry.get("reason") == "event"
    )

    assert sync_event["source_file"] == "CLAUDE.md"
    assert isinstance(sync_event.get("source_hash"), str)
    assert len(sync_event["source_hash"]) == 64
    assert isinstance(sync_event.get("write_outcomes"), dict)
    assert set(sync_event["write_outcomes"].keys()) == set(docs_sync.TARGET_FILES)
    assert "updated" in sync_event["write_outcomes"].values()


def test_atomic_write_retries_windows_style_permission_error(tmp_path: Path, monkeypatch) -> None:
    """Atomic writer should retry transient PermissionError (common on Windows)."""
    target = tmp_path / "AGENTS.md"
    target.write_text("old\n", encoding="utf-8")
    attempts = {"count": 0}
    real_replace = docs_sync.os.replace

    def _flaky_replace(src, dst):
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise PermissionError("Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(docs_sync.os, "replace", _flaky_replace)
    _atomic_write_text(target, "new\n")

    assert target.read_text(encoding="utf-8") == "new\n"
    assert attempts["count"] == 3
    assert list(tmp_path.glob(".AGENTS.md.*.tmp")) == []


def test_atomic_write_retries_posix_eacces_error(tmp_path: Path, monkeypatch) -> None:
    """Atomic writer should retry transient POSIX EACCES replace failures."""
    target = tmp_path / "CLAUDE.md"
    target.write_text("old\n", encoding="utf-8")
    attempts = {"count": 0}
    real_replace = docs_sync.os.replace

    def _flaky_replace(src, dst):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise OSError(errno.EACCES, "Permission denied")
        return real_replace(src, dst)

    monkeypatch.setattr(docs_sync.os, "replace", _flaky_replace)
    _atomic_write_text(target, "line1\r\nline2\r\n")

    assert target.read_bytes() == b"line1\r\nline2\r\n"
    assert attempts["count"] == 2
    assert list(tmp_path.glob(".CLAUDE.md.*.tmp")) == []


def test_atomic_write_cleans_temp_file_after_permanent_failure(tmp_path: Path, monkeypatch) -> None:
    """Atomic writer should not leak temp files when replace fails repeatedly."""
    target = tmp_path / "copilot-instructions.md"
    target.write_text("old\n", encoding="utf-8")

    def _always_fail(src, dst):
        raise PermissionError("still locked")

    monkeypatch.setattr(docs_sync.os, "replace", _always_fail)
    with pytest.raises(PermissionError):
        _atomic_write_text(target, "new\n")

    assert target.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".copilot-instructions.md.*.tmp")) == []


def test_log_write_deadlock_does_not_crash_sync_engine(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    """Sync should keep running when local JSON log sink raises EDEADLK."""
    base = "# Shared instructions\n\n- baseline\n"
    _write_targets(tmp_path, agents=base, claude=base, copilot=base)
    engine = DocsSyncEngine(config=_config(tmp_path))

    original_open = Path.open

    def _patched_open(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        mode = kwargs.get("mode")
        if mode is None and args:
            mode = args[0]
        if self == engine.config.log_path and mode == "a":
            raise OSError(errno.EDEADLK, "Resource deadlock avoided")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _patched_open)

    engine._log("noop", reason="test", conflict_state="none", write_outcomes={})

    captured = capsys.readouterr()
    assert '"event": "log-write-failed"' in captured.err
