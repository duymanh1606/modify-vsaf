"""
VDS Git Orchestrator package.

Provides async git operations across multiple repository groups (LEP, INSURANCE, EKYC).

Public API exports (FR-21.1.2):
- Repository: Dataclass representing a git repository with name, path, project, branch, tags
- Manifest: Collection of repositories with merge and filter capabilities
- ManifestFilters: Filter criteria for selecting repositories from a manifest
- GitOperation: Enum of supported git operations (FETCH, PULL, CLONE, etc.)
- RunSummary: Summary of orchestration results with success/failure counts
- orchestrate_repositories: Main async function to run git operations across repositories
"""

from vds_git_orchestrator.manifest import Manifest, ManifestFilters, Repository
from vds_git_orchestrator.orchestrator import GitOperation, RunSummary, orchestrate_repositories
from vds_git_orchestrator.protocols import SyncableRepo

__all__ = [
    # Orchestrator models and functions (subtask 2.2)
    "GitOperation",
    "Manifest",
    "ManifestFilters",
    # Manifest models (subtask 2.1)
    "Repository",
    "RunSummary",
    # Protocols
    "SyncableRepo",
    "orchestrate_repositories",
]
