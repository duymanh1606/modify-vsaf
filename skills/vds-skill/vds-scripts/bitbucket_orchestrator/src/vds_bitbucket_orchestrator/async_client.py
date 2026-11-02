"""Async Bitbucket client wrapper using asyncio.to_thread().

This module provides an async wrapper around the synchronous BitbucketClient,
enabling non-blocking Bitbucket API operations in async contexts.

Usage:
    from vds_bitbucket_orchestrator import create_async_client

    async def audit_repos():
        client = create_async_client()
        repos = await client.list_repositories("INS")
        return repos

References:
    - FR-21.2.3: AsyncBitbucketClient using asyncio.to_thread()
    - TSK-225: Async Bitbucket wrapper
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from .client import BitbucketClient

if TYPE_CHECKING:
    from .config import BitbucketSettings


class AsyncBitbucketClient:
    """Async wrapper for BitbucketClient using asyncio.to_thread().

    This class wraps the synchronous BitbucketClient methods using
    asyncio.to_thread() to enable non-blocking execution in async contexts.
    It implements the same protocols as BitbucketClient:
    - BitbucketRepositoryClient: Repository operations
    - BitbucketBranchClient: Branch and permission operations
    - BitbucketCodeClient: Code and commit operations
    - BitbucketFullClient: Combined protocol

    The async wrapper is useful for:
    - Concurrent API calls without blocking the event loop
    - Integration with async frameworks (FastAPI, aiohttp, etc.)
    - Parallel evidence collection in audit workflows

    Example:
        from vds_bitbucket_orchestrator import create_async_client

        async def collect_evidence():
            client = create_async_client()

            # Concurrent API calls
            repos, branches = await asyncio.gather(
                client.list_repositories("INS"),
                client.get_branches("INS", "insurance-core"),
            )
            return repos, branches

    Note:
        The underlying HTTP calls are still synchronous but run in a
        thread pool, preventing them from blocking the async event loop.
    """

    def __init__(
        self,
        settings: BitbucketSettings,
        *,
        timeout: int | None = 30,
    ) -> None:
        """Initialize the async client with a sync BitbucketClient.

        Args:
            settings: BitbucketSettings instance with credentials and configuration.
            timeout: HTTP timeout in seconds (default: 30).
        """
        self._sync_client = BitbucketClient(settings, timeout=timeout)
        self._settings = settings
        self._timeout = timeout

    @property
    def sync_client(self) -> BitbucketClient:
        """Access the underlying synchronous client.

        Useful for cases where sync access is needed or for testing.
        """
        return self._sync_client

    # =========================================================================
    # Project Management (BitbucketRepositoryClient)
    # =========================================================================

    async def list_projects(self, limit: int = 25) -> list[dict[str, Any]]:
        """List all projects asynchronously.

        Args:
            limit: Maximum number of projects to return (default: 25)

        Returns:
            List of project dictionaries with keys like 'key', 'name', 'description'
        """
        return await asyncio.to_thread(self._sync_client.list_projects, limit)

    async def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project information asynchronously.

        Args:
            project_key: The project key (e.g., 'INS', 'LEP')

        Returns:
            Project dictionary with metadata
        """
        return await asyncio.to_thread(self._sync_client.get_project, project_key)

    async def create_project(
        self, key: str, name: str, description: str = "Project created via VDS orchestrator"
    ) -> dict[str, Any]:
        """Create a new project asynchronously.

        Args:
            key: Project key
            name: Project name
            description: Project description

        Returns:
            Created project dictionary
        """
        return await asyncio.to_thread(self._sync_client.create_project, key, name, description)

    # =========================================================================
    # Repository Management (BitbucketRepositoryClient)
    # =========================================================================

    async def list_repositories(self, project_key: str, limit: int = 25) -> list[dict[str, Any]]:
        """List repositories in a project asynchronously.

        Args:
            project_key: The project key
            limit: Maximum number of repositories to return (default: 25)

        Returns:
            List of repository dictionaries with keys like 'slug', 'name', 'description'
        """
        return await asyncio.to_thread(self._sync_client.list_repositories, project_key, limit)

    async def get_repository(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get repository information asynchronously.

        Args:
            project_key: The project key
            repository_slug: The repository slug

        Returns:
            Repository dictionary with metadata
        """
        return await asyncio.to_thread(self._sync_client.get_repository, project_key, repository_slug)

    async def create_repository(
        self, project_key: str, repository: str, forkable: bool = False, is_private: bool = True
    ) -> dict[str, Any]:
        """Create a new repository asynchronously.

        Args:
            project_key: Project key
            repository: Repository name
            forkable: Whether the repository can be forked
            is_private: Whether the repository is private

        Returns:
            Created repository dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.create_repository, project_key, repository, forkable, is_private
        )

    async def update_repository(
        self, project_key: str, repository_slug: str, description: str | None = None
    ) -> dict[str, Any]:
        """Update repository information asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            description: New description

        Returns:
            Updated repository dictionary
        """
        return await asyncio.to_thread(self._sync_client.update_repository, project_key, repository_slug, description)

    async def delete_repository(self, project_key: str, repository_slug: str) -> None:
        """Delete a repository asynchronously (DANGER!).

        Args:
            project_key: Project key
            repository_slug: Repository slug
        """
        return await asyncio.to_thread(self._sync_client.delete_repository, project_key, repository_slug)

    async def get_repository_labels(self, project_key: str, repository_slug: str) -> list[str]:
        """Get labels for a repository asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug

        Returns:
            List of label strings
        """
        return await asyncio.to_thread(self._sync_client.get_repository_labels, project_key, repository_slug)

    async def get_default_branch(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get default branch for a repository asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug

        Returns:
            Default branch dictionary
        """
        return await asyncio.to_thread(self._sync_client.get_default_branch, project_key, repository_slug)

    async def set_repository_label(self, project_key: str, repository_slug: str, label_name: str) -> dict[str, Any]:
        """Set a label for a repository asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            label_name: Label to set

        Returns:
            Result dictionary
        """
        return await asyncio.to_thread(self._sync_client.set_repository_label, project_key, repository_slug, label_name)

    # =========================================================================
    # Branch Management (BitbucketBranchClient)
    # =========================================================================

    async def get_branches(
        self,
        project_key: str,
        repository_slug: str,
        filter: str = "",
        limit: int = 99999,
        details: bool = True,
    ) -> list[dict[str, Any]]:
        """Get branches from a repository asynchronously.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            filter: Optional filter string for branch names
            limit: Maximum number of branches to return (default: 99999)
            details: Whether to include branch details (default: True)

        Returns:
            List of branch dictionaries with metadata
        """
        return await asyncio.to_thread(
            self._sync_client.get_branches, project_key, repository_slug, filter, limit, details
        )

    async def create_branch(
        self, project_key: str, repository_slug: str, name: str, start_point: str, message: str | None = None
    ) -> dict[str, Any]:
        """Create a branch asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            name: Branch name
            start_point: Starting commit/branch
            message: Optional message

        Returns:
            Created branch dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.create_branch, project_key, repository_slug, name, start_point, message
        )

    async def delete_branch(
        self, project_key: str, repository_slug: str, name: str, end_point: str | None = None
    ) -> dict[str, Any]:
        """Delete a branch asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            name: Branch name
            end_point: Optional end point

        Returns:
            Result dictionary
        """
        return await asyncio.to_thread(self._sync_client.delete_branch, project_key, repository_slug, name, end_point)

    async def list_branch_permissions(
        self,
        project_key: str,
        repository_slug: str | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """List branch permissions asynchronously.

        Args:
            project_key: The project key
            repository_slug: Optional repository slug (required for cloud mode)
            start: Start index for pagination (default: 0)
            limit: Maximum number of permissions to return (default: 25)

        Returns:
            Normalized list of branch restriction objects
        """
        return await asyncio.to_thread(
            self._sync_client.list_branch_permissions, project_key, repository_slug, start, limit
        )

    # =========================================================================
    # Tag Management
    # =========================================================================

    async def get_tags(
        self, project_key: str, repository_slug: str, filter: str = "", limit: int = 99999
    ) -> list[dict[str, Any]]:
        """Get tags for a repository asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            filter: Optional filter string
            limit: Maximum number of tags

        Returns:
            List of tag dictionaries
        """
        return await asyncio.to_thread(self._sync_client.get_tags, project_key, repository_slug, filter, limit)

    async def set_tag(
        self,
        project_key: str,
        repository_slug: str,
        tag_name: str,
        commit_revision: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Set a tag asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            tag_name: Tag name
            commit_revision: Commit to tag
            description: Optional description

        Returns:
            Created tag dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.set_tag, project_key, repository_slug, tag_name, commit_revision, description
        )

    async def delete_tag(self, project_key: str, repository_slug: str, tag_name: str) -> dict[str, Any]:
        """Delete a tag asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            tag_name: Tag name

        Returns:
            Result dictionary
        """
        return await asyncio.to_thread(self._sync_client.delete_tag, project_key, repository_slug, tag_name)

    # =========================================================================
    # Code Operations (BitbucketCodeClient)
    # =========================================================================

    async def get_content_of_file(
        self,
        project_key: str,
        repository_slug: str,
        filename: str,
        at: str | None = None,
        markup: str | None = None,
    ) -> str:
        """Get raw content of a file from repository asynchronously.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            filename: Path to the file in the repository
            at: Optional commit hash, branch, or tag to retrieve file at
            markup: Optional markup format for rendering

        Returns:
            File content as string
        """
        return await asyncio.to_thread(
            self._sync_client.get_content_of_file, project_key, repository_slug, filename, at, markup
        )

    async def get_commits(
        self,
        project_key: str,
        repository_slug: str,
        hash_oldest: str | None = None,
        hash_newest: str | None = None,
        limit: int = 99999,
    ) -> list[dict[str, Any]]:
        """Get commit list from repository asynchronously.

        Args:
            project_key: The project key
            repository_slug: The repository slug
            hash_oldest: Optional oldest commit hash to start from
            hash_newest: Optional newest commit hash to end at
            limit: Maximum number of commits to return (default: 99999)

        Returns:
            List of commit dictionaries with metadata
        """
        return await asyncio.to_thread(
            self._sync_client.get_commits, project_key, repository_slug, hash_oldest, hash_newest, limit
        )

    # =========================================================================
    # Pull Request Management
    # =========================================================================

    async def list_pull_requests(
        self,
        project_key: str,
        repository_slug: str,
        state: str = "OPEN",
        order: str = "newest",
        limit: int = 100,
        start: int = 0,
    ) -> list[dict[str, Any]]:
        """List pull requests asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            state: PR state (OPEN, MERGED, DECLINED)
            order: Sort order (newest, oldest)
            limit: Maximum number of PRs to return
            start: Start index for pagination

        Returns:
            List of pull request dictionaries
        """
        return await asyncio.to_thread(
            self._sync_client.list_pull_requests, project_key, repository_slug, state, order, limit, start
        )

    async def get_pull_request(self, project_key: str, repository_slug: str, pull_request_id: str) -> dict[str, Any]:
        """Get a specific pull request asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID

        Returns:
            Pull request dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.get_pull_request, project_key, repository_slug, pull_request_id
        )

    async def create_pull_request(
        self,
        source_project: str,
        source_repo: str,
        dest_project: str,
        dest_repo: str,
        source_branch: str,
        destination_branch: str,
        title: str,
        description: str,
        reviewers: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a pull request asynchronously.

        Args:
            source_project: Source project key
            source_repo: Source repository slug
            dest_project: Destination project key
            dest_repo: Destination repository slug
            source_branch: Source branch name
            destination_branch: Destination branch name
            title: PR title
            description: PR description
            reviewers: Optional list of reviewer usernames

        Returns:
            Created pull request dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.create_pull_request,
            source_project,
            source_repo,
            dest_project,
            dest_repo,
            source_branch,
            destination_branch,
            title,
            description,
            reviewers,
        )

    async def add_pull_request_comment(
        self,
        project_key: str,
        repository_slug: str,
        pull_request_id: str,
        text: str,
        parent_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a comment to a pull request asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID
            text: Comment text
            parent_id: Optional parent comment ID for replies

        Returns:
            Created comment dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.add_pull_request_comment,
            project_key,
            repository_slug,
            pull_request_id,
            text,
            parent_id,
        )

    async def get_pull_request_activities(
        self, project_key: str, repository_slug: str, pull_request_id: str
    ) -> list[dict[str, Any]]:
        """Get pull request activities asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID

        Returns:
            List of activity dictionaries
        """
        return await asyncio.to_thread(
            self._sync_client.get_pull_request_activities, project_key, repository_slug, pull_request_id
        )

    async def get_pull_request_changes(
        self, project_key: str, repository_slug: str, pull_request_id: str
    ) -> list[dict[str, Any]]:
        """Get pull request changes asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID

        Returns:
            List of change dictionaries
        """
        return await asyncio.to_thread(
            self._sync_client.get_pull_request_changes, project_key, repository_slug, pull_request_id
        )

    async def merge_pull_request(self, project_key: str, repository_slug: str, pull_request_id: str) -> dict[str, Any]:
        """Merge a pull request asynchronously.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID

        Returns:
            Merge result dictionary
        """
        return await asyncio.to_thread(
            self._sync_client.merge_pull_request, project_key, repository_slug, pull_request_id
        )

    # =========================================================================
    # Pipeline Management (Bitbucket Cloud only)
    # =========================================================================

    async def list_pipelines(self, workspace: str, repository: str, limit: int = 10) -> list[dict[str, Any]]:
        """List pipelines asynchronously (Bitbucket Cloud only).

        Args:
            workspace: Workspace name
            repository: Repository name
            limit: Maximum number of pipelines

        Returns:
            List of pipeline dictionaries
        """
        return await asyncio.to_thread(self._sync_client.list_pipelines, workspace, repository, limit)

    async def trigger_pipeline(self, workspace: str, repository: str, branch: str = "master") -> dict[str, Any]:
        """Trigger a pipeline asynchronously (Bitbucket Cloud only).

        Args:
            workspace: Workspace name
            repository: Repository name
            branch: Branch to trigger pipeline on

        Returns:
            Triggered pipeline dictionary
        """
        return await asyncio.to_thread(self._sync_client.trigger_pipeline, workspace, repository, branch)

    # =========================================================================
    # User and Group Management
    # =========================================================================

    async def list_groups(self, group_filter: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        """List all available groups asynchronously.

        Args:
            group_filter: Optional filter string
            limit: Maximum number of groups

        Returns:
            List of group dictionaries
        """
        return await asyncio.to_thread(self._sync_client.list_groups, group_filter, limit)


__all__ = ["AsyncBitbucketClient"]
