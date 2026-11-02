"""Unit tests for AsyncBitbucketClient (TSK-225).

Tests for the async wrapper that uses asyncio.to_thread() to wrap
synchronous BitbucketClient methods.

References:
    - FR-21.2.3: AsyncBitbucketClient using asyncio.to_thread()
    - TSK-225: Async Bitbucket wrapper
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from vds_bitbucket_orchestrator.async_client import AsyncBitbucketClient


def write_env(tmp_path: Path, content: str) -> Path:
    """Write a temporary .env file for testing."""
    env_path = tmp_path / ".env"
    env_path.write_text(content)
    return env_path


def clear_runtime_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear runtime environment variables for testing."""
    for key in (
        "VDS_USERNAME",
        "VDS_PASSWORD",
        "BITBUCKET_TOKEN",
        "VDS_BITBUCKET_URL",
        "BITBUCKET_BASE_URL",
        "VDS_BITBUCKET_HTTP_BASE",
        "BITBUCKET_CLOUD_WORKSPACE",
        "BITBUCKET_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


class TestAsyncBitbucketClientInit:
    """Tests for AsyncBitbucketClient initialization."""

    def test_async_client_creates_sync_client(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that AsyncBitbucketClient creates an underlying sync client."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            # Verify sync client was created
            mock_client.assert_called_once()
            assert async_client.sync_client is mock_instance

    def test_async_client_passes_timeout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that timeout is passed to the underlying sync client."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            AsyncBitbucketClient(settings, timeout=60)

            call_args = mock_client.call_args
            assert call_args.kwargs.get("timeout") == 60


class TestAsyncRepositoryOperations:
    """Tests for async repository operations."""

    @pytest.mark.asyncio
    async def test_list_projects_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async list_projects method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.list_projects.return_value = [
                {"key": "INS", "name": "Insurance"},
                {"key": "LEP", "name": "Lending"},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.list_projects(limit=10)

            assert len(result) == 2
            assert result[0]["key"] == "INS"
            mock_instance.list_projects.assert_called_once_with(10)

    @pytest.mark.asyncio
    async def test_get_project_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async get_project method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_project.return_value = {"key": "INS", "name": "Insurance"}
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.get_project("INS")

            assert result["key"] == "INS"
            mock_instance.get_project.assert_called_once_with("INS")

    @pytest.mark.asyncio
    async def test_list_repositories_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async list_repositories method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.list_repositories.return_value = [
                {"slug": "insurance-core", "name": "Insurance Core"},
                {"slug": "insurance-api", "name": "Insurance API"},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.list_repositories("INS", limit=50)

            assert len(result) == 2
            assert result[0]["slug"] == "insurance-core"
            mock_instance.list_repositories.assert_called_once_with("INS", 50)

    @pytest.mark.asyncio
    async def test_get_repository_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async get_repository method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_repository.return_value = {
                "slug": "insurance-core",
                "name": "Insurance Core",
            }
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.get_repository("INS", "insurance-core")

            assert result["slug"] == "insurance-core"
            mock_instance.get_repository.assert_called_once_with("INS", "insurance-core")


class TestAsyncBranchOperations:
    """Tests for async branch operations."""

    @pytest.mark.asyncio
    async def test_get_branches_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async get_branches method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_branches.return_value = [
                {"displayId": "main", "isDefault": True},
                {"displayId": "develop", "isDefault": False},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.get_branches("INS", "insurance-core")

            assert len(result) == 2
            assert result[0]["displayId"] == "main"
            mock_instance.get_branches.assert_called_once_with("INS", "insurance-core", "", 99999, True)

    @pytest.mark.asyncio
    async def test_list_branch_permissions_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async list_branch_permissions method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.list_branch_permissions.return_value = [
                {"type": "no-deletes", "matcher": {"id": "refs/heads/main"}},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.list_branch_permissions("INS", "insurance-core")

            assert len(result) == 1
            mock_instance.list_branch_permissions.assert_called_once_with("INS", "insurance-core", 0, 25)


class TestAsyncCodeOperations:
    """Tests for async code operations (BitbucketCodeClient protocol)."""

    @pytest.mark.asyncio
    async def test_get_content_of_file_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async get_content_of_file method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_content_of_file.return_value = "# README\n\nThis is a test."
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.get_content_of_file("INS", "insurance-core", "README.md")

            assert "README" in result
            mock_instance.get_content_of_file.assert_called_once_with("INS", "insurance-core", "README.md", None, None)

    @pytest.mark.asyncio
    async def test_get_commits_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async get_commits method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get_commits.return_value = [
                {"id": "abc123", "message": "Initial commit"},
                {"id": "def456", "message": "Add feature"},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.get_commits("INS", "insurance-core", limit=10)

            assert len(result) == 2
            assert result[0]["id"] == "abc123"
            mock_instance.get_commits.assert_called_once_with("INS", "insurance-core", None, None, 10)


class TestAsyncConcurrentOperations:
    """Tests for concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_api_calls(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that multiple async calls can run concurrently."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.list_repositories.return_value = [{"slug": "repo1"}]
            mock_instance.get_branches.return_value = [{"displayId": "main"}]
            mock_instance.get_content_of_file.return_value = "# README"
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            # Run multiple operations concurrently
            repos, branches, readme = await asyncio.gather(
                async_client.list_repositories("INS"),
                async_client.get_branches("INS", "insurance-core"),
                async_client.get_content_of_file("INS", "insurance-core", "README.md"),
            )

            assert len(repos) == 1
            assert len(branches) == 1
            assert "README" in readme


class TestAsyncPullRequestOperations:
    """Tests for async pull request operations."""

    @pytest.mark.asyncio
    async def test_list_pull_requests_async(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test async list_pull_requests method."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.list_pull_requests.return_value = [
                {"id": 1, "title": "Feature PR", "state": "OPEN"},
            ]
            mock_client.return_value = mock_instance

            from vds_bitbucket_orchestrator.config import load_settings

            settings = load_settings(env_path=env_path)
            async_client = AsyncBitbucketClient(settings)

            result = await async_client.list_pull_requests("INS", "insurance-core")

            assert len(result) == 1
            assert result[0]["title"] == "Feature PR"


class TestCreateAsyncClientFactory:
    """Tests for create_async_client() factory function."""

    def test_create_async_client_returns_async_client(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that create_async_client returns AsyncBitbucketClient."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
VDS_BITBUCKET_URL=https://bitbucket.test.com
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.AsyncBitbucketClient") as mock_async:
            with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient"):
                mock_instance = MagicMock(spec=AsyncBitbucketClient)
                mock_async.return_value = mock_instance

                from vds_bitbucket_orchestrator import create_async_client

                client = create_async_client(env_path=env_path)

                assert client is mock_instance
                mock_async.assert_called_once()

    def test_create_async_client_with_mode_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that mode parameter is passed correctly."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
BITBUCKET_CLOUD_WORKSPACE=testworkspace
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.AsyncBitbucketClient") as mock_async:
            with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient"):
                mock_instance = MagicMock(spec=AsyncBitbucketClient)
                mock_async.return_value = mock_instance

                from vds_bitbucket_orchestrator import create_async_client

                create_async_client(env_path=env_path, mode="cloud")

                call_args = mock_async.call_args
                settings = call_args[0][0]
                assert settings.mode == "cloud"

    def test_create_async_client_with_custom_timeout(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test that timeout is passed to AsyncBitbucketClient."""
        clear_runtime_env(monkeypatch)
        env_path = write_env(
            tmp_path,
            """
VDS_USERNAME=test_user
VDS_PASSWORD=test_pass
""".strip(),
        )

        with patch("vds_bitbucket_orchestrator.factory.AsyncBitbucketClient") as mock_async:
            with patch("vds_bitbucket_orchestrator.async_client.BitbucketClient"):
                mock_instance = MagicMock(spec=AsyncBitbucketClient)
                mock_async.return_value = mock_instance

                from vds_bitbucket_orchestrator import create_async_client

                create_async_client(env_path=env_path, timeout=120)

                call_args = mock_async.call_args
                assert call_args.kwargs.get("timeout") == 120


class TestAsyncClientImports:
    """Test that async client is properly exported from package."""

    def test_async_client_importable_from_package(self) -> None:
        """Test that AsyncBitbucketClient can be imported from package root."""
        from vds_bitbucket_orchestrator import AsyncBitbucketClient

        assert AsyncBitbucketClient is not None

    def test_create_async_client_importable(self) -> None:
        """Test that create_async_client can be imported from package root."""
        from vds_bitbucket_orchestrator import create_async_client

        assert callable(create_async_client)
