"""Factory functions for creating Bitbucket clients with automatic credential loading.

This module provides convenient factory functions that automatically load credentials
from the shared VDS environment loader (`vds_cli_common.env`), simplifying client instantiation.

Usage:
    from vds_bitbucket_orchestrator import create_client, create_async_client

    # Create a sync client with auto-loaded credentials
    client = create_client()

    # Create a sync client with explicit mode
    client = create_client(mode="cloud")

    # Create an async client for non-blocking operations
    async_client = create_async_client()

References:
    - FR-21.2.2: Factory functions that load credentials from the shared VDS env file automatically
    - FR-21.2.3: AsyncBitbucketClient using asyncio.to_thread()
    - TSK-223: Factory functions for Bitbucket
    - TSK-225: Async Bitbucket wrapper
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from vds_cli_common.paths import get_shared_env_path

from .async_client import AsyncBitbucketClient
from .client import BitbucketClient
from .config import load_settings

# Default path for the shared VDS environment file
DEFAULT_VDS_ENV_PATH = get_shared_env_path()


def create_client(
    *,
    mode: Literal["server", "cloud"] | None = None,
    env_path: Path | None = None,
    timeout: int | None = 30,
    strict: bool = True,
) -> BitbucketClient:
    """Create a Bitbucket client with auto-loaded credentials from the shared VDS env file.

    This factory function simplifies client creation by automatically loading
    credentials from the standard VDS environment file location.

    Args:
        mode: Bitbucket mode - 'server' (default) for Bitbucket Server/DC,
              'cloud' for Bitbucket Cloud. If None, uses value from env file
              or defaults to 'server'.
        env_path: Optional custom path to .env file. Defaults to the shared VDS env path.
        timeout: HTTP timeout in seconds (default: 30).
        strict: If True (default), validates that credentials are present.
                Set to False to allow creating client without validation.

    Returns:
        BitbucketClient: Configured Bitbucket client instance.

    Raises:
        ValueError: If strict=True and credentials are missing.
        SettingsError: If environment configuration cannot be loaded.

    Example:
        # Simple usage with defaults (server mode, shared VDS env path)
        client = create_client()

        # Cloud mode
        client = create_client(mode="cloud")

        # Custom env file
        client = create_client(env_path=Path("/custom/path/.env"))

        # Non-strict mode (for testing)
        client = create_client(strict=False)

    Note:
        The client implements BitbucketFullClient protocol, enabling type-safe
        dependency injection:

            def audit_repo(client: BitbucketFullClient, project: str, repo: str):
                return client.get_repository(project, repo)

            client = create_client()
            result = audit_repo(client, "INS", "insurance-core")
    """
    # Build overrides dict for mode if specified
    overrides: dict[str, str] | None = None
    if mode is not None:
        overrides = {"BITBUCKET_MODE": mode}

    # Load settings from env file with optional overrides
    settings = load_settings(
        env_path=env_path or DEFAULT_VDS_ENV_PATH,
        overrides=overrides,
        strict=strict,
    )

    # Create and return the client
    return BitbucketClient(settings, timeout=timeout)


def create_async_client(
    *,
    mode: Literal["server", "cloud"] | None = None,
    env_path: Path | None = None,
    timeout: int | None = 30,
    strict: bool = True,
) -> AsyncBitbucketClient:
    """Create an async Bitbucket client with auto-loaded credentials from the shared VDS env file.

    This factory function creates an AsyncBitbucketClient that wraps the synchronous
    BitbucketClient methods using asyncio.to_thread() for non-blocking execution.

    Args:
        mode: Bitbucket mode - 'server' (default) for Bitbucket Server/DC,
              'cloud' for Bitbucket Cloud. If None, uses value from env file
              or defaults to 'server'.
        env_path: Optional custom path to .env file. Defaults to the shared VDS env path.
        timeout: HTTP timeout in seconds (default: 30).
        strict: If True (default), validates that credentials are present.
                Set to False to allow creating client without validation.

    Returns:
        AsyncBitbucketClient: Async Bitbucket client instance.

    Raises:
        ValueError: If strict=True and credentials are missing.
        SettingsError: If environment configuration cannot be loaded.

    Example:
        import asyncio
        from vds_bitbucket_orchestrator import create_async_client

        async def audit_repos():
            client = create_async_client()

            # Non-blocking API calls
            repos = await client.list_repositories("INS")

            # Concurrent API calls
            repo_info, branches = await asyncio.gather(
                client.get_repository("INS", "insurance-core"),
                client.get_branches("INS", "insurance-core"),
            )
            return repos, repo_info, branches

        # Run the async function
        result = asyncio.run(audit_repos())

    Note:
        The AsyncBitbucketClient implements the same protocols as BitbucketClient:
        - BitbucketRepositoryClient
        - BitbucketBranchClient
        - BitbucketCodeClient
        - BitbucketFullClient

        The underlying HTTP calls are synchronous but run in a thread pool,
        preventing them from blocking the async event loop.
    """
    # Build overrides dict for mode if specified
    overrides: dict[str, str] | None = None
    if mode is not None:
        overrides = {"BITBUCKET_MODE": mode}

    # Load settings from env file with optional overrides
    settings = load_settings(
        env_path=env_path or DEFAULT_VDS_ENV_PATH,
        overrides=overrides,
        strict=strict,
    )

    # Create and return the async client
    return AsyncBitbucketClient(settings, timeout=timeout)


__all__ = [
    "DEFAULT_VDS_ENV_PATH",
    "create_async_client",
    "create_client",
]
