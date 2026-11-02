"""Unit tests for Bitbucket protocol interfaces.

Tests verify that:
1. Protocol classes are properly defined and importable
2. BitbucketClient implements all protocols (structural subtyping)
3. isinstance() checks work correctly with @runtime_checkable protocols
4. Mock implementations can satisfy protocols for testing

References:
    - FR-21.2.1: Protocol classes for dependency injection and testability
    - TSK-222: Protocol interfaces for Bitbucket
"""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest
from vds_bitbucket_orchestrator import (
    BitbucketBranchClient,
    BitbucketClient,
    BitbucketCodeClient,
    BitbucketFullClient,
    BitbucketRepositoryClient,
    BitbucketSettings,
)
from vds_bitbucket_orchestrator.protocols import (
    BitbucketBranchClient as ProtocolBranchClient,
)
from vds_bitbucket_orchestrator.protocols import (
    BitbucketCodeClient as ProtocolCodeClient,
)
from vds_bitbucket_orchestrator.protocols import (
    BitbucketFullClient as ProtocolFullClient,
)
from vds_bitbucket_orchestrator.protocols import (
    BitbucketRepositoryClient as ProtocolRepositoryClient,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_settings() -> BitbucketSettings:
    """Create server-mode settings for testing."""
    return BitbucketSettings(
        VDS_USERNAME="test_user",
        VDS_PASSWORD="test_pass",
        BITBUCKET_TOKEN="test_token",
        BITBUCKET_BASE_URL="https://bitbucket.test.com",
        BITBUCKET_MODE="server",
    )


@pytest.fixture
@patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
def bitbucket_client(mock_atlassian: Mock, mock_settings: BitbucketSettings) -> BitbucketClient:
    """Create a BitbucketClient instance with mocked SDK."""
    return BitbucketClient(mock_settings)


# ============================================================================
# Protocol Import Tests
# ============================================================================


class TestProtocolImports:
    """Test that protocols are properly importable from package root."""

    def test_import_repository_client_from_package(self) -> None:
        """BitbucketRepositoryClient should be importable from package root."""
        assert BitbucketRepositoryClient is not None
        assert BitbucketRepositoryClient is ProtocolRepositoryClient

    def test_import_branch_client_from_package(self) -> None:
        """BitbucketBranchClient should be importable from package root."""
        assert BitbucketBranchClient is not None
        assert BitbucketBranchClient is ProtocolBranchClient

    def test_import_code_client_from_package(self) -> None:
        """BitbucketCodeClient should be importable from package root."""
        assert BitbucketCodeClient is not None
        assert BitbucketCodeClient is ProtocolCodeClient

    def test_import_full_client_from_package(self) -> None:
        """BitbucketFullClient should be importable from package root."""
        assert BitbucketFullClient is not None
        assert BitbucketFullClient is ProtocolFullClient


# ============================================================================
# Protocol Compliance Tests (isinstance checks)
# ============================================================================


class TestBitbucketClientProtocolCompliance:
    """Test that BitbucketClient implements all protocols."""

    def test_implements_repository_client_protocol(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should implement BitbucketRepositoryClient protocol."""
        assert isinstance(bitbucket_client, BitbucketRepositoryClient)

    def test_implements_branch_client_protocol(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should implement BitbucketBranchClient protocol."""
        assert isinstance(bitbucket_client, BitbucketBranchClient)

    def test_implements_code_client_protocol(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should implement BitbucketCodeClient protocol."""
        assert isinstance(bitbucket_client, BitbucketCodeClient)

    def test_implements_full_client_protocol(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should implement BitbucketFullClient protocol."""
        assert isinstance(bitbucket_client, BitbucketFullClient)


# ============================================================================
# Protocol Method Signature Tests
# ============================================================================


class TestRepositoryClientMethods:
    """Test that BitbucketClient has correct method signatures for BitbucketRepositoryClient."""

    def test_has_list_projects_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have list_projects method."""
        assert hasattr(bitbucket_client, "list_projects")
        assert callable(bitbucket_client.list_projects)

    def test_has_get_project_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have get_project method."""
        assert hasattr(bitbucket_client, "get_project")
        assert callable(bitbucket_client.get_project)

    def test_has_list_repositories_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have list_repositories method."""
        assert hasattr(bitbucket_client, "list_repositories")
        assert callable(bitbucket_client.list_repositories)

    def test_has_get_repository_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have get_repository method."""
        assert hasattr(bitbucket_client, "get_repository")
        assert callable(bitbucket_client.get_repository)


class TestBranchClientMethods:
    """Test that BitbucketClient has correct method signatures for BitbucketBranchClient."""

    def test_has_get_branches_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have get_branches method."""
        assert hasattr(bitbucket_client, "get_branches")
        assert callable(bitbucket_client.get_branches)

    def test_has_list_branch_permissions_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have list_branch_permissions method."""
        assert hasattr(bitbucket_client, "list_branch_permissions")
        assert callable(bitbucket_client.list_branch_permissions)


class TestCodeClientMethods:
    """Test that BitbucketClient has correct method signatures for BitbucketCodeClient."""

    def test_has_get_content_of_file_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have get_content_of_file method (not get_file_content)."""
        assert hasattr(bitbucket_client, "get_content_of_file")
        assert callable(bitbucket_client.get_content_of_file)
        # Verify the correct method name is used (not the incorrect one)
        # This validates the code validation note from tasks.md

    def test_has_get_commits_method(self, bitbucket_client: BitbucketClient) -> None:
        """BitbucketClient should have get_commits method (not list_commits)."""
        assert hasattr(bitbucket_client, "get_commits")
        assert callable(bitbucket_client.get_commits)
        # Verify the correct method name is used (not the incorrect one)
        # This validates the code validation note from tasks.md


# ============================================================================
# Mock Implementation Tests
# ============================================================================


class MockRepositoryClient:
    """Mock implementation of BitbucketRepositoryClient for testing."""

    def list_projects(self, limit: int = 25) -> list[dict[str, Any]]:
        return [{"key": "TEST", "name": "Test Project"}]

    def get_project(self, project_key: str) -> dict[str, Any]:
        return {"key": project_key, "name": f"Project {project_key}"}

    def list_repositories(self, project_key: str, limit: int = 25) -> list[dict[str, Any]]:
        return [{"slug": "test-repo", "name": "Test Repository"}]

    def get_repository(self, project_key: str, repository_slug: str) -> dict[str, Any]:
        return {"slug": repository_slug, "name": f"Repository {repository_slug}"}


class MockBranchClient:
    """Mock implementation of BitbucketBranchClient for testing."""

    def get_branches(
        self,
        project_key: str,
        repository_slug: str,
        filter: str = "",
        limit: int = 99999,
        details: bool = True,
    ) -> list[dict[str, Any]]:
        return [{"displayId": "main", "isDefault": True}]

    def list_branch_permissions(
        self,
        project_key: str,
        repository_slug: str | None = None,
        start: int = 0,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        return [{"type": "no-deletes", "matcher": {"id": "main"}}]


class MockCodeClient:
    """Mock implementation of BitbucketCodeClient for testing."""

    def get_content_of_file(
        self,
        project_key: str,
        repository_slug: str,
        filename: str,
        at: str | None = None,
        markup: str | None = None,
    ) -> str:
        return f"# Content of {filename}"

    def get_commits(
        self,
        project_key: str,
        repository_slug: str,
        hash_oldest: str | None = None,
        hash_newest: str | None = None,
        limit: int = 99999,
    ) -> list[dict[str, Any]]:
        return [{"id": "abc123", "message": "Initial commit"}]


class MockFullClient(MockRepositoryClient, MockBranchClient, MockCodeClient):
    """Mock implementation of BitbucketFullClient for testing."""

    pass


class TestMockImplementations:
    """Test that mock implementations satisfy protocols."""

    def test_mock_repository_client_satisfies_protocol(self) -> None:
        """MockRepositoryClient should satisfy BitbucketRepositoryClient protocol."""
        mock = MockRepositoryClient()
        assert isinstance(mock, BitbucketRepositoryClient)

    def test_mock_branch_client_satisfies_protocol(self) -> None:
        """MockBranchClient should satisfy BitbucketBranchClient protocol."""
        mock = MockBranchClient()
        assert isinstance(mock, BitbucketBranchClient)

    def test_mock_code_client_satisfies_protocol(self) -> None:
        """MockCodeClient should satisfy BitbucketCodeClient protocol."""
        mock = MockCodeClient()
        assert isinstance(mock, BitbucketCodeClient)

    def test_mock_full_client_satisfies_protocol(self) -> None:
        """MockFullClient should satisfy BitbucketFullClient protocol."""
        mock = MockFullClient()
        assert isinstance(mock, BitbucketFullClient)


# ============================================================================
# Dependency Injection Tests
# ============================================================================


def audit_repository_with_protocol(client: BitbucketRepositoryClient, project_key: str) -> dict[str, Any]:
    """Example function using BitbucketRepositoryClient protocol for DI."""
    repos = client.list_repositories(project_key)
    return {"project": project_key, "repository_count": len(repos)}


def get_branch_permissions_with_protocol(
    client: BitbucketBranchClient, project_key: str, repo_slug: str
) -> list[dict[str, Any]]:
    """Example function using BitbucketBranchClient protocol for DI."""
    return client.list_branch_permissions(project_key, repo_slug)


def get_file_content_with_protocol(client: BitbucketCodeClient, project_key: str, repo_slug: str, filename: str) -> str:
    """Example function using BitbucketCodeClient protocol for DI."""
    return client.get_content_of_file(project_key, repo_slug, filename)


class TestDependencyInjection:
    """Test that protocols enable proper dependency injection."""

    def test_repository_client_di_with_mock(self) -> None:
        """Functions accepting BitbucketRepositoryClient should work with mock."""
        mock = MockRepositoryClient()
        result = audit_repository_with_protocol(mock, "TEST")
        assert result["project"] == "TEST"
        assert result["repository_count"] == 1

    def test_branch_client_di_with_mock(self) -> None:
        """Functions accepting BitbucketBranchClient should work with mock."""
        mock = MockBranchClient()
        result = get_branch_permissions_with_protocol(mock, "TEST", "test-repo")
        assert len(result) == 1
        assert result[0]["type"] == "no-deletes"

    def test_code_client_di_with_mock(self) -> None:
        """Functions accepting BitbucketCodeClient should work with mock."""
        mock = MockCodeClient()
        result = get_file_content_with_protocol(mock, "TEST", "test-repo", "README.md")
        assert "README.md" in result

    @patch("vds_bitbucket_orchestrator.client.AtlassianBitbucket")
    def test_repository_client_di_with_real_client(
        self, mock_atlassian: Mock, mock_settings: BitbucketSettings
    ) -> None:
        """Functions accepting BitbucketRepositoryClient should work with real client."""
        client = BitbucketClient(mock_settings)
        mock_atlassian_instance = Mock()
        mock_atlassian_instance.repo_list.return_value = [{"slug": "repo1"}, {"slug": "repo2"}]
        client._client = mock_atlassian_instance

        result = audit_repository_with_protocol(client, "TEST")
        assert result["project"] == "TEST"
        assert result["repository_count"] == 2
