"""Tests for vds_git_orchestrator.protocols — Phase 4 FR-P4 (TSK-P3.1).

Covers:
- SyncableRepo protocol structural matching via isinstance
- Rejection of objects missing required properties
- Package-level re-export equivalence
"""

from __future__ import annotations

from typing import Any

from vds_git_orchestrator.protocols import SyncableRepo


class _CompleteSyncable:
    """Minimal concrete class satisfying all 5 SyncableRepo properties."""

    @property
    def name(self) -> str:
        return "test-repo"

    @property
    def project(self) -> str:
        return "INSURANCE"

    @property
    def branch(self) -> str:
        return "main"

    @property
    def url(self) -> str | None:
        return "https://bitbucket.example.com/scm/ins/test-repo.git"

    @property
    def sync_metadata(self) -> dict[str, Any]:
        return {"preserve_local_path": True}


class _NoneUrlSyncable(_CompleteSyncable):
    """Variant where url returns None (valid per protocol)."""

    @property
    def url(self) -> str | None:
        return None


class _MissingName:
    """Object missing the 'name' property."""

    @property
    def project(self) -> str:
        return "P"

    @property
    def branch(self) -> str:
        return "main"

    @property
    def url(self) -> str | None:
        return None

    @property
    def sync_metadata(self) -> dict[str, Any]:
        return {}


class _MissingSyncMetadata:
    """Object missing the 'sync_metadata' property."""

    @property
    def name(self) -> str:
        return "r"

    @property
    def project(self) -> str:
        return "P"

    @property
    def branch(self) -> str:
        return "main"

    @property
    def url(self) -> str | None:
        return None


class TestSyncableRepoProtocol:
    """Verify SyncableRepo structural matching via isinstance."""

    def test_complete_object_satisfies_protocol(self) -> None:
        obj = _CompleteSyncable()
        assert isinstance(obj, SyncableRepo)

    def test_none_url_satisfies_protocol(self) -> None:
        obj = _NoneUrlSyncable()
        assert isinstance(obj, SyncableRepo)

    def test_property_values_accessible(self) -> None:
        obj = _CompleteSyncable()
        assert obj.name == "test-repo"
        assert obj.project == "INSURANCE"
        assert obj.branch == "main"
        assert obj.url == "https://bitbucket.example.com/scm/ins/test-repo.git"
        assert obj.sync_metadata == {"preserve_local_path": True}

    def test_missing_name_rejected(self) -> None:
        obj = _MissingName()
        assert not isinstance(obj, SyncableRepo)

    def test_missing_sync_metadata_rejected(self) -> None:
        obj = _MissingSyncMetadata()
        assert not isinstance(obj, SyncableRepo)

    def test_plain_dict_rejected(self) -> None:
        obj = {"name": "r", "project": "P", "branch": "m", "url": None, "sync_metadata": {}}
        assert not isinstance(obj, SyncableRepo)


class TestPackageExport:
    """Verify SyncableRepo is re-exported from the package root."""

    def test_import_from_package_root(self) -> None:
        from vds_git_orchestrator import SyncableRepo as PkgProto
        from vds_git_orchestrator.protocols import SyncableRepo as ModProto

        assert PkgProto is ModProto

    def test_in_all_list(self) -> None:
        import vds_git_orchestrator

        assert "SyncableRepo" in vds_git_orchestrator.__all__
