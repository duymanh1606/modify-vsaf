"""
Tests for vds_git_orchestrator public API exports (TSK-221).

Validates FR-21.1.2: Export Repository, Manifest, ManifestFilters, GitOperation,
RunSummary, orchestrate_repositories from vds_git_orchestrator.__init__

These tests verify that:
1. All public symbols can be imported from the package root
2. The __all__ list contains all expected symbols
3. Imported symbols are the correct types/classes
4. Basic functionality works when using package-level imports
"""

from pathlib import Path


class TestPublicAPIExports:
    """Test that all public symbols are exported from package root."""

    def test_import_repository_from_package_root(self) -> None:
        """Verify Repository can be imported from vds_git_orchestrator."""
        from vds_git_orchestrator import Repository

        # Verify it's the correct class by checking it's a dataclass
        assert hasattr(Repository, "__dataclass_fields__")
        assert "name" in Repository.__dataclass_fields__
        assert "path" in Repository.__dataclass_fields__
        assert "project" in Repository.__dataclass_fields__
        assert "branch" in Repository.__dataclass_fields__

    def test_import_manifest_from_package_root(self) -> None:
        """Verify Manifest can be imported from vds_git_orchestrator."""
        from vds_git_orchestrator import Manifest

        # Verify it's the correct class
        assert hasattr(Manifest, "__dataclass_fields__")
        assert "repositories" in Manifest.__dataclass_fields__
        assert hasattr(Manifest, "merge")
        assert hasattr(Manifest, "filter")

    def test_import_manifest_filters_from_package_root(self) -> None:
        """Verify ManifestFilters can be imported from vds_git_orchestrator."""
        from vds_git_orchestrator import ManifestFilters

        # Verify it's the correct class
        assert hasattr(ManifestFilters, "__dataclass_fields__")
        assert "project" in ManifestFilters.__dataclass_fields__
        assert "name_match" in ManifestFilters.__dataclass_fields__
        assert "include_tags" in ManifestFilters.__dataclass_fields__
        assert "exclude_tags" in ManifestFilters.__dataclass_fields__

    def test_import_git_operation_from_package_root(self) -> None:
        """Verify GitOperation can be imported from vds_git_orchestrator."""
        from vds_git_orchestrator import GitOperation

        # Verify it's an Enum with expected values
        assert hasattr(GitOperation, "FETCH")
        assert hasattr(GitOperation, "PULL")
        assert hasattr(GitOperation, "CLONE")
        assert hasattr(GitOperation, "STATUS")
        assert GitOperation.PULL.value == "pull"

    def test_import_run_summary_from_package_root(self) -> None:
        """Verify RunSummary can be imported from vds_git_orchestrator."""
        from vds_git_orchestrator import RunSummary

        # Verify it's the correct class
        assert hasattr(RunSummary, "__dataclass_fields__")
        assert "total" in RunSummary.__dataclass_fields__
        assert "successes" in RunSummary.__dataclass_fields__
        assert "failures" in RunSummary.__dataclass_fields__
        assert hasattr(RunSummary, "from_results")
        assert hasattr(RunSummary, "to_dict")

    def test_import_orchestrate_repositories_from_package_root(self) -> None:
        """Verify orchestrate_repositories can be imported from vds_git_orchestrator."""
        # Verify it's a callable (async function)
        import inspect

        from vds_git_orchestrator import orchestrate_repositories

        assert callable(orchestrate_repositories)
        assert inspect.iscoroutinefunction(orchestrate_repositories)


class TestAllList:
    """Test that __all__ contains all expected public symbols."""

    def test_all_list_contains_manifest_symbols(self) -> None:
        """Verify __all__ includes Repository, Manifest, ManifestFilters."""
        import vds_git_orchestrator

        assert "Repository" in vds_git_orchestrator.__all__
        assert "Manifest" in vds_git_orchestrator.__all__
        assert "ManifestFilters" in vds_git_orchestrator.__all__

    def test_all_list_contains_orchestrator_symbols(self) -> None:
        """Verify __all__ includes GitOperation, RunSummary, orchestrate_repositories."""
        import vds_git_orchestrator

        assert "GitOperation" in vds_git_orchestrator.__all__
        assert "RunSummary" in vds_git_orchestrator.__all__
        assert "orchestrate_repositories" in vds_git_orchestrator.__all__

    def test_all_list_has_exactly_six_symbols(self) -> None:
        """Verify __all__ contains exactly the 6 expected public symbols."""
        import vds_git_orchestrator

        expected_symbols = {
            "Repository",
            "Manifest",
            "ManifestFilters",
            "GitOperation",
            "RunSummary",
            "orchestrate_repositories",
            "SyncableRepo",
        }
        assert set(vds_git_orchestrator.__all__) == expected_symbols


class TestImportEquivalence:
    """Test that package-level imports are equivalent to module-level imports."""

    def test_repository_import_equivalence(self) -> None:
        """Verify package import equals module import for Repository."""
        from vds_git_orchestrator import Repository as PkgRepository
        from vds_git_orchestrator.manifest import Repository as ModRepository

        assert PkgRepository is ModRepository

    def test_manifest_import_equivalence(self) -> None:
        """Verify package import equals module import for Manifest."""
        from vds_git_orchestrator import Manifest as PkgManifest
        from vds_git_orchestrator.manifest import Manifest as ModManifest

        assert PkgManifest is ModManifest

    def test_manifest_filters_import_equivalence(self) -> None:
        """Verify package import equals module import for ManifestFilters."""
        from vds_git_orchestrator import ManifestFilters as PkgFilters
        from vds_git_orchestrator.manifest import ManifestFilters as ModFilters

        assert PkgFilters is ModFilters

    def test_git_operation_import_equivalence(self) -> None:
        """Verify package import equals module import for GitOperation."""
        from vds_git_orchestrator import GitOperation as PkgOp
        from vds_git_orchestrator.orchestrator import GitOperation as ModOp

        assert PkgOp is ModOp

    def test_run_summary_import_equivalence(self) -> None:
        """Verify package import equals module import for RunSummary."""
        from vds_git_orchestrator import RunSummary as PkgSummary
        from vds_git_orchestrator.orchestrator import RunSummary as ModSummary

        assert PkgSummary is ModSummary

    def test_orchestrate_repositories_import_equivalence(self) -> None:
        """Verify package import equals module import for orchestrate_repositories."""
        from vds_git_orchestrator import orchestrate_repositories as pkg_func
        from vds_git_orchestrator.orchestrator import orchestrate_repositories as mod_func

        assert pkg_func is mod_func


class TestBasicFunctionality:
    """Test basic functionality using package-level imports."""

    def test_create_repository_from_package_import(self, tmp_path: Path) -> None:
        """Verify Repository can be instantiated using package import."""
        from vds_git_orchestrator import Repository

        repo = Repository(
            name="test-repo",
            path=tmp_path / "test-repo",
            project="insurance",
            branch="release",
            tags={"core", "backend"},
        )

        assert repo.name == "test-repo"
        assert repo.project == "insurance"
        assert repo.branch == "release"
        assert repo.tags == {"core", "backend"}

    def test_create_manifest_from_package_import(self, tmp_path: Path) -> None:
        """Verify Manifest can be instantiated using package import."""
        from vds_git_orchestrator import Manifest, Repository

        repo = Repository(
            name="test-repo",
            path=tmp_path / "test-repo",
            project="insurance",
            branch="release",
        )
        manifest = Manifest(repositories=[repo])

        assert len(manifest.repositories) == 1
        assert manifest.repositories[0].name == "test-repo"

    def test_filter_manifest_from_package_import(self, tmp_path: Path) -> None:
        """Verify ManifestFilters works with package imports."""
        from vds_git_orchestrator import Manifest, ManifestFilters, Repository

        repos = [
            Repository(
                name="service-a",
                path=tmp_path / "service-a",
                project="insurance",
                branch="release",
            ),
            Repository(
                name="service-b",
                path=tmp_path / "service-b",
                project="lep",
                branch="release",
            ),
        ]
        manifest = Manifest(repositories=repos)
        filters = ManifestFilters(project="insurance")

        filtered = manifest.filter(filters)

        assert len(filtered) == 1
        assert filtered[0].name == "service-a"

    def test_git_operation_enum_from_package_import(self) -> None:
        """Verify GitOperation enum works with package import."""
        from vds_git_orchestrator import GitOperation

        assert GitOperation.PULL.value == "pull"
        assert GitOperation.FETCH.value == "fetch"
        assert GitOperation.CLONE.value == "clone"
        assert GitOperation.STATUS.value == "status"
