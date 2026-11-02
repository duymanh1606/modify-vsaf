"""AGENTS-first sync engine for AGENTS plus legacy mirrored instruction files."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from errno import EACCES, EBUSY, EDEADLK, EPERM
from pathlib import Path
from typing import Protocol, TypeVar

from .sync_api import (
    ConfluencePropertySyncApiClient,
    SyncApiClient,
    SyncApiDocument,
    SyncApiError,
    SyncApiRevisionConflict,
    SyncApiTransientError,
    VdsAiMemorySyncApiClient,
)

WatchBackend = str
_T = TypeVar("_T")

TARGET_FILES: tuple[str, str, str] = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)


class SyncError(RuntimeError):
    """Base error for instruction sync failures."""


class RevisionConflictError(SyncError):
    """Raised when central state revision does not match expected revision."""


@dataclass(frozen=True)
class CentralDocument:
    """Canonical central-state document."""

    content: str
    revision: str
    content_hash: str
    source_file: str
    updated_at: str


class CentralStateBackend(Protocol):
    """Central-state adapter interface."""

    def pull(self) -> CentralDocument | None:
        """Return current canonical document or None when not initialized."""

    def push_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> CentralDocument:
        """Update canonical document using optimistic concurrency semantics."""


@dataclass
class LocalJsonCentralStateBackend:
    """Local JSON-backed central state with If-Match style revision checks."""

    state_path: Path

    def pull(self) -> CentralDocument | None:
        if not self.state_path.exists():
            return None
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        return CentralDocument(
            content=payload["content"],
            revision=str(payload["revision"]),
            content_hash=payload["content_hash"],
            source_file=payload["source_file"],
            updated_at=payload["updated_at"],
        )

    def push_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> CentralDocument:
        current = self.pull()
        if expected_revision is None:
            if current is not None:
                raise RevisionConflictError(f"Expected empty central state but found revision {current.revision}.")
        elif current is None or current.revision != expected_revision:
            actual = current.revision if current else "<missing>"
            raise RevisionConflictError(f"Central revision mismatch (expected={expected_revision}, actual={actual}).")

        revision = "1" if current is None else str(int(current.revision) + 1)
        now = datetime.now(UTC).isoformat()
        payload = {
            "content": content,
            "revision": revision,
            "content_hash": _sha256(content),
            "source_file": source_file,
            "updated_at": now,
        }
        _write_json_atomic(self.state_path, payload)
        return CentralDocument(
            content=payload["content"],
            revision=payload["revision"],
            content_hash=payload["content_hash"],
            source_file=payload["source_file"],
            updated_at=payload["updated_at"],
        )


@dataclass
class HttpCentralStateBackend:
    """HTTP-backed central state with optimistic concurrency semantics."""

    client: SyncApiClient
    retry_attempts: int = 3
    retry_base_delay_seconds: float = 0.2
    retry_max_delay_seconds: float = 1.0

    def pull(self) -> CentralDocument | None:
        try:
            document = self._retry_transient_errors("pull", self.client.pull_document)
        except SyncApiError as exc:
            raise SyncError(f"Failed pulling central state via HTTP: {exc}") from exc
        if document is None:
            return None
        return _as_central_document(document)

    def push_if_match(
        self,
        *,
        content: str,
        source_file: str,
        expected_revision: str | None,
    ) -> CentralDocument:
        try:
            document = self._retry_transient_errors(
                "push",
                lambda: self.client.push_document_if_match(
                    content=content,
                    source_file=source_file,
                    expected_revision=expected_revision,
                ),
            )
        except SyncApiRevisionConflict as exc:
            raise RevisionConflictError(str(exc)) from exc
        except SyncApiError as exc:
            raise SyncError(f"Failed pushing central state via HTTP: {exc}") from exc
        return _as_central_document(document)

    def _retry_transient_errors(self, operation: str, request_fn: Callable[[], _T]) -> _T:
        attempts = max(self.retry_attempts, 1)
        for attempt in range(1, attempts + 1):
            try:
                return request_fn()
            except SyncApiTransientError:
                if attempt >= attempts:
                    raise
                delay = min(
                    self.retry_base_delay_seconds * (2 ** (attempt - 1)),
                    self.retry_max_delay_seconds,
                )
                time.sleep(delay)
            except SyncApiRevisionConflict:
                raise
        raise SyncError(f"Unexpected retry state for operation '{operation}'.")


@dataclass
class SyncLedger:
    """Local sync ledger for incremental conflict detection."""

    last_revision: str | None = None
    last_source_file: str | None = None
    file_hashes: dict[str, str] = field(default_factory=dict)
    synced_hash: str | None = None
    synced_content: str | None = None

    @classmethod
    def load(cls, path: Path) -> SyncLedger:
        if not path.exists():
            return cls()
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            last_revision=payload.get("last_revision"),
            last_source_file=payload.get("last_source_file"),
            file_hashes=dict(payload.get("file_hashes", {})),
            synced_hash=payload.get("synced_hash"),
            synced_content=payload.get("synced_content"),
        )

    def save(self, path: Path) -> None:
        payload = {
            "last_revision": self.last_revision,
            "last_source_file": self.last_source_file,
            "file_hashes": self.file_hashes,
            "synced_hash": self.synced_hash,
            "synced_content": self.synced_content,
        }
        _write_json_atomic(path, payload)


@dataclass(frozen=True)
class SyncConfig:
    """Runtime configuration for watch-agents sync."""

    repo_root: Path
    target_files: tuple[str, str, str] = TARGET_FILES
    workspace_dirname: str = ".vds-sync"
    reconcile_interval_seconds: int = 300
    debounce_ms: int = 500
    watch_backend: WatchBackend = "auto"
    central_backend: str = "local"
    central_contract: str = "generic"
    central_state_url: str | None = None
    central_timeout_seconds: int = 10
    central_auth_token: str | None = None
    central_memory_id: str | None = None
    central_user_id: str = "vds-sync-agent"
    central_session_id: str = "vds-sync-session"
    central_confluence_server: str = "internal"
    central_confluence_page_id: str | None = None
    central_confluence_property_key: str = "vds_sync_instructions"
    dry_run: bool = False
    log_json: bool = True
    lock_stale_seconds: int = 900
    lock_timeout_seconds: int = 5
    conflict_dir: Path | None = None

    @property
    def sync_dir(self) -> Path:
        return self.repo_root / self.workspace_dirname

    @property
    def central_state_path(self) -> Path:
        return self.sync_dir / "instructions-central-state.json"

    @property
    def ledger_path(self) -> Path:
        return self.sync_dir / "watch-agents-ledger.json"

    @property
    def lock_path(self) -> Path:
        return self.sync_dir / "watch-agents.lock"

    @property
    def log_path(self) -> Path:
        return self.sync_dir / "watch-agents.log.jsonl"

    @property
    def resolved_conflict_dir(self) -> Path:
        return self.conflict_dir if self.conflict_dir is not None else self.sync_dir / "conflicts"


@dataclass(frozen=True)
class FileSnapshot:
    """Snapshot of one target file."""

    relpath: str
    abspath: Path
    content: str
    content_hash: str
    mtime: float


@dataclass(frozen=True)
class LineEdit:
    """A line-range replacement edit for conservative three-way merge."""

    start: int
    end: int
    replacement: tuple[str, ...]


class SyncFileLock:
    """Simple cross-platform lock-file with stale lock eviction."""

    def __init__(self, path: Path, *, stale_seconds: int, timeout_seconds: int) -> None:
        self.path = path
        self.stale_seconds = stale_seconds
        self.timeout_seconds = timeout_seconds

    def __enter__(self) -> SyncFileLock:
        deadline = time.time() + self.timeout_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)

        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    payload = {
                        "pid": os.getpid(),
                        "created_at": time.time(),
                    }
                    os.write(fd, json.dumps(payload).encode("utf-8"))
                finally:
                    os.close(fd)
                return self
            except FileExistsError:
                if self._is_stale():
                    self.path.unlink(missing_ok=True)
                    continue
                if time.time() > deadline:
                    raise SyncError(f"Could not acquire lock: {self.path}") from None
                time.sleep(0.1)

    def __exit__(self, *_args: object) -> None:
        self.path.unlink(missing_ok=True)

    def _is_stale(self) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            created_at = float(payload.get("created_at", 0))
        except (json.JSONDecodeError, OSError, ValueError):
            return True
        return (time.time() - created_at) > self.stale_seconds


class DocsSyncEngine:
    """Core multi-writer reconciliation engine."""

    def __init__(self, *, config: SyncConfig, backend: CentralStateBackend | None = None) -> None:
        self.config = config
        self.backend = backend or _build_backend(config)
        self.ledger = SyncLedger.load(config.ledger_path)

    def run_once(self, *, reason: str) -> str:
        snapshots = self._collect_snapshots()
        central = self.backend.pull()

        if self._needs_startup_strategy(central):
            return self._startup_reconcile(snapshots=snapshots, central=central, reason=reason)

        return self._steady_state_reconcile(snapshots=snapshots, central=central, reason=reason)

    def watch(self, *, once: bool = False) -> None:
        with SyncFileLock(
            self.config.lock_path,
            stale_seconds=self.config.lock_stale_seconds,
            timeout_seconds=self.config.lock_timeout_seconds,
        ):
            self.run_once(reason="startup")
            if once:
                return

            watch_backend = self._resolve_watch_backend()
            self._log("watch-backend-selected", backend=watch_backend)
            if watch_backend == "watchfiles":
                self._watch_loop_watchfiles()
                return
            self._watch_loop_polling()

    def _watch_loop_polling(self) -> None:
        last_periodic = time.monotonic()
        previous_hashes = self._snapshot_hash_map(self._collect_snapshots())

        while True:
            time.sleep(max(self.config.debounce_ms / 1000.0, 0.2))

            current = self._collect_snapshots()
            current_hashes = self._snapshot_hash_map(current)
            if current_hashes != previous_hashes:
                self.run_once(reason="event")
                previous_hashes = self._snapshot_hash_map(self._collect_snapshots())

            now = time.monotonic()
            if now - last_periodic >= self.config.reconcile_interval_seconds:
                self.run_once(reason="periodic")
                previous_hashes = self._snapshot_hash_map(self._collect_snapshots())
                last_periodic = now

    def _watch_loop_watchfiles(self) -> None:
        watch = _load_watchfiles_watch()
        if watch is None:
            raise SyncError("watch_backend='watchfiles' requested but 'watchfiles' package is not installed.")

        last_periodic = time.monotonic()
        target_files = {(self.config.repo_root / relpath).resolve() for relpath in self.config.target_files}
        rust_timeout_ms = max(200, min(self.config.debounce_ms, 2000))

        for changes in watch(
            self.config.repo_root,
            recursive=True,
            debounce=self.config.debounce_ms,
            yield_on_timeout=True,
            rust_timeout=rust_timeout_ms,
        ):
            has_target_change = False
            for _change, changed_path in changes:
                try:
                    resolved = Path(changed_path).resolve()
                except OSError:
                    continue
                if resolved in target_files:
                    has_target_change = True
                    break

            if has_target_change:
                self.run_once(reason="event")

            now = time.monotonic()
            if now - last_periodic >= self.config.reconcile_interval_seconds:
                self.run_once(reason="periodic")
                last_periodic = now

    def _resolve_watch_backend(self) -> WatchBackend:
        configured = self.config.watch_backend.lower().strip()
        if configured not in {"auto", "watchfiles", "polling"}:
            raise SyncError(
                f"Invalid watch backend '{self.config.watch_backend}'. Expected: auto, watchfiles, polling."
            )
        if configured == "polling":
            return "polling"
        if configured == "watchfiles":
            if _load_watchfiles_watch() is None:
                raise SyncError("watch_backend='watchfiles' requested but 'watchfiles' package is not installed.")
            return "watchfiles"
        if _load_watchfiles_watch() is not None:
            return "watchfiles"
        return "polling"

    def _startup_reconcile(
        self,
        *,
        snapshots: dict[str, FileSnapshot],
        central: CentralDocument | None,
        reason: str,
    ) -> str:
        local_hashes = {rel: snap.content_hash for rel, snap in snapshots.items()}
        unique_hashes = set(local_hashes.values())

        if central is None:
            source = self._select_local_source_without_baseline(snapshots)
            if source is None:
                artifact = self._write_conflict_artifact(
                    reason="startup-local-conflict",
                    snapshots=snapshots,
                    central=central,
                )
                self._log(
                    "conflict",
                    reason=reason,
                    artifact=str(artifact),
                    conflict_state="artifact-written",
                    write_outcomes={},
                )
                return "conflict"
            canonical = self.backend.push_if_match(
                content=snapshots[source].content,
                source_file=source,
                expected_revision=None,
            )
            write_outcomes = self._fan_out(
                canonical.content,
                canonical_hash=canonical.content_hash,
            )
            self._update_ledger(canonical=canonical)
            self._log(
                "sync",
                reason=reason,
                source_file=source,
                source_hash=snapshots[source].content_hash,
                revision=canonical.revision,
                conflict_state="none",
                write_outcomes=write_outcomes,
            )
            return "synced"

        if len(unique_hashes) == 1:
            only_hash = next(iter(unique_hashes))
            if only_hash == central.content_hash:
                self._update_ledger(canonical=central)
                self._log(
                    "noop",
                    reason=reason,
                    source_file=central.source_file,
                    source_hash=central.content_hash,
                    revision=central.revision,
                    conflict_state="none",
                    write_outcomes={},
                )
                return "noop"
            write_outcomes = self._fan_out(
                central.content,
                canonical_hash=central.content_hash,
            )
            self._update_ledger(canonical=central)
            self._log(
                "fanout",
                reason=reason,
                source_file=central.source_file,
                source_hash=central.content_hash,
                revision=central.revision,
                conflict_state="none",
                write_outcomes=write_outcomes,
            )
            return "fanout"

        source = self._select_single_modified_candidate(snapshots, baseline_hash=central.content_hash)
        if source is None:
            artifact = self._write_conflict_artifact(
                reason="startup-divergent-local-state",
                snapshots=snapshots,
                central=central,
            )
            self._log(
                "conflict",
                reason=reason,
                artifact=str(artifact),
                revision=central.revision,
                conflict_state="artifact-written",
                write_outcomes={},
            )
            return "conflict"

        try:
            canonical = self.backend.push_if_match(
                content=snapshots[source].content,
                source_file=source,
                expected_revision=central.revision,
            )
        except RevisionConflictError:
            retried = self._retry_with_safe_merge(
                source=source,
                local_content=snapshots[source].content,
                reason=f"{reason}:startup-central-revision-conflict",
            )
            if retried is not None:
                write_outcomes = self._fan_out(
                    retried.content,
                    canonical_hash=retried.content_hash,
                )
                self._update_ledger(canonical=retried)
                self._log(
                    "sync-merge-retry",
                    reason=reason,
                    source_file=source,
                    source_hash=snapshots[source].content_hash,
                    revision=retried.revision,
                    conflict_state="merge-applied",
                    write_outcomes=write_outcomes,
                )
                return "synced"
            artifact = self._write_conflict_artifact(
                reason="startup-central-revision-conflict",
                snapshots=snapshots,
                central=self.backend.pull(),
            )
            self._log(
                "conflict",
                reason=reason,
                artifact=str(artifact),
                source_file=source,
                source_hash=snapshots[source].content_hash,
                conflict_state="artifact-written",
                write_outcomes={},
            )
            return "conflict"

        write_outcomes = self._fan_out(
            canonical.content,
            canonical_hash=canonical.content_hash,
        )
        self._update_ledger(canonical=canonical)
        self._log(
            "sync",
            reason=reason,
            source_file=source,
            source_hash=snapshots[source].content_hash,
            revision=canonical.revision,
            conflict_state="none",
            write_outcomes=write_outcomes,
        )
        return "synced"

    def _steady_state_reconcile(
        self,
        *,
        snapshots: dict[str, FileSnapshot],
        central: CentralDocument | None,
        reason: str,
    ) -> str:
        changed = [rel for rel, snap in snapshots.items() if self.ledger.file_hashes.get(rel) != snap.content_hash]

        if not changed:
            if central and any(s.content_hash != central.content_hash for s in snapshots.values()):
                write_outcomes = self._fan_out(
                    central.content,
                    canonical_hash=central.content_hash,
                )
                self._update_ledger(canonical=central)
                self._log(
                    "fanout",
                    reason=reason,
                    source_file=central.source_file,
                    source_hash=central.content_hash,
                    revision=central.revision,
                    conflict_state="none",
                    write_outcomes=write_outcomes,
                )
                return "fanout"
            self._log("noop", reason=reason, conflict_state="none", write_outcomes={})
            return "noop"

        distinct_hashes = {snapshots[rel].content_hash for rel in changed}
        if len(changed) > 1 and len(distinct_hashes) > 1:
            artifact = self._write_conflict_artifact(
                reason="divergent-local-edits",
                snapshots=snapshots,
                central=central,
            )
            self._log(
                "conflict",
                reason=reason,
                artifact=str(artifact),
                conflict_state="artifact-written",
                write_outcomes={},
            )
            return "conflict"

        source = changed[0]
        expected_revision = self.ledger.last_revision or (central.revision if central else None)
        if expected_revision is None:
            expected_revision = None

        try:
            canonical = self.backend.push_if_match(
                content=snapshots[source].content,
                source_file=source,
                expected_revision=expected_revision,
            )
        except RevisionConflictError:
            retried = self._retry_with_safe_merge(
                source=source,
                local_content=snapshots[source].content,
                reason=f"{reason}:central-revision-mismatch",
            )
            if retried is not None:
                write_outcomes = self._fan_out(
                    retried.content,
                    canonical_hash=retried.content_hash,
                )
                self._update_ledger(canonical=retried)
                self._log(
                    "sync-merge-retry",
                    reason=reason,
                    source_file=source,
                    source_hash=snapshots[source].content_hash,
                    revision=retried.revision,
                    conflict_state="merge-applied",
                    write_outcomes=write_outcomes,
                )
                return "synced"
            artifact = self._write_conflict_artifact(
                reason="central-revision-mismatch",
                snapshots=snapshots,
                central=self.backend.pull(),
            )
            self._log(
                "conflict",
                reason=reason,
                artifact=str(artifact),
                source_file=source,
                source_hash=snapshots[source].content_hash,
                conflict_state="artifact-written",
                write_outcomes={},
            )
            return "conflict"

        write_outcomes = self._fan_out(
            canonical.content,
            canonical_hash=canonical.content_hash,
        )
        self._update_ledger(canonical=canonical)
        self._log(
            "sync",
            reason=reason,
            source_file=source,
            source_hash=snapshots[source].content_hash,
            revision=canonical.revision,
            conflict_state="none",
            write_outcomes=write_outcomes,
        )
        return "synced"

    def _collect_snapshots(self) -> dict[str, FileSnapshot]:
        snapshots: dict[str, FileSnapshot] = {}
        for relpath in self.config.target_files:
            abspath = self.config.repo_root / relpath
            if not abspath.exists():
                raise SyncError(f"Missing required file for sync: {abspath}")
            content = abspath.read_text(encoding="utf-8")
            stat = abspath.stat()
            snapshots[relpath] = FileSnapshot(
                relpath=relpath,
                abspath=abspath,
                content=content,
                content_hash=_sha256(content),
                mtime=stat.st_mtime,
            )
        return snapshots

    def _fan_out(self, content: str, *, canonical_hash: str) -> dict[str, str]:
        outcomes: dict[str, str] = {}
        for relpath in self.config.target_files:
            path = self.config.repo_root / relpath
            current = path.read_text(encoding="utf-8")
            if _sha256(current) == canonical_hash:
                outcomes[relpath] = "unchanged"
                continue
            if self.config.dry_run:
                outcomes[relpath] = "dry-run-skip"
                continue
            _atomic_write_text(path, content)
            outcomes[relpath] = "updated"
        return outcomes

    def _update_ledger(self, *, canonical: CentralDocument) -> None:
        snapshots = self._collect_snapshots()
        self.ledger.last_revision = canonical.revision
        self.ledger.last_source_file = canonical.source_file
        self.ledger.synced_hash = canonical.content_hash
        self.ledger.synced_content = canonical.content
        self.ledger.file_hashes = {rel: snap.content_hash for rel, snap in snapshots.items()}
        if not self.config.dry_run:
            self.config.sync_dir.mkdir(parents=True, exist_ok=True)
            self.ledger.save(self.config.ledger_path)

    def _write_conflict_artifact(
        self,
        *,
        reason: str,
        snapshots: dict[str, FileSnapshot],
        central: CentralDocument | None,
    ) -> Path:
        conflict_dir = self.config.resolved_conflict_dir
        conflict_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        artifact = conflict_dir / f".sync-conflict-{ts}.md"

        lines = [
            "# Sync Conflict",
            "",
            f"- reason: {reason}",
            f"- timestamp_utc: {datetime.now(UTC).isoformat()}",
            f"- central_revision: {central.revision if central else '<none>'}",
            f"- central_hash: {central.content_hash if central else '<none>'}",
            "",
            "## Local Hashes",
        ]
        for relpath in self.config.target_files:
            lines.append(f"- {relpath}: {snapshots[relpath].content_hash}")

        lines.extend(
            [
                "",
                "## Next Actions",
                "- Resolve conflicting edits manually.",
                "- Re-run `vds-cli docs watch-agents --once --repo-root <repo>` after resolution.",
            ]
        )

        _atomic_write_text(artifact, "\n".join(lines) + "\n")
        return artifact

    def _needs_startup_strategy(self, central: CentralDocument | None) -> bool:
        if not self.ledger.file_hashes:
            return True
        return bool(central and self.ledger.last_revision is None)

    def _snapshot_hash_map(self, snapshots: dict[str, FileSnapshot]) -> dict[str, str]:
        return {rel: snap.content_hash for rel, snap in snapshots.items()}

    def _select_local_source_without_baseline(self, snapshots: dict[str, FileSnapshot]) -> str | None:
        hashes = {rel: snap.content_hash for rel, snap in snapshots.items()}
        groups = _hash_groups(hashes)
        if len(groups) == 1:
            return self.config.target_files[0]
        if len(groups) == 2:
            newest = max(snapshots.values(), key=lambda item: item.mtime)
            return newest.relpath
        return None

    def _select_single_modified_candidate(
        self,
        snapshots: dict[str, FileSnapshot],
        *,
        baseline_hash: str,
    ) -> str | None:
        non_baseline = [rel for rel, snap in snapshots.items() if snap.content_hash != baseline_hash]
        if len(non_baseline) == 1:
            return non_baseline[0]
        return None

    def _retry_with_safe_merge(
        self,
        *,
        source: str,
        local_content: str,
        reason: str,
    ) -> CentralDocument | None:
        latest = self.backend.pull()
        if latest is None:
            return None
        merged = self._safe_three_way_merge(
            base_content=self.ledger.synced_content,
            local_content=local_content,
            remote_content=latest.content,
        )
        if merged is None:
            return None
        try:
            canonical = self.backend.push_if_match(
                content=merged,
                source_file=source,
                expected_revision=latest.revision,
            )
        except RevisionConflictError:
            return None
        self._log(
            "merge-retry-applied",
            reason=reason,
            source_file=source,
            source_hash=_sha256(local_content),
            base_revision=self.ledger.last_revision,
            remote_revision=latest.revision,
            merged_revision=canonical.revision,
            conflict_state="merge-applied",
        )
        return canonical

    def _safe_three_way_merge(
        self,
        *,
        base_content: str | None,
        local_content: str,
        remote_content: str,
    ) -> str | None:
        if base_content is None:
            return None
        if local_content == remote_content:
            return local_content
        if local_content == base_content:
            return remote_content
        if remote_content == base_content:
            return local_content

        base_lines = base_content.splitlines(keepends=True)
        local_edits = _line_edits(base_lines, local_content.splitlines(keepends=True))
        remote_edits = _line_edits(base_lines, remote_content.splitlines(keepends=True))

        merged_edits: list[LineEdit] = []
        for edit in [*local_edits, *remote_edits]:
            if any(
                existing.start == edit.start and existing.end == edit.end and existing.replacement == edit.replacement
                for existing in merged_edits
            ):
                continue
            merged_edits.append(edit)

        for index, left in enumerate(merged_edits):
            for right in merged_edits[index + 1 :]:
                if _edits_conflict(left, right):
                    return None

        merged = list(base_lines)
        for edit in sorted(merged_edits, key=lambda item: (item.start, item.end), reverse=True):
            merged[edit.start : edit.end] = list(edit.replacement)
        return "".join(merged)

    def _log(self, event: str, **fields: object) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=True)
        if self.config.log_json:
            print(line)
        self.config.sync_dir.mkdir(parents=True, exist_ok=True)
        for attempt in range(4):
            try:
                with self.config.log_path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
                return
            except OSError as exc:
                if exc.errno in {EDEADLK, EBUSY, EACCES, EPERM} and attempt < 3:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                # Do not crash sync loop because of local log sink write failures.
                print(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "event": "log-write-failed",
                            "error": str(exc),
                            "log_path": str(self.config.log_path),
                        },
                        ensure_ascii=True,
                    ),
                    file=sys.stderr,
                )
                return


def find_repo_root(start: Path) -> Path:
    """Find repository root by walking up until AGENTS and mirrored instruction files exist."""
    current = start.resolve()
    while True:
        if all((current / relpath).exists() for relpath in TARGET_FILES):
            return current
        if current.parent == current:
            raise SyncError(
                "Could not locate repository root containing AGENTS.md plus mirrored legacy instruction files "
                "(CLAUDE.md and .github/copilot-instructions.md)"
            )
        current = current.parent


def run_watch_agents(
    *,
    repo_root: Path,
    reconcile_interval_seconds: int,
    debounce_ms: int,
    watch_backend: WatchBackend,
    central_backend: str,
    central_contract: str,
    central_state_url: str | None,
    central_timeout_seconds: int,
    central_auth_token: str | None,
    central_memory_id: str | None,
    central_user_id: str,
    central_session_id: str,
    central_confluence_server: str,
    central_confluence_page_id: str | None,
    central_confluence_property_key: str,
    dry_run: bool,
    conflict_dir: Path | None,
    log_json: bool,
    once: bool,
) -> None:
    """Run the watch-agents command with resolved config."""
    resolved_root = find_repo_root(repo_root)
    config = SyncConfig(
        repo_root=resolved_root,
        reconcile_interval_seconds=reconcile_interval_seconds,
        debounce_ms=debounce_ms,
        watch_backend=watch_backend,
        central_backend=central_backend,
        central_contract=central_contract,
        central_state_url=central_state_url,
        central_timeout_seconds=central_timeout_seconds,
        central_auth_token=central_auth_token,
        central_memory_id=central_memory_id,
        central_user_id=central_user_id,
        central_session_id=central_session_id,
        central_confluence_server=central_confluence_server,
        central_confluence_page_id=central_confluence_page_id,
        central_confluence_property_key=central_confluence_property_key,
        dry_run=dry_run,
        conflict_dir=conflict_dir,
        log_json=log_json,
    )
    engine = DocsSyncEngine(config=config)
    engine.watch(once=once)


def _build_backend(config: SyncConfig) -> CentralStateBackend:
    backend = config.central_backend.lower().strip()
    if backend == "local":
        return LocalJsonCentralStateBackend(config.central_state_path)
    if backend == "http":
        contract = config.central_contract.lower().strip()
        if contract == "generic":
            if not config.central_state_url:
                raise SyncError("central_contract='generic' requires --central-state-url.")
            return HttpCentralStateBackend(
                client=SyncApiClient(
                    endpoint=config.central_state_url,
                    timeout_seconds=config.central_timeout_seconds,
                    auth_token=config.central_auth_token,
                )
            )
        if contract == "vds-ai-memory":
            base_url = config.central_state_url or os.getenv("VDS_AI_MEMORY_BASE_URL")
            if not base_url:
                raise SyncError(
                    "central_contract='vds-ai-memory' requires --central-state-url or VDS_AI_MEMORY_BASE_URL."
                )
            memory_id = config.central_memory_id
            if not memory_id:
                raise SyncError("central_contract='vds-ai-memory' requires --central-memory-id.")
            auth_token = config.central_auth_token or os.getenv("VDS_AI_MEMORY_API_KEY")
            return HttpCentralStateBackend(
                client=VdsAiMemorySyncApiClient(
                    base_url=base_url,
                    memory_id=memory_id,
                    user_id=config.central_user_id,
                    session_id=config.central_session_id,
                    timeout_seconds=config.central_timeout_seconds,
                    auth_token=auth_token,
                )
            )
        if contract == "confluence-property":
            page_id = config.central_confluence_page_id
            if not page_id:
                raise SyncError("central_contract='confluence-property' requires --central-confluence-page-id.")
            base_url = _resolve_confluence_base_url(
                server=config.central_confluence_server,
                override=config.central_state_url,
            )
            auth_token = _resolve_confluence_token(
                server=config.central_confluence_server,
                explicit_token=config.central_auth_token,
            )
            username = os.getenv("VDS_USERNAME")
            password = os.getenv("VDS_PASSWORD")
            if not auth_token and not (username and password):
                raise SyncError(
                    "Confluence credentials missing. Provide VDS_USERNAME+VDS_PASSWORD or "
                    "INTERNAL_CONFLUENCE_TOKEN/EXTERNAL_CONFLUENCE_TOKEN (or --central-auth-token)."
                )
            return HttpCentralStateBackend(
                client=ConfluencePropertySyncApiClient(
                    base_url=base_url,
                    page_id=page_id,
                    property_key=config.central_confluence_property_key,
                    timeout_seconds=config.central_timeout_seconds,
                    auth_token=auth_token,
                    username=username,
                    password=password,
                )
            )
        raise SyncError(
            "Invalid central contract for HTTP backend. Expected: generic, vds-ai-memory, confluence-property."
        )
    raise SyncError(f"Invalid central backend '{config.central_backend}'. Expected: local, http.")


def _resolve_confluence_base_url(*, server: str, override: str | None) -> str:
    if override:
        return override
    server_lower = server.lower().strip()
    if server_lower in {"internal", "int", "main"}:
        return os.getenv("CONFLUENCE_INTERNAL_URL", "http://confluence.digital.vn")
    if server_lower in {"external", "ext", "outsource"}:
        return os.getenv("CONFLUENCE_EXTERNAL_URL", "http://10.254.136.35:8090")
    raise SyncError(f"Unknown confluence server '{server}'. Expected internal or external.")


def _resolve_confluence_token(*, server: str, explicit_token: str | None) -> str | None:
    if explicit_token:
        return explicit_token
    server_lower = server.lower().strip()
    if server_lower in {"internal", "int", "main"}:
        return os.getenv("INTERNAL_CONFLUENCE_TOKEN")
    if server_lower in {"external", "ext", "outsource"}:
        return os.getenv("EXTERNAL_CONFLUENCE_TOKEN")
    return None


def _sha256(content: str) -> str:
    import hashlib

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _hash_groups(hashes: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for relpath, digest in hashes.items():
        grouped.setdefault(digest, []).append(relpath)
    return grouped


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
            temp_path = Path(fh.name)

        for attempt in range(4):
            try:
                os.replace(temp_path, path)
                return
            except OSError as exc:
                if not _is_retryable_replace_error(exc) or attempt >= 3:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _is_retryable_replace_error(exc: OSError) -> bool:
    if isinstance(exc, PermissionError):
        return True
    return exc.errno in {EACCES, EPERM, EBUSY}


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def _as_central_document(document: SyncApiDocument) -> CentralDocument:
    return CentralDocument(
        content=document.content,
        revision=document.revision,
        content_hash=document.content_hash,
        source_file=document.source_file,
        updated_at=document.updated_at,
    )


def _load_watchfiles_watch():
    try:
        from watchfiles import watch  # type: ignore
    except ModuleNotFoundError:
        return None
    return watch


def _line_edits(base_lines: list[str], target_lines: list[str]) -> list[LineEdit]:
    edits: list[LineEdit] = []
    matcher = SequenceMatcher(a=base_lines, b=target_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        edits.append(LineEdit(start=i1, end=i2, replacement=tuple(target_lines[j1:j2])))
    return edits


def _edits_conflict(left: LineEdit, right: LineEdit) -> bool:
    if left.start == right.start and left.end == right.end and left.replacement == right.replacement:
        return False

    left_insert = left.start == left.end
    right_insert = right.start == right.end

    if left_insert and right_insert:
        return left.start == right.start
    if left_insert:
        return right.start <= left.start < right.end
    if right_insert:
        return left.start <= right.start < left.end

    return not (left.end <= right.start or right.end <= left.start)
