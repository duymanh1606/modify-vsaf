"""Bitbucket client wrapper using atlassian-python-api for consistency."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from itertools import islice
from typing import TYPE_CHECKING, Any

import requests
import structlog
from atlassian import Bitbucket as AtlassianBitbucket

from .errors import (
    AuthError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ResponseError,
    RetryError,
    TransportError,
    VDSClientError,
)

if TYPE_CHECKING:
    from .config import BitbucketSettings

# Substrings that mark a rejected credential. Shared by the error mapper below and by the
# one-shot auth fallback, so the two can never drift into disagreeing about what a 401 is.
UNAUTHORIZED_MARKERS = ("unauthorized", "authentication", "401")


def _is_unauthorized(error: Exception) -> bool:
    """True when the server rejected the credential itself.

    Deliberately 401-shaped only. A 403 is an answer from a server that did accept the
    login and is talking about permissions, so trying a second credential there would
    spend a login attempt to learn nothing.
    """
    text = str(error).lower()
    return any(marker in text for marker in UNAUTHORIZED_MARKERS)


def _drained(result: Any) -> Any:
    """Materialise a lazy result so its first request happens inside the caller's ``try``.

    The paginated endpoints of atlassian-python-api hand back a generator, and nothing
    has left the machine yet when they do: the request goes out on the first ``next()``,
    which for a caller means the 401 surfaces outside the block meant to catch it.

    Safe to do here because no method of ``BitbucketClient`` returns a lazy iterator —
    every one of them already builds a list, a dict or ``None`` before returning. Note
    that ``list`` and ``dict`` are not ``Iterator``s, so ordinary results pass through
    untouched.
    """
    return list(result) if isinstance(result, Iterator) else result


class _RetriesAuthOnce:
    """The atlassian client, with exactly one second chance at authenticating.

    Every Bitbucket call in this module goes through ``self._client``, so wrapping it once
    here is how the fallback login from ``BitbucketSettings.auth_attempts()`` reaches all
    of them without rewriting every call site.

    "Once" is the whole point, not an implementation detail. The cursor only moves
    forward, so a credential the server refuses costs one failed login per process rather
    than a stream of them. A stream is what locks a Bitbucket account, and locking the
    user's account is the bug this class exists to fix — so never wrap a loop around it.

    Chained attribute access (``client.cloud.workspaces.get(...)``) hands back the inner
    object and leaves this wrapper behind. Those paths are Bitbucket Cloud only, where the
    Bearer token is the shape that works, so they never needed the fallback.
    """

    def __init__(
        self,
        build: Callable[[dict[str, str]], Any],
        attempts: list[dict[str, str]],
    ) -> None:
        self._build = build
        self._attempts = attempts
        self._at = 0
        self._inner = build(attempts[0])
        self._log = structlog.get_logger(__name__)

    def _fall_back(self) -> bool:
        """Move to the next credential shape. False when there is no next one."""
        if self._at + 1 >= len(self._attempts):
            return False
        self._at += 1
        self._inner = self._build(self._attempts[self._at])
        # Field names only. The values are a Personal Access Token and must not be logged.
        self._log.warning("auth_fallback", attempt=self._at + 1, fields=sorted(self._attempts[self._at]))
        return True

    def __getattr__(self, name: str) -> Any:
        # Read through __dict__: during __init__ the attribute does not exist yet, and
        # asking for it the normal way would land back in here forever.
        inner = self.__dict__.get("_inner")
        if inner is None:
            raise AttributeError(name)

        target = getattr(inner, name)
        if not callable(target):
            return target

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                return _drained(target(*args, **kwargs))
            except Exception as exc:
                if not _is_unauthorized(exc) or not self._fall_back():
                    raise
                # One rejected login, one retry, and the cursor has already moved — so a
                # second 401 leaves through the `raise` above instead of coming back here.
                return _drained(getattr(self._inner, name)(*args, **kwargs))

        return call


class BitbucketClient:
    """Bitbucket client wrapper using atlassian-python-api SDK.

    This class implements the following protocols for dependency injection:
    - BitbucketRepositoryClient: Repository operations (list_projects, get_project, etc.)
    - BitbucketBranchClient: Branch and permission operations (get_branches, list_branch_permissions)
    - BitbucketCodeClient: Code operations (get_content_of_file, get_commits)
    - BitbucketFullClient: Combined protocol (union of all above)

    The protocols enable type-safe dependency injection and mock implementations for testing.
    See protocols.py for protocol definitions.

    Example:
        from vds_bitbucket_orchestrator import BitbucketClient, BitbucketFullClient

        def audit_repo(client: BitbucketFullClient, project: str, repo: str) -> dict:
            # Type-safe access to all client methods
            return {
                "repo": client.get_repository(project, repo),
                "permissions": client.list_branch_permissions(project, repo),
                "readme": client.get_content_of_file(project, repo, "README.md"),
            }

        # BitbucketClient satisfies BitbucketFullClient protocol
        client = BitbucketClient(settings)
        result = audit_repo(client, "INS", "insurance-core")
    """

    def __init__(
        self,
        settings: BitbucketSettings,
        *,
        timeout: int | None = 30,
    ) -> None:
        self._settings = settings
        self._timeout = timeout or 30

        # Validate credentials
        settings.require_basic_or_token()

        try:
            url = settings.get_url()

            def build(auth_kwargs: dict[str, str]) -> Any:
                if settings.is_cloud_mode:
                    # For Bitbucket Cloud, we need to use the cloud API
                    return AtlassianBitbucket(
                        url=url, timeout=self._timeout, cloud=True, workspace=settings.cloud_workspace, **auth_kwargs
                    )
                # For Bitbucket Server/Data Center
                return AtlassianBitbucket(url=url, timeout=self._timeout, **auth_kwargs)

            # Built through the wrapper, not directly: on Bitbucket Server the first
            # credential shape is the one that answers 401, and every command in this
            # module depended on it. See BitbucketSettings.auth_attempts for the order.
            self._client = _RetriesAuthOnce(build, settings.auth_attempts())

        except Exception as exc:
            raise TransportError(
                f"Failed to initialize Bitbucket client: {exc}",
                context={"mode": settings.mode, "url": settings.get_url()},
            ) from exc

        self._log = structlog.get_logger(__name__).bind(mode=settings.mode, url=settings.get_url())

        # Store retry settings
        self._max_retries = settings.max_retries
        self._retry_backoff_factor = settings.retry_backoff_factor

    def _with_retry(self, operation, operation_name: str):
        """Execute an operation with retry logic using instance settings."""
        for attempt in range(self._max_retries + 1):
            try:
                result = operation()
                return result or []
            except Exception as exc:
                try:
                    self._handle_api_error(exc, operation_name)
                except (TransportError, RateLimitError) as retry_exc:
                    if attempt == self._max_retries:
                        self._log.error(
                            "retry_attempts_exhausted",
                            operation=operation_name,
                            attempts=self._max_retries,
                            final_error=str(retry_exc),
                        )
                        raise RetryError(
                            f"Retry attempts exhausted: {retry_exc}",
                            context={
                                "original_error": str(retry_exc),
                                "operation": operation_name,
                                "attempts": self._max_retries,
                            },
                        ) from retry_exc

                    wait_time = self._retry_backoff_factor * (2**attempt)
                    self._log.warning(
                        "retry_attempt",
                        operation=operation_name,
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        wait_time=wait_time,
                        error=str(retry_exc),
                    )
                    time.sleep(wait_time)
                except VDSClientError:
                    # Don't retry on client errors (auth, not found, etc.)
                    raise

    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Convert atlassian-python-api errors to our standardized errors."""
        error_str = str(error).lower()
        transport_markers = (
            "timed out",
            "timeout",
            "connection error",
            "connection reset",
            "connection refused",
            "name or service not known",
            "temporary failure in name resolution",
            "max retries exceeded",
        )

        if any(marker in error_str for marker in UNAUTHORIZED_MARKERS):
            raise AuthError(f"Authentication failed during {operation}", context={"error": str(error)})
        elif "forbidden" in error_str or "403" in error_str:
            raise AuthError(f"Access forbidden during {operation}", context={"error": str(error)})
        elif "not found" in error_str or "404" in error_str:
            raise NotFoundError(f"Resource not found during {operation}", context={"error": str(error)})
        elif "rate limit" in error_str or "429" in error_str:
            raise RateLimitError(f"Rate limited during {operation}", context={"error": str(error)})
        elif "conflict" in error_str or "409" in error_str:
            raise ConflictError(f"Conflict during {operation}", context={"error": str(error)})
        elif "server error" in error_str or "500" in error_str:
            raise ResponseError(f"Server error during {operation}", context={"error": str(error)})
        elif any(marker in error_str for marker in transport_markers):
            raise TransportError(f"Transport error during {operation}: {error}", context={"error": str(error)})
        else:
            raise VDSClientError(f"API error during {operation}: {error}", context={"error": str(error)})

    # Project Management
    def list_projects(self, limit: int = 25) -> list[dict[str, Any]]:
        """List all projects."""
        return self._with_retry(lambda: list(self._client.project_list(limit=limit)), "list_projects")

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project information."""
        try:
            result = self._client.project(project_key)
            self._log.debug("project_retrieved", project_key=project_key)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_project {project_key}")

    def create_project(
        self, key: str, name: str, description: str = "Project created via VDS orchestrator"
    ) -> dict[str, Any]:
        """Create a new project."""
        try:
            result = self._client.create_project(key, name, description)
            self._log.info("project_created", key=key, name=name)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_project {key}")

    # Repository Management
    def list_repositories(self, project_key: str, limit: int = 25) -> list[dict[str, Any]]:
        """List repositories in a project."""
        return self._with_retry(
            lambda: list(self._client.repo_list(project_key, limit=limit)), f"list_repositories {project_key}"
        )

    def get_repository(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get repository information."""
        try:
            result = self._client.get_repo(project_key, repository_slug)
            self._log.debug("repository_retrieved", project_key=project_key, repository=repository_slug)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_repository {project_key}/{repository_slug}")

    def create_repository(
        self, project_key: str, repository: str, forkable: bool = False, is_private: bool = True
    ) -> dict[str, Any]:
        """Create a new repository."""
        try:
            result = self._client.create_repo(project_key, repository, forkable=forkable, is_private=is_private)
            self._log.info("repository_created", project_key=project_key, repository=repository)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_repository {repository}")

    def update_repository(
        self, project_key: str, repository_slug: str, description: str | None = None
    ) -> dict[str, Any]:
        """Update repository information."""
        try:
            result = self._client.update_repo(project_key, repository_slug, description=description or "")
            self._log.info("repository_updated", project_key=project_key, repository=repository_slug)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"update_repository {repository_slug}")

    def delete_repository(self, project_key: str, repository_slug: str) -> None:
        """Delete a repository (DANGER!).

        Reference: https://atlassian-python-api.readthedocs.io/bitbucket.html#delete-a-repository-danger
        """
        try:
            self._client.delete_repo(project_key, repository_slug)
            self._log.warning("repository_deleted", project_key=project_key, repository=repository_slug)
        except Exception as exc:
            self._handle_api_error(exc, f"delete_repository {repository_slug}")

    def get_repository_labels(self, project_key: str, repository_slug: str) -> list[str]:
        """Get labels for a repository."""
        try:
            result = self._client.get_repo_labels(project_key, repository_slug)
            self._log.debug("repository_labels_retrieved", project_key=project_key, repository=repository_slug)
            return result if isinstance(result, list) else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_repository_labels {repository_slug}")

    def fork_repository(
        self,
        project_key: str,
        repository_slug: str,
        new_project_key: str | None = None,
        new_repository_slug: str | None = None,
    ) -> dict[str, Any]:
        """Fork a repository.

        Args:
            project_key: Source project key
            repository_slug: Source repository slug
            new_project_key: Target project key (if forking to new project). If None, forks within same project.
            new_repository_slug: Target repository slug. If None, uses same name as source.
        """
        try:
            if new_project_key:
                # Fork to new project
                if not new_repository_slug:
                    new_repository_slug = repository_slug
                result = self._client.fork_repository_new_project(  # type: ignore[attr-defined]
                    project_key, repository_slug, new_project_key, new_repository_slug
                )
                self._log.info(
                    "repository_forked_to_new_project",
                    source_project=project_key,
                    source_repo=repository_slug,
                    target_project=new_project_key,
                    target_repo=new_repository_slug,
                )
            else:
                # Fork within same project
                if not new_repository_slug:
                    new_repository_slug = f"{repository_slug}-fork"
                result = self._client.fork_repository(project_key, repository_slug, new_repository_slug)  # type: ignore[attr-defined]
                self._log.info(
                    "repository_forked",
                    project_key=project_key,
                    source_repo=repository_slug,
                    target_repo=new_repository_slug,
                )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"fork_repository {project_key}/{repository_slug}")

    def get_forked_repositories(self, project_key: str, repository_slug: str) -> list[dict[str, Any]]:
        """Get list of repositories forked from a source repository.

        Note: SDK doesn't have a direct method for this. We use repository list and filter.
        This may not be perfect but provides a way to discover forks.
        """
        try:
            # List all repositories in the project and filter for forks
            # Note: This is a workaround - actual fork relationship may need to be checked via repository metadata
            repos = self.list_repositories(project_key, limit=99999)
            # Filter repositories that might be forks (this is heuristic-based)
            # In practice, you may need to check repository origin or fork metadata
            forks = [repo for repo in repos if repository_slug.lower() in repo.get("slug", "").lower()]
            self._log.debug(
                "forked_repositories_retrieved", project_key=project_key, source_repo=repository_slug, count=len(forks)
            )
            return forks
        except Exception as exc:
            self._handle_api_error(exc, f"get_forked_repositories {project_key}/{repository_slug}")

    def set_repository_label(self, project_key: str, repository_slug: str, label_name: str) -> dict[str, Any]:
        """Set a label for a repository."""
        try:
            result = self._client.set_repo_label(project_key, repository_slug, label_name)
            self._log.info(
                "repository_label_set", project_key=project_key, repository=repository_slug, label=label_name
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_repository_label {repository_slug}")

    # Pull Request Management
    def list_pull_requests(
        self,
        project_key: str,
        repository_slug: str,
        state: str = "OPEN",
        order: str = "newest",
        limit: int = 100,
        start: int = 0,
    ) -> list[dict[str, Any]]:
        """List pull requests.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            state: PR state (OPEN, MERGED, DECLINED)
            order: Sort order (newest, oldest)
            limit: Maximum number of PRs to return
            start: Start index for pagination
        """
        return self._with_retry(
            lambda: list(
                self._client.get_pull_requests(
                    project_key, repository_slug, state=state, order=order, limit=limit, start=start
                )
            ),
            f"list_pull_requests {project_key}/{repository_slug}",
        )

    def create_pull_request(
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
        """Create a pull request."""
        try:
            kwargs = {}
            if reviewers:
                kwargs["reviewers"] = reviewers

            result = self._client.open_pull_request(
                source_project,
                source_repo,
                dest_project,
                dest_repo,
                source_branch,
                destination_branch,
                title,
                description,
                **kwargs,
            )
            self._log.info("pull_request_created", title=title, source=source_branch, dest=destination_branch)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_pull_request {title}")

    def get_pull_request(self, project_key: str, repository_slug: str, pull_request_id: str) -> dict[str, Any]:
        """Get a specific pull request."""
        try:
            # Get all PRs and find the one matching the ID
            prs = self._client.get_pull_requests(project_key, repository_slug, limit=1000)
            for pr in prs:
                if str(pr.get("id")) == str(pull_request_id):
                    self._log.debug(
                        "pull_request_retrieved",
                        project_key=project_key,
                        repository=repository_slug,
                        pr_id=pull_request_id,
                    )
                    return pr
            raise NotFoundError(
                f"Pull request {pull_request_id} not found",
                context={"project_key": project_key, "repository_slug": repository_slug},
            )
        except Exception as exc:
            self._handle_api_error(exc, f"get_pull_request {pull_request_id}")

    def add_pull_request_comment(
        self, project_key: str, repository_slug: str, pull_request_id: str, text: str, parent_id: str | None = None
    ) -> dict[str, Any]:
        """Add a comment to a pull request.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            pull_request_id: Pull request ID
            text: Comment text
            parent_id: Optional parent comment ID for replies
        """
        try:
            result = self._client.add_pull_request_comment(
                project_key, repository_slug, pull_request_id, text, parent_id=parent_id
            )
            self._log.info(
                "pull_request_comment_added",
                project_key=project_key,
                repository=repository_slug,
                pr_id=pull_request_id,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"add_pull_request_comment {pull_request_id}")

    def get_pull_request_activities(
        self, project_key: str, repository_slug: str, pull_request_id: str
    ) -> list[dict[str, Any]]:
        """Get pull request activities."""
        try:
            result = self._client.get_pull_requests_activities(project_key, repository_slug, pull_request_id)
            self._log.debug(
                "pull_request_activities_retrieved",
                project_key=project_key,
                repository=repository_slug,
                pr_id=pull_request_id,
            )
            return result if isinstance(result, list) else [result]
        except Exception as exc:
            self._handle_api_error(exc, f"get_pull_request_activities {pull_request_id}")

    def get_pull_request_changes(
        self, project_key: str, repository_slug: str, pull_request_id: str
    ) -> list[dict[str, Any]]:
        """Get pull request changes."""
        try:
            result = self._client.get_pull_requests_changes(project_key, repository_slug, pull_request_id)
            self._log.debug(
                "pull_request_changes_retrieved",
                project_key=project_key,
                repository=repository_slug,
                pr_id=pull_request_id,
            )
            return result if isinstance(result, list) else [result]
        except Exception as exc:
            self._handle_api_error(exc, f"get_pull_request_changes {pull_request_id}")

    def delete_pull_request(
        self, project_key: str, repository_slug: str, pull_request_id: str, pull_request_version: int
    ) -> dict[str, Any]:
        """Delete a pull request."""
        try:
            result = self._client.delete_pull_request(
                project_key, repository_slug, pull_request_id, pull_request_version
            )
            self._log.info(
                "pull_request_deleted",
                project_key=project_key,
                repository=repository_slug,
                pr_id=pull_request_id,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"delete_pull_request {pull_request_id}")

    def merge_pull_request(self, project_key: str, repository_slug: str, pull_request_id: str) -> dict[str, Any]:
        """Merge a pull request.

        Note: This method attempts to use merge_pull_request if available in the SDK.
        If it fails, consider using PR state transitions or activities API.
        """
        try:
            # Try the direct merge method first
            if hasattr(self._client, "merge_pull_request"):
                result = self._client.merge_pull_request(project_key, repository_slug, pull_request_id)
            else:
                # Fallback: Use PR activities to merge (may require different approach)
                raise VDSClientError(
                    "merge_pull_request method not available in SDK. Use PR state transitions or activities API.",
                    context={"project_key": project_key, "repository_slug": repository_slug, "pr_id": pull_request_id},
                )
            self._log.info(
                "pull_request_merged", project_key=project_key, repository=repository_slug, pr_id=pull_request_id
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"merge_pull_request {pull_request_id}")

    # Pipeline Management (for Bitbucket Cloud)
    def list_pipelines(self, workspace: str, repository: str, limit: int = 10) -> list[dict[str, Any]]:
        """List pipelines (Bitbucket Cloud only)."""
        if not self._settings.is_cloud_mode:
            raise VDSClientError("Pipelines are only available in Bitbucket Cloud mode")

        return self._with_retry(
            lambda: list(self._client.get_pipelines(workspace, repository, limit=limit)),
            f"list_pipelines {workspace}/{repository}",
        )

    def trigger_pipeline(self, workspace: str, repository: str, branch: str = "master") -> dict[str, Any]:
        """Trigger a pipeline (Bitbucket Cloud only)."""
        try:
            if not self._settings.is_cloud_mode:
                raise VDSClientError("Pipelines are only available in Bitbucket Cloud mode")

            result = self._client.trigger_pipeline(workspace, repository, branch=branch)
            self._log.info("pipeline_triggered", workspace=workspace, repository=repository, branch=branch)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"trigger_pipeline {workspace}/{repository}")

    # Branch Management
    def get_branches(
        self,
        project_key: str,
        repository_slug: str,
        filter: str = "",
        limit: int = 99999,
        details: bool = True,
    ) -> list[dict[str, Any]]:
        """Get branches from a repository."""
        try:
            result = self._client.get_branches(
                project_key, repository_slug, filter=filter, limit=limit, details=details
            )
            self._log.debug("branches_retrieved", project_key=project_key, repository=repository_slug)
            return result if isinstance(result, list) else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_branches {project_key}/{repository_slug}")

    def create_branch(
        self, project_key: str, repository_slug: str, name: str, start_point: str, message: str | None = None
    ) -> dict[str, Any]:
        """Create a branch."""
        try:
            result = self._client.create_branch(project_key, repository_slug, name, start_point, message or "")
            self._log.info("branch_created", project_key=project_key, repository=repository_slug, branch=name)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_branch {name}")

    def delete_branch(
        self, project_key: str, repository_slug: str, name: str, end_point: str | None = None
    ) -> dict[str, Any]:
        """Delete a branch."""
        try:
            result = self._client.delete_branch(project_key, repository_slug, name, end_point=end_point)
            self._log.info("branch_deleted", project_key=project_key, repository=repository_slug, branch=name)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"delete_branch {name}")

    # Tag Management
    def get_tags(
        self, project_key: str, repository_slug: str, filter: str = "", limit: int = 99999
    ) -> list[dict[str, Any]]:
        """Get tags for a repository."""
        try:
            result = self._client.get_tags(project_key, repository_slug, filter=filter, limit=limit)
            self._log.debug("tags_retrieved", project_key=project_key, repository=repository_slug)
            return result if isinstance(result, list) else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_tags {project_key}/{repository_slug}")

    def set_tag(
        self,
        project_key: str,
        repository_slug: str,
        tag_name: str,
        commit_revision: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Set a tag."""
        try:
            result = self._client.set_tag(
                project_key, repository_slug, tag_name, commit_revision, description=description
            )
            self._log.info("tag_set", project_key=project_key, repository=repository_slug, tag=tag_name)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_tag {tag_name}")

    def delete_tag(self, project_key: str, repository_slug: str, tag_name: str) -> dict[str, Any]:
        """Delete a tag."""
        try:
            result = self._client.delete_tag(project_key, repository_slug, tag_name)
            self._log.info("tag_deleted", project_key=project_key, repository=repository_slug, tag=tag_name)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"delete_tag {tag_name}")

    # User and Group Management
    def list_groups(self, group_filter: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        """List all available groups.

        Args:
            group_filter: Optional filter string to search for specific groups
            limit: Maximum number of groups to return
        """
        try:
            # Use get_groups with optional filter parameter
            if group_filter:
                result = list(self._client.get_groups(group_filter=group_filter, limit=limit))
            else:
                result = list(self._client.get_groups(limit=limit))
            self._log.debug("groups_listed", count=len(result) if result else 0, filter=group_filter)
            return result or []
        except Exception as exc:
            self._handle_api_error(exc, "list_groups")

    def list_project_users(
        self, project_key: str, filter_str: str | None = None, limit: int = 25
    ) -> list[dict[str, Any]]:
        """List users in a project.

        Args:
            project_key: Project key
            filter_str: Optional filter string to search for specific users
            limit: Maximum number of users to return
        """
        try:
            result = list(self._client.project_users(project_key, limit=limit, filter_str=filter_str))
            self._log.debug(
                "project_users_listed", project_key=project_key, count=len(result) if result else 0, filter=filter_str
            )
            return result or []
        except Exception as exc:
            self._handle_api_error(exc, f"list_project_users {project_key}")

    def list_project_groups(
        self, project_key: str, filter_str: str | None = None, limit: int = 25
    ) -> list[dict[str, Any]]:
        """List groups in a project.

        Args:
            project_key: Project key
            filter_str: Optional filter string to search for specific groups
            limit: Maximum number of groups to return
        """
        try:
            result = list(self._client.project_groups(project_key, limit=limit, filter_str=filter_str))
            self._log.debug(
                "project_groups_listed", project_key=project_key, count=len(result) if result else 0, filter=filter_str
            )
            return result or []
        except Exception as exc:
            self._handle_api_error(exc, f"list_project_groups {project_key}")

    def grant_user_repository_permissions(
        self, project_key: str, repository_slug: str, username: str, permission: str
    ) -> dict[str, Any]:
        """Grant repository permissions to a user."""
        try:
            result = self._client.repo_grant_user_permissions(project_key, repository_slug, username, permission)
            self._log.info(
                "user_repository_permissions_granted",
                project_key=project_key,
                repository_slug=repository_slug,
                username=username,
                permission=permission,
            )
            return result
        except Exception as exc:
            self._handle_api_error(
                exc, f"grant_user_repository_permissions {project_key}/{repository_slug} for {username}"
            )

    def grant_user_project_permissions(self, project_key: str, username: str, permission: str) -> dict[str, Any]:
        """Grant project permissions to a user."""
        try:
            result = self._client.project_grant_user_permissions(project_key, username, permission)
            self._log.info(
                "user_project_permissions_granted", project_key=project_key, username=username, permission=permission
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"grant_user_project_permissions {project_key} for {username}")

    def grant_group_project_permissions(self, project_key: str, group_name: str, permission: str) -> dict[str, Any]:
        """Grant project permissions to a group."""
        try:
            result = self._client.project_grant_group_permissions(project_key, group_name, permission)
            self._log.info(
                "group_project_permissions_granted",
                project_key=project_key,
                group=group_name,
                permission=permission,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"grant_group_project_permissions {project_key} for {group_name}")

    def grant_group_repository_permissions(
        self, project_key: str, repository_slug: str, group: str, permission: str
    ) -> dict[str, Any]:
        """Grant repository permissions to a group."""
        try:
            result = self._client.repo_grant_group_permissions(project_key, repository_slug, group, permission)
            self._log.info(
                "group_repository_permissions_granted",
                project_key=project_key,
                repository_slug=repository_slug,
                group=group,
                permission=permission,
            )
            return result
        except Exception as exc:
            self._handle_api_error(
                exc, f"grant_group_repository_permissions {project_key}/{repository_slug} for {group}"
            )

    # Branch Permissions
    def set_branches_permissions(
        self,
        project_key: str,
        multiple_permissions: bool = False,
        matcher_type: str | None = None,
        matcher_value: str | None = None,
        permission_type: str | None = None,
        repository_slug: str | None = None,
        except_users: list[str] | None = None,
        except_groups: list[str] | None = None,
        except_access_keys: list[str] | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> dict[str, Any]:
        """Set branch permissions."""
        try:
            result = self._client.set_branches_permissions(
                project_key,
                multiple_permissions=multiple_permissions,
                matcher_type=matcher_type,
                matcher_value=matcher_value,
                permission_type=permission_type,
                repository_slug=repository_slug,
                except_users=except_users or [],
                except_groups=except_groups or [],
                except_access_keys=except_access_keys or [],
                start=start,
                limit=limit,
            )
            self._log.info(
                "branch_permissions_set",
                project_key=project_key,
                repository_slug=repository_slug,
                permission_type=permission_type,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_branches_permissions {project_key}")

    def list_branch_permissions(
        self,
        project_key: str,
        repository_slug: str | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """List branch permissions (server and cloud).

        Returns a normalized list of branch restriction objects (payload["values"] when present).
        """

        def _fetch_permissions() -> list[dict[str, Any]]:
            settings = self._settings
            if settings.is_cloud_mode:
                if not repository_slug:
                    raise VDSClientError("repository_slug is required for cloud branch permissions list")
                if not settings.cloud_workspace:
                    raise VDSClientError("BITBUCKET_CLOUD_WORKSPACE is required for cloud mode")

                # Bitbucket Cloud uses page/pagelen rather than start/limit.
                page = 1 + (start // max(1, limit))
                url = (
                    f"https://api.bitbucket.org/2.0/repositories/"
                    f"{settings.cloud_workspace}/{repository_slug}/branch-restrictions"
                )
                params = {"page": page, "pagelen": limit}
            else:
                base_url = settings.get_url().rstrip("/")
                if repository_slug:
                    path = f"/rest/branch-permissions/2.0/projects/{project_key}/repos/{repository_slug}/restrictions"
                else:
                    path = f"/rest/branch-permissions/2.0/projects/{project_key}/restrictions"
                url = f"{base_url}{path}"
                params = {"start": start, "limit": limit}

            headers = {"Accept": "application/json"}
            auth = None

            if settings.token:
                headers["Authorization"] = f"Bearer {settings.token}"
            elif settings.username and settings.password:
                auth = (settings.username, settings.password)

            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    auth=auth,
                    timeout=self._timeout,
                )
            except requests.exceptions.Timeout as exc:
                raise TransportError(
                    f"Branch permissions request timed out: {exc}",
                    context={"url": url, "project_key": project_key, "repo": repository_slug},
                ) from exc
            except requests.exceptions.RequestException as exc:
                raise TransportError(
                    f"Branch permissions request failed: {exc}",
                    context={"url": url, "project_key": project_key, "repo": repository_slug},
                ) from exc

            status = response.status_code
            try:
                payload: Any = response.json() if response.content else {}
            except ValueError:
                payload = {"raw": response.text}

            if status in (401, 403):
                raise AuthError(
                    "Authentication failed while listing branch permissions",
                    context={"status_code": status, "response": payload},
                )
            if status == 404:
                raise NotFoundError(
                    "Branch permissions not found",
                    context={"status_code": status, "response": payload},
                )
            if status == 429:
                raise RateLimitError(
                    "Rate limited while listing branch permissions",
                    context={"status_code": status, "response": payload},
                )
            if status == 409:
                raise ConflictError(
                    "Conflict while listing branch permissions",
                    context={"status_code": status, "response": payload},
                )
            if status >= 500:
                raise ResponseError(
                    "Server error while listing branch permissions",
                    context={"status_code": status, "response": payload},
                )
            if status >= 400:
                raise VDSClientError(
                    "Failed to list branch permissions",
                    context={"status_code": status, "response": payload},
                )

            if isinstance(payload, dict):
                values = payload.get("values")
                return values if isinstance(values, list) else []
            if isinstance(payload, list):
                return payload
            return []

        result = self._with_retry(_fetch_permissions, f"list_branch_permissions {project_key}")
        self._log.debug(
            "branch_permissions_listed",
            project_key=project_key,
            repository_slug=repository_slug,
            count=len(result),
        )
        return result

    def get_branch_permission(
        self, project_key: str, permission_id: int, repository_slug: str | None = None
    ) -> dict[str, Any]:
        """Get a single branch permission by permission ID."""
        try:
            result = self._client.get_branch_permission(project_key, permission_id, repository_slug=repository_slug)
            self._log.debug(
                "branch_permission_retrieved",
                project_key=project_key,
                permission_id=permission_id,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_branch_permission {permission_id}")

    def delete_branch_permission(
        self, project_key: str, permission_id: int, repository_slug: str | None = None
    ) -> None:
        """Delete a single branch permission by permission ID."""
        try:
            self._client.delete_branch_permission(project_key, permission_id, repository_slug=repository_slug)
            self._log.info(
                "branch_permission_deleted",
                project_key=project_key,
                permission_id=permission_id,
                repository_slug=repository_slug,
            )
        except Exception as exc:
            self._handle_api_error(exc, f"delete_branch_permission {permission_id}")

    # Webhook Management (Bitbucket Cloud only)
    def list_webhooks(
        self,
        project_key: str,
        repository_slug: str,
        *,
        event: str | None = None,
        statistics: bool = False,
    ) -> list[dict[str, Any]]:
        """List repository webhooks."""
        try:
            result = self._client.get_webhooks(project_key, repository_slug, event=event, statistics=statistics)
            self._log.debug(
                "webhooks_listed",
                project_key=project_key,
                repository_slug=repository_slug,
                event=event,
                statistics=statistics,
                count=len(result) if isinstance(result, list) else 0,
            )
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            self._handle_api_error(exc, f"list_webhooks {project_key}/{repository_slug}")

    def get_webhook(self, project_key: str, repository_slug: str, webhook_id: int) -> dict[str, Any]:
        """Retrieve a specific webhook."""
        try:
            result = self._client.get_webhook(project_key, repository_slug, webhook_id)
            self._log.debug(
                "webhook_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                webhook_id=webhook_id,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_webhook {project_key}/{repository_slug}/{webhook_id}")

    def create_webhook(
        self,
        project_key: str,
        repository_slug: str,
        name: str,
        events: list[str],
        webhook_url: str,
        *,
        active: bool = True,
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Create a repository webhook."""
        try:
            result = self._client.create_webhook(
                project_key,
                repository_slug,
                name,
                events,
                webhook_url,
                active,
                secret=secret,
            )
            self._log.info(
                "webhook_created",
                project_key=project_key,
                repository_slug=repository_slug,
                name=name,
                events=events,
                active=active,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_webhook {project_key}/{repository_slug}")

    def update_webhook(
        self,
        project_key: str,
        repository_slug: str,
        webhook_id: int,
        *,
        name: str | None = None,
        events: list[str] | None = None,
        webhook_url: str | None = None,
        active: bool | None = None,
        secret: str | None = None,
    ) -> dict[str, Any]:
        """Update a repository webhook."""
        try:
            params: dict[str, Any] = {}
            if name is not None:
                params["name"] = name
            if events is not None:
                params["events"] = events
            if webhook_url is not None:
                params["url"] = webhook_url
            if active is not None:
                params["active"] = active
            if secret is not None:
                params["secret"] = secret

            result = self._client.update_webhook(project_key, repository_slug, webhook_id, **params)
            self._log.info(
                "webhook_updated",
                project_key=project_key,
                repository_slug=repository_slug,
                webhook_id=webhook_id,
                updated_fields=list(params.keys()),
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"update_webhook {project_key}/{repository_slug}/{webhook_id}")

    def delete_webhook(self, project_key: str, repository_slug: str, webhook_id: int) -> None:
        """Delete a repository webhook."""
        try:
            self._client.delete_webhook(project_key, repository_slug, webhook_id)
            self._log.info(
                "webhook_deleted",
                project_key=project_key,
                repository_slug=repository_slug,
                webhook_id=webhook_id,
            )
        except Exception as exc:
            self._handle_api_error(exc, f"delete_webhook {project_key}/{repository_slug}/{webhook_id}")

    # Conditions-Reviewers Management
    def get_project_conditions(self, project_key: str) -> list[dict[str, Any]]:
        """Get all project conditions with reviewers list."""
        try:
            result = self._client.get_project_conditions(project_key)
            self._log.debug("project_conditions_retrieved", project_key=project_key, count=len(result) if result else 0)
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_project_conditions {project_key}")

    def get_project_condition(self, project_key: str, condition_id: int) -> dict[str, Any]:
        """Get a project condition with reviewers list."""
        try:
            result = self._client.get_project_condition(project_key, condition_id)
            self._log.debug("project_condition_retrieved", project_key=project_key, condition_id=condition_id)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_project_condition {condition_id}")

    def create_project_condition(self, project_key: str, condition: dict[str, Any]) -> dict[str, Any]:
        """Create project condition with reviewers."""
        try:
            result = self._client.create_project_condition(project_key, condition)
            self._log.info("project_condition_created", project_key=project_key)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_project_condition {project_key}")

    def update_project_condition(
        self, project_key: str, condition: dict[str, Any], condition_id: int
    ) -> dict[str, Any]:
        """Update a project condition with reviewers."""
        try:
            result = self._client.update_project_condition(project_key, condition, condition_id)
            self._log.info("project_condition_updated", project_key=project_key, condition_id=condition_id)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"update_project_condition {condition_id}")

    def delete_project_condition(self, project_key: str, condition_id: int) -> None:
        """Delete a project condition."""
        try:
            self._client.delete_project_condition(project_key, condition_id)
            self._log.info("project_condition_deleted", project_key=project_key, condition_id=condition_id)
        except Exception as exc:
            self._handle_api_error(exc, f"delete_project_condition {condition_id}")

    def get_repo_conditions(self, project_key: str, repository_slug: str) -> list[dict[str, Any]]:
        """Get all repository conditions with reviewers list."""
        try:
            result = self._client.get_repo_conditions(project_key, repository_slug)
            self._log.debug(
                "repo_conditions_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                count=len(result) if result else 0,
            )
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_repo_conditions {project_key}/{repository_slug}")

    def get_repo_condition(self, project_key: str, repository_slug: str, condition_id: int) -> dict[str, Any]:
        """Get a repository condition with reviewers list."""
        try:
            result = self._client.get_repo_condition(project_key, repository_slug, condition_id)
            self._log.debug(
                "repo_condition_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                condition_id=condition_id,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_repo_condition {condition_id}")

    def create_repo_condition(
        self, project_key: str, repository_slug: str, condition: dict[str, Any]
    ) -> dict[str, Any]:
        """Create repository condition with reviewers."""
        try:
            result = self._client.create_repo_condition(project_key, repository_slug, condition)
            self._log.info("repo_condition_created", project_key=project_key, repository_slug=repository_slug)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"create_repo_condition {project_key}/{repository_slug}")

    def update_repo_condition(
        self, project_key: str, repository_slug: str, condition: dict[str, Any], condition_id: int
    ) -> dict[str, Any]:
        """Update a repository condition with reviewers."""
        try:
            result = self._client.update_repo_condition(project_key, repository_slug, condition, condition_id)
            self._log.info(
                "repo_condition_updated",
                project_key=project_key,
                repository_slug=repository_slug,
                condition_id=condition_id,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"update_repo_condition {condition_id}")

    def delete_repo_condition(self, project_key: str, repository_slug: str, condition_id: int) -> None:
        """Delete a repository condition."""
        try:
            self._client.delete_repo_condition(project_key, repository_slug, condition_id)
            self._log.info(
                "repo_condition_deleted",
                project_key=project_key,
                repository_slug=repository_slug,
                condition_id=condition_id,
            )
        except Exception as exc:
            self._handle_api_error(exc, f"delete_repo_condition {condition_id}")

    # Code Management
    def get_content_of_file(
        self, project_key: str, repository_slug: str, filename: str, at: str | None = None, markup: str | None = None
    ) -> str:
        """Get raw content of the file from repository."""
        try:
            result = self._client.get_content_of_file(project_key, repository_slug, filename, at=at, markup=markup)
            self._log.debug(
                "file_content_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                filename=filename,
            )
            # The upstream SDK may return bytes; normalize to text so CLI can write safely.
            if isinstance(result, bytes):
                return result.decode("utf-8", errors="replace")
            return str(result) if result is not None else ""
        except Exception as exc:
            self._handle_api_error(exc, f"get_content_of_file {filename}")

    def get_commits(
        self,
        project_key: str,
        repository_slug: str,
        hash_oldest: str | None = None,
        hash_newest: str | None = None,
        limit: int = 99999,
    ) -> list[dict[str, Any]]:
        """Get commit list from repository."""
        try:
            result = self._client.get_commits(project_key, repository_slug, hash_oldest, hash_newest, limit=limit)
            # atlassian-python-api returns a paged iterator; consuming it directly may fetch the
            # entire history even when `limit` is small. Cap local iteration to the requested limit.
            if isinstance(result, list):
                commits_list = result[:limit] if limit and limit > 0 else result
            elif result:
                commits_list = list(islice(result, limit)) if limit and limit > 0 else list(result)
            else:
                commits_list = []
            self._log.debug(
                "commits_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                count=len(commits_list),
            )
            return commits_list
        except Exception as exc:
            self._handle_api_error(exc, f"get_commits {project_key}/{repository_slug}")

    def get_diff(
        self, project_key: str, repository_slug: str, path: str, hash_oldest: str, hash_newest: str
    ) -> dict[str, Any]:
        """Get diff between two commits."""
        try:
            result = self._client.get_diff(project_key, repository_slug, path, hash_oldest, hash_newest)
            self._log.debug(
                "diff_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                path=path,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_diff {path}")

    def get_changelog(
        self, project_key: str, repository_slug: str, ref_from: str, ref_to: str, limit: int = 99999
    ) -> list[dict[str, Any]]:
        """Get change log between 2 refs."""
        try:
            result = self._client.get_changelog(project_key, repository_slug, ref_from, ref_to, limit=limit)
            # SDK may return a generator, convert to list first
            changelog_list = result if isinstance(result, list) else list(result) if result else []
            self._log.debug(
                "changelog_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                count=len(changelog_list),
            )
            return changelog_list
        except Exception as exc:
            self._handle_api_error(exc, f"get_changelog {project_key}/{repository_slug}")

    # Code Insights Operations (Cloud-only)
    def create_code_insights_report(
        self,
        project_key: str,
        repository_slug: str,
        commit_id: str,
        report_key: str,
        report_title: str,
        reporter: str,
        result: str,
        data: list[dict[str, Any]] | None = None,
        **report_params: Any,
    ) -> dict[str, Any]:
        """Create a Code Insights report.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            commit_id: Commit hash
            report_key: Unique report key
            report_title: Report title
            reporter: Reporter name
            result: Report result ('PASSED', 'FAILED', 'PENDING')
            data: Optional report data (list of data items)
            **report_params: Additional report parameters (e.g., report_type, details, link)
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code Insights is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            params: dict[str, Any] = {
                "reporter": reporter,
                "result": result,
            }
            if data:
                params["data"] = data
            params.update(report_params)

            result_obj = self._client.create_code_insights_report(
                project_key, repository_slug, commit_id, report_key, report_title, **params
            )
            self._log.info(
                "code_insights_report_created",
                project_key=project_key,
                repository_slug=repository_slug,
                commit_id=commit_id,
                report_key=report_key,
            )
            return result_obj
        except Exception as exc:
            self._handle_api_error(
                exc, f"create_code_insights_report {project_key}/{repository_slug}/{commit_id}/{report_key}"
            )

    def get_code_insights_report(
        self, project_key: str, repository_slug: str, commit_id: str, report_key: str
    ) -> dict[str, Any]:
        """Get a Code Insights report."""
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code Insights is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            result = self._client.get_code_insights_report(project_key, repository_slug, commit_id, report_key)
            self._log.debug(
                "code_insights_report_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                commit_id=commit_id,
                report_key=report_key,
            )
            return result
        except Exception as exc:
            self._handle_api_error(
                exc, f"get_code_insights_report {project_key}/{repository_slug}/{commit_id}/{report_key}"
            )

    def add_code_insights_annotations_to_report(
        self,
        project_key: str,
        repository_slug: str,
        commit_id: str,
        report_key: str,
        annotations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Add annotations to a Code Insights report."""
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code Insights is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            result = self._client.add_code_insights_annotations_to_report(
                project_key, repository_slug, commit_id, report_key, annotations
            )
            self._log.info(
                "code_insights_annotations_added",
                project_key=project_key,
                repository_slug=repository_slug,
                commit_id=commit_id,
                report_key=report_key,
                annotation_count=len(annotations),
            )
            return result
        except Exception as exc:
            self._handle_api_error(
                exc, f"add_code_insights_annotations_to_report {project_key}/{repository_slug}/{commit_id}/{report_key}"
            )

    def delete_code_insights_report(
        self, project_key: str, repository_slug: str, commit_id: str, report_key: str
    ) -> None:
        """Delete a Code Insights report."""
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code Insights is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            self._client.delete_code_insights_report(project_key, repository_slug, commit_id, report_key)
            self._log.info(
                "code_insights_report_deleted",
                project_key=project_key,
                repository_slug=repository_slug,
                commit_id=commit_id,
                report_key=report_key,
            )
        except Exception as exc:
            self._handle_api_error(
                exc, f"delete_code_insights_report {project_key}/{repository_slug}/{commit_id}/{report_key}"
            )

    # Repository Settings Operations
    def get_branching_model(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get branching model configuration."""
        try:
            result = self._client.get_branching_model(project_key, repository_slug)
            self._log.debug(
                "branching_model_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_branching_model {project_key}/{repository_slug}")

    def set_branching_model(self, project_key: str, repository_slug: str, model: dict[str, Any]) -> dict[str, Any]:
        """Set branching model configuration."""
        try:
            result = self._client.set_branching_model(project_key, repository_slug, model)
            self._log.info(
                "branching_model_set",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_branching_model {project_key}/{repository_slug}")

    def enable_branching_model(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Enable branching model."""
        try:
            result = self._client.enable_branching_model(project_key, repository_slug)
            self._log.info(
                "branching_model_enabled",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"enable_branching_model {project_key}/{repository_slug}")

    def disable_branching_model(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Disable branching model."""
        try:
            result = self._client.disable_branching_model(project_key, repository_slug)
            self._log.info(
                "branching_model_disabled",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"disable_branching_model {project_key}/{repository_slug}")

    def get_default_branch(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get default branch."""
        try:
            result = self._client.get_default_branch(project_key, repository_slug)
            self._log.debug(
                "default_branch_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_default_branch {project_key}/{repository_slug}")

    def set_default_branch(self, project_key: str, repository_slug: str, branch: str) -> dict[str, Any]:
        """Set default branch."""
        try:
            result = self._client.set_default_branch(project_key, repository_slug, branch)
            self._log.info(
                "default_branch_set",
                project_key=project_key,
                repository_slug=repository_slug,
                branch=branch,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_default_branch {project_key}/{repository_slug}")

    def get_repo_hook_settings(
        self,
        project_key: str,
        repository_slug: str,
        start: int = 0,
        limit: int | None = None,
        filter_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get repository hook settings."""
        try:
            result = self._client.all_repo_hook_settings(
                project_key, repository_slug, start=start, limit=limit, filter_type=filter_type
            )
            # SDK may return a generator, convert to list first
            hooks_list = result if isinstance(result, list) else list(result) if result else []
            self._log.debug(
                "repo_hook_settings_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                count=len(hooks_list),
            )
            return hooks_list
        except Exception as exc:
            self._handle_api_error(exc, f"get_repo_hook_settings {project_key}/{repository_slug}")

    def enable_repo_hook_settings(self, project_key: str, repository_slug: str, hook_key: str) -> dict[str, Any]:
        """Enable repository hook."""
        try:
            result = self._client.enable_repo_hook_settings(project_key, repository_slug, hook_key)
            self._log.info(
                "repo_hook_enabled",
                project_key=project_key,
                repository_slug=repository_slug,
                hook_key=hook_key,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"enable_repo_hook_settings {project_key}/{repository_slug}/{hook_key}")

    def disable_repo_hook_settings(self, project_key: str, repository_slug: str, hook_key: str) -> dict[str, Any]:
        """Disable repository hook."""
        try:
            result = self._client.disable_repo_hook_settings(project_key, repository_slug, hook_key)
            self._log.info(
                "repo_hook_disabled",
                project_key=project_key,
                repository_slug=repository_slug,
                hook_key=hook_key,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"disable_repo_hook_settings {project_key}/{repository_slug}/{hook_key}")

    def get_lfs_repo_status(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        """Get Git LFS repository status."""
        try:
            result = self._client.get_lfs_repo_status(project_key, repository_slug)
            self._log.debug(
                "lfs_repo_status_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_lfs_repo_status {project_key}/{repository_slug}")

    def set_lfs_repo_status(self, project_key: str, repository_slug: str, enabled: bool) -> dict[str, Any]:
        """Set Git LFS repository status."""
        try:
            result = self._client.set_lfs_repo_status(project_key, repository_slug, enabled)
            self._log.info(
                "lfs_repo_status_set",
                project_key=project_key,
                repository_slug=repository_slug,
                enabled=enabled,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"set_lfs_repo_status {project_key}/{repository_slug}")

    # Advanced Code Operations
    def get_file_list(
        self,
        project_key: str,
        repository_slug: str,
        sub_folder: str | None = None,
        query: str | None = None,
        start: int = 0,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get file list from repository.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            sub_folder: Optional subfolder path
            query: Optional query string for filtering
            start: Start index for pagination
            limit: Maximum number of results
        """
        try:
            result = self._client.get_file_list(
                project_key, repository_slug, sub_folder=sub_folder, query=query, start=start, limit=limit
            )
            self._log.debug(
                "file_list_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                sub_folder=sub_folder,
                count=len(result) if result else 0,
            )
            return result if isinstance(result, list) else [result] if result else []
        except Exception as exc:
            self._handle_api_error(exc, f"get_file_list {project_key}/{repository_slug}")

    def get_commit_info(
        self, project_key: str, repository_slug: str, commit: str, path: str | None = None
    ) -> dict[str, Any]:
        """Get commit information.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            commit: Commit hash
            path: Optional file path
        """
        try:
            result = self._client.get_commit_info(project_key, repository_slug, commit, path=path)
            self._log.debug(
                "commit_info_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                commit=commit,
                path=path,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_commit_info {project_key}/{repository_slug}/{commit}")

    def get_commit_changes(
        self,
        project_key: str,
        repository_slug: str,
        commit_id: str | None = None,
        hash_newest: str | None = None,
        merges: str = "include",
    ) -> dict[str, Any]:
        """Get commit changes.

        Args:
            project_key: Project key
            repository_slug: Repository slug
            commit_id: Commit ID (preferred)
            hash_newest: Newest commit hash (alternative to commit_id)
            merges: How to handle merges ('include', 'exclude', 'only')
        """
        try:
            result = self._client.get_commit_changes(
                project_key, repository_slug, hash_newest=hash_newest, merges=merges, commit_id=commit_id
            )
            self._log.debug(
                "commit_changes_retrieved",
                project_key=project_key,
                repository_slug=repository_slug,
                commit_id=commit_id,
                hash_newest=hash_newest,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"get_commit_changes {project_key}/{repository_slug}")

    def search_code(self, team: str, search_query: str, page: int = 1, limit: int = 10) -> dict[str, Any]:
        """Search code (Cloud-only).

        Args:
            team: Team/workspace name (Cloud only)
            search_query: Search query string
            page: Page number for pagination
            limit: Maximum number of results per page
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code search is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            result = self._client.search_code(team, search_query, page=page, limit=limit)
            self._log.debug(
                "code_search_performed",
                team=team,
                search_query=search_query,
                page=page,
            )
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"search_code {team}")

    def search_code_advanced(
        self,
        team: str,
        search_query: str,
        *,
        page: int = 1,
        limit: int = 10,
        repository: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Advanced code search with additional filters (Cloud-only).

        Args:
            team: Team/workspace name (Cloud only)
            search_query: Search query string
            page: Page number for pagination (default: 1)
            limit: Maximum number of results per page (default: 10)
            repository: Optional repository slug to filter by
            **kwargs: Additional search parameters (if supported by SDK)

        Note: Code search is only available in Bitbucket Cloud. Server/DC instances
        do not have code search capabilities via the REST API.
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Code search is only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            # SDK search_code may support additional parameters via kwargs
            result = self._client.search_code(team, search_query, page=page, limit=limit, **kwargs)  # type: ignore[call-arg]
            self._log.debug(
                "code_search_advanced_performed",
                team=team,
                search_query=search_query,
                page=page,
                limit=limit,
                repository=repository,
            )
            # If repository filter is provided, filter results client-side
            # (SDK may not support repository parameter directly)
            if repository and isinstance(result, dict) and "values" in result:
                filtered = [
                    item for item in result.get("values", []) if item.get("repository", {}).get("slug") == repository
                ]
                result["values"] = filtered
                result["size"] = len(filtered)
            return result
        except Exception as exc:
            self._handle_api_error(exc, f"search_code_advanced {team}")

    def _get_cloud_repository(self, workspace: str, repository_slug: str):
        """Retrieve a repository object using the cloud API."""
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Repository variable operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            return self._client.cloud.repositories.get(workspace, repository_slug)  # type: ignore[attr-defined]
        except Exception as exc:
            self._handle_api_error(exc, f"cloud_repository {workspace}/{repository_slug}")

    # --- Repository Variables (Cloud-only) ---
    @staticmethod
    def _variable_to_dict(variable: Any) -> dict[str, Any]:
        """Convert a repository variable object or dict to a plain dictionary."""
        data = getattr(variable, "data", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            return dict(data)
        if isinstance(variable, dict):
            return dict(variable)
        return {}

    @staticmethod
    def _deployment_environment_to_dict(environment: Any) -> dict[str, Any]:
        """Convert a deployment environment object to a dict."""
        data = getattr(environment, "data", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            return dict(data)
        if isinstance(environment, dict):
            return dict(environment)
        return {}

    @staticmethod
    def _issue_to_dict(issue: Any) -> dict[str, Any]:
        """Convert an issue object to a dict."""
        data = getattr(issue, "data", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            return dict(data)
        if isinstance(issue, dict):
            return dict(issue)
        return {}

    def _get_pull_request(
        self,
        workspace: str,
        repository_slug: str,
        pull_request_id: str | int,
    ):
        """Retrieve a pull request object."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            return repository.pullrequests.get(pull_request_id)  # type: ignore[attr-defined]
        except Exception as exc:
            self._handle_api_error(exc, f"pull_request {workspace}/{repository_slug}/{pull_request_id}")

    def _get_issue(
        self,
        workspace: str,
        repository_slug: str,
        issue_id: str | int,
    ):
        """Retrieve an issue object."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            return repository.issues.get(issue_id)  # type: ignore[attr-defined]
        except Exception as exc:
            self._handle_api_error(exc, f"repository_issue {workspace}/{repository_slug}/{issue_id}")

    @staticmethod
    def _pipeline_to_dict(pipeline: Any) -> dict[str, Any]:
        """Convert a pipeline object to a plain dictionary."""
        data = getattr(pipeline, "data", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            return dict(data)
        if isinstance(pipeline, dict):
            return dict(pipeline)
        return {}

    @staticmethod
    def _pipeline_step_to_dict(step: Any) -> dict[str, Any]:
        """Convert a pipeline step object to a plain dictionary."""
        data = getattr(step, "data", None)
        if callable(data):
            data = data()
        if isinstance(data, dict):
            return dict(data)
        if isinstance(step, dict):
            return dict(step)
        return {}

    def list_repository_variables(self, workspace: str, repository_slug: str) -> list[dict[str, Any]]:
        """List repository variables."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            variables = [
                self._variable_to_dict(variable)
                for variable in repository.repository_variables.each()  # type: ignore[attr-defined]
            ]
            self._log.debug(
                "repo_variables_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                count=len(variables),
            )
            return variables
        except Exception as exc:
            self._handle_api_error(exc, f"list_repository_variables {workspace}/{repository_slug}")

    def get_repository_variable(self, workspace: str, repository_slug: str, variable_uuid: str) -> dict[str, Any]:
        """Get a repository variable by UUID."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            variable = repository.repository_variables.get(variable_uuid)  # type: ignore[attr-defined]
            data = self._variable_to_dict(variable)
            self._log.debug(
                "repo_variable_retrieved",
                workspace=workspace,
                repository_slug=repository_slug,
                variable_uuid=variable_uuid,
            )
            return data
        except Exception as exc:
            self._handle_api_error(exc, f"get_repository_variable {workspace}/{repository_slug}/{variable_uuid}")

    def create_repository_variable(
        self,
        workspace: str,
        repository_slug: str,
        key: str,
        value: str,
        secured: bool = False,
    ) -> dict[str, Any]:
        """Create a repository variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            variable = repository.repository_variables.create(key, value, secured)  # type: ignore[attr-defined]
            data = self._variable_to_dict(variable)
            self._log.info(
                "repo_variable_created",
                workspace=workspace,
                repository_slug=repository_slug,
                key=key,
                secured=secured,
            )
            return data
        except Exception as exc:
            self._handle_api_error(exc, f"create_repository_variable {workspace}/{repository_slug}")

    def update_repository_variable(
        self,
        workspace: str,
        repository_slug: str,
        variable_uuid: str,
        *,
        key: str | None = None,
        value: str | None = None,
        secured: bool | None = None,
    ) -> dict[str, Any]:
        """Update a repository variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        update_payload: dict[str, Any] = {}
        if key is not None:
            update_payload["key"] = key
        if value is not None:
            update_payload["value"] = value
        if secured is not None:
            update_payload["secured"] = secured
        if not update_payload:
            raise VDSClientError(
                "Provide at least one of --key/--value/--secured to update repository variable",
                context={"workspace": workspace, "repository": repository_slug, "variable_uuid": variable_uuid},
            )
        try:
            variable = repository.repository_variables.get(variable_uuid)  # type: ignore[attr-defined]
            variable.update(**update_payload)  # type: ignore[attr-defined]
            data = self._variable_to_dict(variable)
            self._log.info(
                "repo_variable_updated",
                workspace=workspace,
                repository_slug=repository_slug,
                variable_uuid=variable_uuid,
                fields=list(update_payload.keys()),
            )
            return data
        except Exception as exc:
            self._handle_api_error(exc, f"update_repository_variable {workspace}/{repository_slug}/{variable_uuid}")

    def delete_repository_variable(self, workspace: str, repository_slug: str, variable_uuid: str) -> None:
        """Delete a repository variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            variable = repository.repository_variables.get(variable_uuid)  # type: ignore[attr-defined]
            variable.delete()  # type: ignore[attr-defined]
            self._log.info(
                "repo_variable_deleted",
                workspace=workspace,
                repository_slug=repository_slug,
                variable_uuid=variable_uuid,
            )
        except Exception as exc:
            self._handle_api_error(exc, f"delete_repository_variable {workspace}/{repository_slug}/{variable_uuid}")

    # --- Deployment Environments (Cloud-only) ---
    def list_deployment_environments(self, workspace: str, repository_slug: str) -> list[dict[str, Any]]:
        """List deployment environments."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            environments = [
                self._deployment_environment_to_dict(env)
                for env in repository.deployment_environments.each()  # type: ignore[attr-defined]
            ]
            self._log.debug(
                "deployment_environments_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                count=len(environments),
            )
            return environments
        except Exception as exc:
            self._handle_api_error(exc, f"list_deployment_environments {workspace}/{repository_slug}")

    def get_deployment_environment(self, workspace: str, repository_slug: str, environment_uuid: str) -> dict[str, Any]:
        """Retrieve a deployment environment."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            environment = repository.deployment_environments.get(environment_uuid)  # type: ignore[attr-defined]
            data = self._deployment_environment_to_dict(environment)
            self._log.debug(
                "deployment_environment_retrieved",
                workspace=workspace,
                repository_slug=repository_slug,
                environment_uuid=environment_uuid,
            )
            return data
        except Exception as exc:
            self._handle_api_error(exc, f"get_deployment_environment {workspace}/{repository_slug}/{environment_uuid}")

    def list_deployment_environment_variables(
        self,
        workspace: str,
        repository_slug: str,
        environment_uuid: str,
        *,
        pagelen: int = 10,
    ) -> list[dict[str, Any]]:
        """List variables for a deployment environment."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            environment = repository.deployment_environments.get(environment_uuid)  # type: ignore[attr-defined]
            variables = [
                self._variable_to_dict(variable)
                for variable in environment.deployment_environment_variables.each(pagelen=pagelen)  # type: ignore[attr-defined]
            ]
            self._log.debug(
                "deployment_env_variables_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                environment_uuid=environment_uuid,
                count=len(variables),
            )
            return variables
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"list_deployment_environment_variables {workspace}/{repository_slug}/{environment_uuid}",
            )

    def create_deployment_environment_variable(
        self,
        workspace: str,
        repository_slug: str,
        environment_uuid: str,
        key: str,
        value: str,
        secured: bool = False,
    ) -> dict[str, Any]:
        """Create a deployment environment variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            environment = repository.deployment_environments.get(environment_uuid)  # type: ignore[attr-defined]
            variable = environment.deployment_environment_variables.create(key, value, secured)  # type: ignore[attr-defined]
            data = self._variable_to_dict(variable)
            self._log.info(
                "deployment_env_variable_created",
                workspace=workspace,
                repository_slug=repository_slug,
                environment_uuid=environment_uuid,
                key=key,
                secured=secured,
            )
            return data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"create_deployment_environment_variable {workspace}/{repository_slug}/{environment_uuid}",
            )

    def update_deployment_environment_variable(
        self,
        workspace: str,
        repository_slug: str,
        environment_uuid: str,
        variable_uuid: str,
        *,
        key: str | None = None,
        value: str | None = None,
        secured: bool | None = None,
    ) -> dict[str, Any]:
        """Update a deployment environment variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        update_payload: dict[str, Any] = {}
        if key is not None:
            update_payload["key"] = key
        if value is not None:
            update_payload["value"] = value
        if secured is not None:
            update_payload["secured"] = secured
        if not update_payload:
            raise VDSClientError(
                "Provide at least one of --key/--value/--secured to update deployment environment variable",
                context={
                    "workspace": workspace,
                    "repository": repository_slug,
                    "environment_uuid": environment_uuid,
                    "variable_uuid": variable_uuid,
                },
            )
        try:
            environment = repository.deployment_environments.get(environment_uuid)  # type: ignore[attr-defined]
            variable = environment.deployment_environment_variables.get(variable_uuid)  # type: ignore[attr-defined]
            variable.update(**update_payload)  # type: ignore[attr-defined]
            data = self._variable_to_dict(variable)
            self._log.info(
                "deployment_env_variable_updated",
                workspace=workspace,
                repository_slug=repository_slug,
                environment_uuid=environment_uuid,
                variable_uuid=variable_uuid,
                fields=list(update_payload.keys()),
            )
            return data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"update_deployment_environment_variable {workspace}/{repository_slug}/{environment_uuid}/{variable_uuid}",
            )

    def delete_deployment_environment_variable(
        self,
        workspace: str,
        repository_slug: str,
        environment_uuid: str,
        variable_uuid: str,
    ) -> None:
        """Delete a deployment environment variable."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            environment = repository.deployment_environments.get(environment_uuid)  # type: ignore[attr-defined]
            variable = environment.deployment_environment_variables.get(variable_uuid)  # type: ignore[attr-defined]
            variable.delete()  # type: ignore[attr-defined]
            self._log.info(
                "deployment_env_variable_deleted",
                workspace=workspace,
                repository_slug=repository_slug,
                environment_uuid=environment_uuid,
                variable_uuid=variable_uuid,
            )
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"delete_deployment_environment_variable {workspace}/{repository_slug}/{environment_uuid}/{variable_uuid}",
            )

    # --- Repository Issues (Cloud-only) ---
    def list_repository_issues(
        self,
        workspace: str,
        repository_slug: str,
        *,
        query: str | None = None,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        """List repository issues."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            issues = [
                self._issue_to_dict(issue)
                for issue in repository.issues.each(q=query, sort=sort)  # type: ignore[attr-defined]
            ]
            self._log.debug(
                "repository_issues_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                count=len(issues),
                query=query,
                sort=sort,
            )
            return issues
        except Exception as exc:
            self._handle_api_error(exc, f"list_repository_issues {workspace}/{repository_slug}")

    def create_repository_issue(
        self,
        workspace: str,
        repository_slug: str,
        title: str,
        description: str = "",
        *,
        kind: str = "task",
        priority: str = "major",
    ) -> dict[str, Any]:
        """Create an issue."""
        if not title:
            raise VDSClientError(
                "Issue title must not be empty",
                context={"workspace": workspace, "repository": repository_slug},
            )
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            issue = repository.issues.create(title, description, kind, priority)  # type: ignore[attr-defined]
            issue_data = self._issue_to_dict(issue)
            self._log.info(
                "repository_issue_created",
                workspace=workspace,
                repository_slug=repository_slug,
                issue_id=issue_data.get("id"),
                kind=kind,
                priority=priority,
            )
            return issue_data
        except Exception as exc:
            self._handle_api_error(exc, f"create_repository_issue {workspace}/{repository_slug}")

    def get_repository_issue(
        self,
        workspace: str,
        repository_slug: str,
        issue_id: str | int,
    ) -> dict[str, Any]:
        """Get a single issue."""
        issue = self._get_issue(workspace, repository_slug, issue_id)
        data = self._issue_to_dict(issue)
        self._log.debug(
            "repository_issue_retrieved",
            workspace=workspace,
            repository_slug=repository_slug,
            issue_id=issue_id,
        )
        return data

    def update_repository_issue(
        self,
        workspace: str,
        repository_slug: str,
        issue_id: str | int,
        *,
        title: str | None = None,
        description: str | None = None,
        kind: str | None = None,
        priority: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any]:
        """Update an issue."""
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if kind is not None:
            payload["kind"] = kind
        if priority is not None:
            payload["priority"] = priority
        if state is not None:
            payload["state"] = state
        if description is not None:
            payload["content"] = {"raw": description}
        if not payload:
            raise VDSClientError(
                "Provide at least one field to update issue",
                context={
                    "workspace": workspace,
                    "repository": repository_slug,
                    "issue_id": issue_id,
                },
            )
        issue = self._get_issue(workspace, repository_slug, issue_id)
        try:
            issue.update(**payload)  # type: ignore[attr-defined]
            data = self._issue_to_dict(issue)
            self._log.info(
                "repository_issue_updated",
                workspace=workspace,
                repository_slug=repository_slug,
                issue_id=issue_id,
                fields=list(payload.keys()),
            )
            return data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"update_repository_issue {workspace}/{repository_slug}/{issue_id}",
            )

    def delete_repository_issue(
        self,
        workspace: str,
        repository_slug: str,
        issue_id: str | int,
    ) -> None:
        """Delete an issue."""
        issue = self._get_issue(workspace, repository_slug, issue_id)
        try:
            issue.delete()  # type: ignore[attr-defined]
            self._log.info(
                "repository_issue_deleted",
                workspace=workspace,
                repository_slug=repository_slug,
                issue_id=issue_id,
            )
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"delete_repository_issue {workspace}/{repository_slug}/{issue_id}",
            )

    # --- Pull Request Blockers (Cloud-only) ---
    def list_pull_request_blockers(
        self,
        workspace: str,
        repository_slug: str,
        pull_request_id: str | int,
        *,
        query: str | None = None,
    ) -> list[dict[str, Any]]:
        """List pull request blockers."""
        pull_request = self._get_pull_request(workspace, repository_slug, pull_request_id)
        params = {"q": query} if query else None
        try:
            result = pull_request.get("blockers", params=params)  # type: ignore[attr-defined]
            if isinstance(result, dict) and "values" in result:
                blockers = result.get("values", [])
            elif isinstance(result, list):
                blockers = result
            else:
                blockers = [result] if result else []
            blockers_data = [self._variable_to_dict(blocker) for blocker in blockers]
            self._log.debug(
                "pull_request_blockers_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                pull_request_id=pull_request_id,
                count=len(blockers_data),
                query=query,
            )
            return blockers_data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"list_pull_request_blockers {workspace}/{repository_slug}/{pull_request_id}",
            )

    def add_pull_request_blocker(
        self,
        workspace: str,
        repository_slug: str,
        pull_request_id: str | int,
        message: str,
        *,
        reason: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Add a blocker to a pull request."""
        if not message:
            raise VDSClientError(
                "Blocker message must not be empty",
                context={
                    "workspace": workspace,
                    "repository": repository_slug,
                    "pull_request_id": pull_request_id,
                },
            )
        pull_request = self._get_pull_request(workspace, repository_slug, pull_request_id)
        payload: dict[str, Any] = {"message": message}
        if reason:
            payload["reason"] = reason
        if severity:
            payload["severity"] = severity
        try:
            blocker = pull_request.post("blockers", payload)  # type: ignore[attr-defined]
            blocker_data = self._variable_to_dict(blocker)
            self._log.info(
                "pull_request_blocker_added",
                workspace=workspace,
                repository_slug=repository_slug,
                pull_request_id=pull_request_id,
                blocker_uuid=blocker_data.get("uuid"),
            )
            return blocker_data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"add_pull_request_blocker {workspace}/{repository_slug}/{pull_request_id}",
            )

    def delete_pull_request_blocker(
        self,
        workspace: str,
        repository_slug: str,
        pull_request_id: str | int,
        blocker_uuid: str,
    ) -> None:
        """Delete a pull request blocker."""
        if not blocker_uuid:
            raise VDSClientError(
                "Blocker UUID is required",
                context={
                    "workspace": workspace,
                    "repository": repository_slug,
                    "pull_request_id": pull_request_id,
                },
            )
        pull_request = self._get_pull_request(workspace, repository_slug, pull_request_id)
        try:
            pull_request.delete(f"blockers/{blocker_uuid}")  # type: ignore[attr-defined]
            self._log.info(
                "pull_request_blocker_deleted",
                workspace=workspace,
                repository_slug=repository_slug,
                pull_request_id=pull_request_id,
                blocker_uuid=blocker_uuid,
            )
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"delete_pull_request_blocker {workspace}/{repository_slug}/{pull_request_id}/{blocker_uuid}",
            )

    def _get_pipeline(self, workspace: str, repository_slug: str, pipeline_uuid: str):
        """Retrieve a pipeline object using the cloud API."""
        repository = self._get_cloud_repository(workspace, repository_slug)
        try:
            return repository.pipelines.get(pipeline_uuid)  # type: ignore[attr-defined]
        except Exception as exc:
            self._handle_api_error(exc, f"pipeline {workspace}/{repository_slug}/{pipeline_uuid}")

    def get_pipeline(self, workspace: str, repository_slug: str, pipeline_uuid: str) -> dict[str, Any]:
        """Get pipeline details."""
        pipeline = self._get_pipeline(workspace, repository_slug, pipeline_uuid)
        data = self._pipeline_to_dict(pipeline)
        self._log.debug(
            "pipeline_retrieved",
            workspace=workspace,
            repository_slug=repository_slug,
            pipeline_uuid=pipeline_uuid,
        )
        return data

    def list_pipeline_steps(
        self,
        workspace: str,
        repository_slug: str,
        pipeline_uuid: str,
    ) -> list[dict[str, Any]]:
        """List steps for a pipeline."""
        pipeline = self._get_pipeline(workspace, repository_slug, pipeline_uuid)
        try:
            steps = [
                self._pipeline_step_to_dict(step)
                for step in pipeline.steps()  # type: ignore[attr-defined]
            ]
            self._log.debug(
                "pipeline_steps_listed",
                workspace=workspace,
                repository_slug=repository_slug,
                pipeline_uuid=pipeline_uuid,
                count=len(steps),
            )
            return steps
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"list_pipeline_steps {workspace}/{repository_slug}/{pipeline_uuid}",
            )

    def get_pipeline_step(
        self,
        workspace: str,
        repository_slug: str,
        pipeline_uuid: str,
        step_uuid: str,
    ) -> dict[str, Any]:
        """Get details for a pipeline step."""
        pipeline = self._get_pipeline(workspace, repository_slug, pipeline_uuid)
        try:
            step = pipeline.step(step_uuid)  # type: ignore[attr-defined]
            data = self._pipeline_step_to_dict(step)
            self._log.debug(
                "pipeline_step_retrieved",
                workspace=workspace,
                repository_slug=repository_slug,
                pipeline_uuid=pipeline_uuid,
                step_uuid=step_uuid,
            )
            return data
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"get_pipeline_step {workspace}/{repository_slug}/{pipeline_uuid}/{step_uuid}",
            )

    def get_pipeline_step_log(
        self,
        workspace: str,
        repository_slug: str,
        pipeline_uuid: str,
        step_uuid: str,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> dict[str, Any]:
        """Get log output for a pipeline step."""
        pipeline = self._get_pipeline(workspace, repository_slug, pipeline_uuid)
        try:
            step = pipeline.step(step_uuid)  # type: ignore[attr-defined]
            result = step.log(start=start, end=end)  # type: ignore[attr-defined]
            total_size: int | None = None
            content_bytes: bytes = b""
            if isinstance(result, tuple):
                total_size_raw, chunk = result
                if isinstance(total_size_raw, (bytes, bytearray)):
                    try:
                        total_size = int(total_size_raw.decode())
                    except (ValueError, AttributeError):
                        total_size = None
                else:
                    try:
                        total_size = int(total_size_raw)
                    except (ValueError, TypeError):
                        total_size = None
                content_bytes = chunk or b""
            elif isinstance(result, (bytes, bytearray)):
                content_bytes = bytes(result)
            elif result is None:
                content_bytes = b""
            else:
                # Unknown type, attempt to convert to bytes
                try:
                    content_bytes = bytes(result)
                except Exception:  # pragma: no cover - defensive
                    content_bytes = str(result).encode("utf-8", errors="replace")

            content_text = content_bytes.decode("utf-8", errors="replace")
            size = total_size if total_size is not None else len(content_bytes)
            payload = {
                "workspace": workspace,
                "repository": repository_slug,
                "pipeline_uuid": pipeline_uuid,
                "step_uuid": step_uuid,
                "size": size,
                "content": content_text,
                "range_start": start,
                "range_end": end,
            }
            self._log.debug(
                "pipeline_step_log_retrieved",
                workspace=workspace,
                repository_slug=repository_slug,
                pipeline_uuid=pipeline_uuid,
                step_uuid=step_uuid,
                size=size,
            )
            return payload
        except Exception as exc:
            self._handle_api_error(
                exc,
                f"get_pipeline_step_log {workspace}/{repository_slug}/{pipeline_uuid}/{step_uuid}",
            )

    def stop_pipeline(
        self,
        workspace: str,
        repository_slug: str,
        pipeline_uuid: str,
    ) -> dict[str, Any]:
        """Stop a running pipeline."""
        pipeline = self._get_pipeline(workspace, repository_slug, pipeline_uuid)
        try:
            pipeline.stop()  # type: ignore[attr-defined]
            self._log.info(
                "pipeline_stopped",
                workspace=workspace,
                repository_slug=repository_slug,
                pipeline_uuid=pipeline_uuid,
            )
            return {
                "workspace": workspace,
                "repository": repository_slug,
                "pipeline_uuid": pipeline_uuid,
                "status": "stopped",
            }
        except Exception as exc:
            self._handle_api_error(exc, f"stop_pipeline {workspace}/{repository_slug}/{pipeline_uuid}")

    # --- Cloud Workspace Operations (Cloud-only) ---
    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces (Cloud-only).

        Returns:
            List of workspace dictionaries
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            # Access cloud API: cloud.workspaces.each()
            workspaces = list(self._client.cloud.workspaces.each())  # type: ignore[attr-defined]
            self._log.debug("workspaces_listed", count=len(workspaces))
            return workspaces
        except Exception as exc:
            self._handle_api_error(exc, "list_workspaces")

    def get_workspace(self, workspace_slug: str) -> dict[str, Any]:
        """Get workspace by slug (Cloud-only).

        Args:
            workspace_slug: Workspace slug/identifier
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            # Access cloud API: cloud.workspaces.get(workspace_slug)
            workspace = self._client.cloud.workspaces.get(workspace_slug)  # type: ignore[attr-defined]
            self._log.debug("workspace_retrieved", workspace_slug=workspace_slug)
            return workspace
        except Exception as exc:
            self._handle_api_error(exc, f"get_workspace {workspace_slug}")

    def get_workspace_permissions(self, workspace_slug: str) -> list[dict[str, Any]]:
        """Get workspace permissions (Cloud-only).

        Args:
            workspace_slug: Workspace slug/identifier
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            workspace = self._client.cloud.workspaces.get(workspace_slug)  # type: ignore[attr-defined]
            # Access: workplace.permissions.each()
            permissions = list(workspace.permissions.each())  # type: ignore[attr-defined]
            self._log.debug("workspace_permissions_retrieved", workspace_slug=workspace_slug, count=len(permissions))
            return permissions
        except Exception as exc:
            self._handle_api_error(exc, f"get_workspace_permissions {workspace_slug}")

    def get_workspace_repository_permissions(
        self, workspace_slug: str, repo_slug: str | None = None
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Get workspace repository permissions (Cloud-only).

        Args:
            workspace_slug: Workspace slug/identifier
            repo_slug: Optional repository slug. If provided, returns permissions for that repo only.
                      If None, returns all repository permissions.
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            workspace = self._client.cloud.workspaces.get(workspace_slug)  # type: ignore[attr-defined]
            if repo_slug:
                # Access: workplace.permissions.repositories(repo_slug)
                permissions = workspace.permissions.repositories(repo_slug)  # type: ignore[attr-defined]
            else:
                # Access: workplace.permissions.repositories()
                permissions = list(workspace.permissions.repositories())  # type: ignore[attr-defined]
            self._log.debug(
                "workspace_repository_permissions_retrieved",
                workspace_slug=workspace_slug,
                repo_slug=repo_slug,
                is_list=repo_slug is None,
            )
            return permissions
        except Exception as exc:
            self._handle_api_error(exc, f"get_workspace_repository_permissions {workspace_slug}/{repo_slug}")

    def list_workspace_projects(self, workspace_slug: str) -> list[dict[str, Any]]:
        """List projects in workspace (Cloud-only).

        Args:
            workspace_slug: Workspace slug/identifier
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            workspace = self._client.cloud.workspaces.get(workspace_slug)  # type: ignore[attr-defined]
            # Access: workplace.projects.each()
            projects = list(workspace.projects.each())  # type: ignore[attr-defined]
            self._log.debug("workspace_projects_listed", workspace_slug=workspace_slug, count=len(projects))
            return projects
        except Exception as exc:
            self._handle_api_error(exc, f"list_workspace_projects {workspace_slug}")

    def get_workspace_project(self, workspace_slug: str, project_key: str) -> dict[str, Any]:
        """Get project from workspace (Cloud-only).

        Args:
            workspace_slug: Workspace slug/identifier
            project_key: Project key
        """
        if not self._settings.is_cloud_mode:
            raise VDSClientError(
                "Workspace operations are only available in Bitbucket Cloud mode",
                context={"mode": self._settings.mode},
            )
        try:
            workspace = self._client.cloud.workspaces.get(workspace_slug)  # type: ignore[attr-defined]
            # Access: workplace.projects.get(project_key)
            project = workspace.projects.get(project_key)  # type: ignore[attr-defined]
            self._log.debug("workspace_project_retrieved", workspace_slug=workspace_slug, project_key=project_key)
            return project
        except Exception as exc:
            self._handle_api_error(exc, f"get_workspace_project {workspace_slug}/{project_key}")

    def download_archive(
        self,
        project_key: str,
        repo_slug: str,
        dest_fd: Any,
        *,
        at: str | None = None,
        format: str = "zip",
        path: str | None = None,
        prefix: str | None = None,
        chunk_size: int = 8192,
    ) -> None:
        """Download a repository archive to a file-like object.

        Args:
            project_key: Bitbucket project key.
            repo_slug: Repository slug.
            dest_fd: Writable binary file-like object (e.g. open file or BytesIO).
            at: Commit/tag/branch reference (optional).
            format: Archive format — "zip", "tar.gz", "tar", "tgz" (default "zip").
            path: Limit archive to a specific path prefix (optional).
            prefix: Custom top-level directory prefix inside the archive (optional).
            chunk_size: Bytes per read chunk (default 8192).
        """
        try:
            self._client.download_repo_archive(
                project_key=project_key,
                repository_slug=repo_slug,
                dest_fd=dest_fd,
                at=at,
                format=format,
                path=path,
                prefix=prefix,
                chunk_size=chunk_size,
            )
        except Exception as exc:
            raise VDSClientError(str(exc)) from exc

    def close(self) -> None:
        """Close client (cleanup method for compatibility)."""
        # atlassian-python-api doesn't require explicit cleanup
        pass

    def __enter__(self) -> BitbucketClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["BitbucketClient"]
