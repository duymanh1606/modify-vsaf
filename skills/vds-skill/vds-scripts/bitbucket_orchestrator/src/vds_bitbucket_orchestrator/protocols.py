"""Protocol interfaces for Bitbucket client dependency injection and testability.

This module defines Protocol classes that enable:
- Dependency injection for testing with mock implementations
- Type-safe interfaces for different Bitbucket API capabilities
- Separation of concerns between repository, branch, and code operations

Usage:
    from vds_bitbucket_orchestrator.protocols import (
        BitbucketRepositoryClient,
        BitbucketBranchClient,
        BitbucketCodeClient,
        BitbucketFullClient,
    )

    def audit_repository(client: BitbucketRepositoryClient, project_key: str) -> dict:
        repos = client.list_repositories(project_key)
        return {"repositories": repos}

References:
    - FR-21.2.1: Protocol classes for dependency injection and testability
    - TSK-222: Protocol interfaces for Bitbucket
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BitbucketRepositoryClient(Protocol):
    """Protocol for Bitbucket repository operations.

    This protocol defines the interface for repository-related operations
    including listing, getting, creating, and managing repositories.

    Implementations:
        - BitbucketClient: Full implementation using atlassian-python-api
        - Mock implementations for testing
    """

    def list_projects(self, limit: int = 25) -> list[dict[str, Any]]:
        """List all projects.

        Args:
            limit: Maximum number of projects to return (default: 25)

        Returns:
            List of project dictionaries with keys like 'key', 'name', 'description'
        """
        ...

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project information.

        Args:
            project_key: The project key (e.g., 'INS', 'LEP')

        Returns:
            Project dictionary with metadata
        """
        ...

    def list_repositories(self, project_key: str, limit: int = 25) -> list[dict[str, Any]]:
        """List repositories in a project.

        Args:
            project_key: The project key
            limit: Maximum number of repositories to return (default: 25)

        Returns:
            List of repository dictionaries with keys like 'slug', 'name', 'description'
        """
        ...

    def get_repository(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get repository information.

        Args:
            project_key: The project key
            repository_slug: The repository slug

        Returns:
            Repository dictionary with metadata
        """
        ...


@runtime_checkable
class BitbucketBranchClient(Protocol):
    """Protocol for Bitbucket branch and permission operations.

    This protocol defines the interface for branch-related operations
    including listing branches, managing permissions, and branch restrictions.

    Implementations:
        - BitbucketClient: Full implementation using atlassian-python-api
        - Mock implementations for testing
    """

    def get_branches(
        self,
        project_key: str,
        repository_slug: str,
        filter: str = "",
        limit: int = 99999,
        details: bool = True,
    ) -> list[dict[str, Any]]:
        """Get branches from a repository.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            filter: Optional filter string for branch names
            limit: Maximum number of branches to return (default: 99999)
            details: Whether to include branch details (default: True)

        Returns:
            List of branch dictionaries with metadata
        """
        ...

    def list_branch_permissions(
        self,
        project_key: str,
        repository_slug: str | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """List branch permissions (server and cloud).

        Args:
            project_key: The project key
            repository_slug: Optional repository slug (required for cloud mode)
            start: Start index for pagination (default: 0)
            limit: Maximum number of permissions to return (default: 25)

        Returns:
            Normalized list of branch restriction objects
        """
        ...


@runtime_checkable
class BitbucketCodeClient(Protocol):
    """Protocol for Bitbucket code and commit operations.

    This protocol defines the interface for code-related operations
    including file content retrieval and commit history.

    Implementations:
        - BitbucketClient: Full implementation using atlassian-python-api
        - Mock implementations for testing

    Note:
        Method names match the atlassian-python-api SDK:
        - get_content_of_file() (not get_file_content)
        - get_commits() (not list_commits)
    """

    def get_content_of_file(
        self,
        project_key: str,
        repository_slug: str,
        filename: str,
        at: str | None = None,
        markup: str | None = None,
    ) -> str:
        """Get raw content of a file from repository.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            filename: Path to the file in the repository
            at: Optional commit hash, branch, or tag to retrieve file at
            markup: Optional markup format for rendering

        Returns:
            File content as string
        """
        ...

    def get_commits(
        self,
        project_key: str,
        repository_slug: str,
        hash_oldest: str | None = None,
        hash_newest: str | None = None,
        limit: int = 99999,
    ) -> list[dict[str, Any]]:
        """Get commit list from repository.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            hash_oldest: Optional oldest commit hash to start from
            hash_newest: Optional newest commit hash to end at
            limit: Maximum number of commits to return (default: 99999)

        Returns:
            List of commit dictionaries with metadata
        """
        ...


@runtime_checkable
class BitbucketFullClient(BitbucketRepositoryClient, BitbucketBranchClient, BitbucketCodeClient, Protocol):
    """Combined protocol for full Bitbucket client capabilities.

    This protocol is a union of all Bitbucket client protocols:
    - BitbucketRepositoryClient: Repository operations
    - BitbucketBranchClient: Branch and permission operations
    - BitbucketCodeClient: Code and commit operations

    Use this protocol when you need access to all Bitbucket capabilities.
    For more focused interfaces, use the individual protocols.

    Implementations:
        - BitbucketClient: Full implementation using atlassian-python-api

    Example:
        def full_audit(client: BitbucketFullClient, project_key: str, repo_slug: str):
            # Repository operations
            repo = client.get_repository(project_key, repo_slug)

            # Branch operations
            permissions = client.list_branch_permissions(project_key, repo_slug)

            # Code operations
            readme = client.get_content_of_file(project_key, repo_slug, "README.md")
            commits = client.get_commits(project_key, repo_slug, limit=10)

            return {"repo": repo, "permissions": permissions, "readme": readme, "commits": commits}
    """

    pass


__all__ = [
    "BitbucketBranchClient",
    "BitbucketCodeClient",
    "BitbucketFullClient",
    "BitbucketRepositoryClient",
]
