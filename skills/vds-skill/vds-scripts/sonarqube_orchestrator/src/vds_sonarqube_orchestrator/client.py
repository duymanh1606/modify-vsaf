"""SonarQube client wrapper using python-sonarqube-api.

This module provides a client for SonarQube server operations including
project management, issue retrieval, quality gate checks, and metrics.

Architecture:
    Client -> python-sonarqube-api -> SonarQube Server

The client uses:
- python-sonarqube-api for SonarQube API communication
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from sonarqube import SonarQubeClient as Sonar

from vds_sonarqube_orchestrator.errors import (
    AuthError,
    ClientPermissionError,
    ClientTimeoutError,
    NotFoundError,
    RetryError,
    TransportError,
    VDSClientError,
)

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings

# Suppress InsecureRequestWarning for self-signed certs
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


class SonarqubeClient:
    """High-level SonarQube client using python-sonarqube-api.

    This client provides access to SonarQube API endpoints including
    health checks, project management, issues, quality gates, and metrics.

    Example:
        >>> from vds_sonarqube_orchestrator import SonarqubeClient, load_settings
        >>> settings = load_settings()
        >>> with SonarqubeClient(settings) as client:
        ...     health = client.ping()
        ...     print(health)
    """

    def __init__(self, config: SonarqubeSettings) -> None:
        """Initialize the client with configuration.

        Args:
            config: SonarqubeSettings instance with connection parameters.
        """
        self.config = config
        self._sonar: Sonar | None = None

    def _get_sonar_client(self) -> Sonar:
        """Get or create the SonarQube client (lazy initialization)."""
        if self._sonar is None:
            # Prepare authentication
            token = self.config.token
            username = self.config.user
            password = self.config.password

            # Determine auth method
            if token:
                auth_args = {"token": token}
            elif username and password:
                auth_args = {"username": username, "password": password}
            else:
                # No auth - public access only
                auth_args = {}

            self._sonar = Sonar(
                sonarqube_url=self.config.base_url,
                verify=self.config.verify_certs,
                timeout=int(self.config.request_timeout),
                **auth_args,
            )

        return self._sonar

    @property
    def sonar(self) -> Sonar:
        """Access the underlying python-sonarqube-api client."""
        return self._get_sonar_client()

    def _handle_sonar_error(self, exc: Exception, operation: str) -> None:
        """Convert python-sonarqube-api exceptions to our error hierarchy.

        Args:
            exc: The caught exception.
            operation: Description of the operation for error messages.

        Raises:
            AuthError: For authentication failures.
            ClientPermissionError: For permission issues.
            NotFoundError: For missing resources.
            TransportError: For network issues.
            ClientTimeoutError: For timeouts.
            VDSClientError: For other errors.
        """
        # Get error message
        error_msg = str(exc)

        # Check for common patterns in error messages
        # 401 Unauthorized
        if "401" in error_msg or "Unauthorized" in error_msg or "Authentication" in error_msg:
            raise AuthError(
                f"Authentication failed for {operation}",
                context={"error": error_msg},
            ) from exc

        # 403 Forbidden
        if "403" in error_msg or "Forbidden" in error_msg or "Permission" in error_msg:
            raise ClientPermissionError(
                f"Permission denied for {operation}",
                context={"error": error_msg},
            ) from exc

        # 404 Not Found
        if "404" in error_msg or "not found" in error_msg.lower():
            raise NotFoundError(
                f"Resource not found for {operation}",
                context={"error": error_msg},
            ) from exc

        # Connection/timeout errors
        if isinstance(exc, TimeoutError) or "timeout" in error_msg.lower():
            raise ClientTimeoutError(
                f"Request timed out for {operation}",
                context={"error": error_msg},
            ) from exc

        if "Connection" in error_msg or "Network" in error_msg:
            raise TransportError(
                f"Connection failed for {operation}",
                context={"error": error_msg},
            ) from exc

        # Default to generic client error
        raise VDSClientError(
            f"Error during {operation}: {error_msg}",
            context={"error": error_msg},
        ) from exc

    # -------------------------------------------------------------------------
    # Server Health and Info
    # -------------------------------------------------------------------------

    def ping(self) -> dict[str, Any]:
        """Test connectivity to SonarQube server.

        Returns:
            Server status dict with id, version, status fields.

        Raises:
            AuthError: For authentication failures.
            TransportError: For network issues.
        """
        try:
            result = self.sonar.server.get_server_version()
            return (
                {"status": "up", "version": result}
                if isinstance(result, str)
                else {"status": "unknown", "result": result}
            )
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={**{"operation": "ping"}, "attempts": self.config.max_retries},
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, "ping")

    # -------------------------------------------------------------------------
    # Project Operations
    # -------------------------------------------------------------------------

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get project details by key.

        Args:
            project_key: SonarQube project key.

        Returns:
            Project configuration dict.

        Raises:
            NotFoundError: If project not found.
            AuthError: For authentication failures.
        """
        try:
            result = self.sonar.projects.get_project(key=project_key)
            return result if isinstance(result, dict) else {"key": project_key, "result": result}
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_project", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_project({project_key})")

    def search_projects(
        self,
        query: str | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Search for projects.

        Args:
            query: Optional search query.
            page: Page number (pagination).
            per_page: Results per page.

        Returns:
            List of project dicts.
        """
        try:
            search_results = self.sonar.projects.search_projects(
                q=query,
                p=page,
                ps=per_page,
            )
            # Extract components from response
            if isinstance(search_results, dict):
                components = search_results.get("components", [])
            elif isinstance(search_results, list):
                components = search_results
            else:
                components = []
            return components if isinstance(components, list) else []
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "search_projects", "query": query},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, "search_projects")

    # -------------------------------------------------------------------------
    # Issue Operations
    # -------------------------------------------------------------------------

    def get_issues(
        self,
        project_key: str,
        severities: list[str] | None = None,
        types: list[str] | None = None,
        statuses: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get issues for a project.

        Args:
            project_key: SonarQube project key.
            severities: Optional list of severities (BLOCKER, CRITICAL, MAJOR, MINOR, INFO).
            types: Optional list of types (BUG, VULNERABILITY, CODE_SMELL).
            statuses: Optional list of statuses (OPEN, CONFIRMED, REOPENED, RESOLVED, CLOSED).
            page: Page number (pagination).
            per_page: Results per page.

        Returns:
            List of issue dicts.
        """
        try:
            # Build issue search parameters
            params = {
                "componentKeys": project_key,
                "p": page,
                "ps": per_page,
            }
            if severities:
                params["severities"] = ",".join(severities)
            if types:
                params["types"] = ",".join(types)
            if statuses:
                params["statuses"] = ",".join(statuses)

            result = self.sonar.issues.search_issues(**params)
            if isinstance(result, dict):
                issues = result.get("issues", [])
            elif isinstance(result, list):
                issues = result
            else:
                issues = []
            return issues if isinstance(issues, list) else []
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_issues", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_issues({project_key})")

    # -------------------------------------------------------------------------
    # Metrics and Measures
    # -------------------------------------------------------------------------

    def get_measures(
        self,
        project_key: str,
        metrics: str | list[str],
        branch: str | None = None,
    ) -> dict[str, Any]:
        """Get measures/metrics for a project.

        Args:
            project_key: SonarQube project key.
            metrics: Metric key(s) - can be string or list.
            branch: Optional branch name.

        Returns:
            Dict mapping metric keys to values.

        Common metrics:
            - bugs, vulnerabilities, code_smells
            - coverage, lines_to_cover
            - duplicated_lines_density, ncloc
            - sqale_index, sqale_rating
            - reliability_rating, security_rating
        """
        try:
            metric_str = ",".join(metrics) if isinstance(metrics, list) else metrics

            # Use correct API method signature
            result = self.sonar.measures.get_component_with_specified_measures(
                component=project_key,
                metricKeys=metric_str,
                branch=branch,
            )

            # Extract measures from response
            measures: dict[str, Any] = {}
            if isinstance(result, dict):
                component = result.get("component", {})
                for measure in component.get("measures", []):
                    metric = measure.get("metric", "")
                    value = measure.get("value")
                    if value is not None:
                        measures[metric] = value

            return measures
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_measures", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_measures({project_key})")

    # -------------------------------------------------------------------------
    # Quality Gate Operations
    # -------------------------------------------------------------------------

    def get_quality_gate_status(
        self,
        project_key: str,
        branch: str | None = None,
    ) -> dict[str, Any]:
        """Get quality gate status for a project.

        Args:
            project_key: SonarQube project key.
            branch: Optional branch name.

        Returns:
            Quality gate status dict with status (OK/ERROR/WARN) and conditions.
        """
        try:
            params = {"projectKey": project_key}
            if branch:
                params["branch"] = branch

            # Use direct API call since python-sonarqube-api doesn't have a wrapper
            url = f"{self.sonar.base_url}/api/qualitygates/project_status"
            response = self.sonar.session.request("GET", url, params=params)
            response.raise_for_status()
            result = response.json()

            # Extract status from response
            if isinstance(result, dict):
                return result
            return {"status": "UNKNOWN", "result": result}
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_quality_gate_status", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_quality_gate_status({project_key})")

    # -------------------------------------------------------------------------
    # Task/Scan Operations
    # -------------------------------------------------------------------------

    def get_task_info(self, task_id: str) -> dict[str, Any]:
        """Get scan task status and info.

        Args:
            task_id: SonarQube task ID (e.g., "AU-TpxcA-i5").

        Returns:
            Task info dict with status, statusText, component, etc.
        """
        try:
            # Use direct API call since python-sonarqube-api doesn't have a get_task method
            url = f"{self.sonar.base_url}/api/ce/task"
            response = self.sonar.session.request("GET", url, params={"id": task_id})
            response.raise_for_status()
            result = response.json()
            return result if isinstance(result, dict) else {"task": task_id, "result": result}
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_task_info", "task_id": task_id},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_task_info({task_id})")

    # -------------------------------------------------------------------------
    # Security Hotspots Operations
    # -------------------------------------------------------------------------

    def get_hotspots(
        self,
        project_key: str,
        statuses: list[str] | None = None,
        page: int = 1,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get security hotspots for a project.

        Args:
            project_key: SonarQube project key.
            statuses: Optional list of statuses (TO_REVIEW, REVIEWED).
            page: Page number (pagination).
            per_page: Results per page.

        Returns:
            List of hotspot dicts.
        """
        try:
            params = {
                "projectKey": project_key,
                "p": page,
                "ps": per_page,
            }
            if statuses:
                params["statuses"] = ",".join(statuses)

            # Use direct API call since python-sonarqube-api doesn't have hotspots wrapper
            url = f"{self.sonar.base_url}/api/hotspots/search"
            response = self.sonar.session.request("GET", url, params=params)
            response.raise_for_status()
            result = response.json()

            if isinstance(result, dict):
                hotspots = result.get("hotspots", [])
            elif isinstance(result, list):
                hotspots = result
            else:
                hotspots = []
            return hotspots if isinstance(hotspots, list) else []
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_hotspots", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_hotspots({project_key})")

    # -------------------------------------------------------------------------
    # CE Activity Operations
    # -------------------------------------------------------------------------

    def get_ce_activity(
        self,
        project_key: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get Compute Engine activity (analysis tasks)."""
        try:
            params: dict[str, Any] = {"ps": limit}
            if project_key:
                params["component"] = project_key

            url = f"{self.sonar.base_url}/api/ce/activity"
            response = self.sonar.session.request("GET", url, params=params)
            response.raise_for_status()
            result = response.json()

            tasks = result.get("tasks", []) if isinstance(result, dict) else []
            return tasks if isinstance(tasks, list) else []
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_ce_activity", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, "get_ce_activity")
            return []

    def get_measures_history(
        self,
        project_key: str,
        metrics: list[str],
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get historical measures for trend analysis."""
        try:
            from datetime import datetime, timedelta

            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            metric_str = ",".join(metrics)

            url = f"{self.sonar.base_url}/api/measures/search_history"
            params = {
                "component": project_key,
                "metrics": metric_str,
                "from": from_date,
            }
            response = self.sonar.session.request("GET", url, params=params)
            response.raise_for_status()
            result = response.json()

            measures = result.get("measures", []) if isinstance(result, dict) else []
            return measures if isinstance(measures, list) else []
        except RetryError as exc:
            raise RetryError(
                f"Retry attempts exhausted after {self.config.max_retries} attempts",
                context={
                    **{"operation": "get_measures_history", "project_key": project_key},
                    "attempts": self.config.max_retries,
                },
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            self._handle_sonar_error(exc, f"get_measures_history({project_key})")
            return []

    # -------------------------------------------------------------------------
    # Context Manager and Cleanup
    # -------------------------------------------------------------------------

    def close(self) -> None:
        """Close the SonarQube client and release connections."""
        if self._sonar is not None:
            self._sonar = None

    def __enter__(self) -> SonarqubeClient:
        """Enter context manager."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close client."""
        self.close()


__all__ = ["SonarqubeClient"]
