"""Local SonarQube scanner orchestration.

This module provides orchestration for running local code quality scans
using Maven or sonar-scanner CLI tools.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from vds_sonarqube_orchestrator.errors import VDSClientError

if TYPE_CHECKING:
    from vds_sonarqube_orchestrator.config import SonarqubeSettings


class SonarqubeScanner:
    """Orchestrator for local SonarQube scans.

    Supports Maven-based scans and sonar-scanner CLI execution.

    Example:
        >>> from vds_sonarqube_orchestrator import SonarqubeScanner, load_settings
        >>> settings = load_settings()
        >>> scanner = SonarqubeScanner(settings)
        >>> task_id = scanner.scan_maven("/path/to/project", "my-project")
        >>> print(f"Scan task: {task_id}")
    """

    # Default Maven plugin version
    DEFAULT_MAVEN_PLUGIN_VERSION = "3.10.0.2594"

    # Default scan timeout in seconds
    DEFAULT_SCAN_TIMEOUT = 600  # 10 minutes

    # Polling interval for task completion
    DEFAULT_POLL_INTERVAL = 5  # seconds

    def __init__(self, config: SonarqubeSettings) -> None:
        """Initialize the scanner with configuration.

        Args:
            config: SonarqubeSettings instance with connection parameters.
        """
        self.config = config

    # -------------------------------------------------------------------------
    # Maven Scan
    # -------------------------------------------------------------------------

    def scan_maven(
        self,
        project_dir: Path | str,
        project_key: str,
        branch: str | None = None,
        wait: bool = False,
        timeout: int = DEFAULT_SCAN_TIMEOUT,
        maven_opts: list[str] | None = None,
    ) -> str | None:
        """Run a Maven-based SonarQube scan.

        Args:
            project_dir: Path to the project directory (containing pom.xml).
            project_key: SonarQube project key.
            branch: Optional branch name.
            wait: If True, wait for scan completion and return task ID.
            timeout: Maximum time to wait for scan completion (seconds).
            maven_opts: Additional Maven options (e.g., "-DskipTests").

        Returns:
            Task ID if wait=True and task was found, None otherwise.

        Raises:
            VDSClientError: If scan execution fails.
        """
        project_dir = Path(project_dir)
        if not project_dir.exists():
            raise VDSClientError(
                f"Project directory does not exist: {project_dir}",
                context={"project_dir": str(project_dir)},
            )

        pom_xml = project_dir / "pom.xml"
        if not pom_xml.exists():
            raise VDSClientError(
                f"pom.xml not found in: {project_dir}",
                context={"project_dir": str(project_dir)},
            )

        # Build Maven command
        cmd = [
            "mvn",
        ]

        # Add user-specified options
        if maven_opts:
            cmd.extend(maven_opts)
        else:
            # Default: skip tests
            cmd.extend(["-DskipTests"])

        # Add SonarQube properties
        cmd.extend(
            [
                f"-Dsonar.host.url={self.config.base_url}",
                f"-Dsonar.projectKey={project_key}",
            ]
        )

        # Add authentication
        if self.config.token:
            cmd.append(f"-Dsonar.token={self.config.token}")
        elif self.config.user and self.config.password:
            cmd.extend(
                [
                    f"-Dsonar.login={self.config.user}",
                    f"-Dsonar.password={self.config.password}",
                ]
            )

        # Add branch if specified
        if branch:
            cmd.append(f"-Dsonar.branch.name={branch}")

        # Add SonarQube Maven plugin goal
        cmd.append(
            f"org.sonarsource.scanner.maven:sonar-maven-plugin:{self.DEFAULT_MAVEN_PLUGIN_VERSION}:sonar"
        )

        # Execute scan
        try:
            env = os.environ.copy()

            # Add proxy settings if needed (non-proxy hosts)
            non_proxy_hosts = getattr(self.config, "non_proxy_hosts", None)
            if non_proxy_hosts:
                env.setdefault("http.nonProxyHosts", non_proxy_hosts)
                env.setdefault("https.nonProxyHosts", non_proxy_hosts)

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            # Check for errors
            if result.returncode != 0:
                raise VDSClientError(
                    f"Maven scan failed with exit code {result.returncode}",
                    context={
                        "project_dir": str(project_dir),
                        "project_key": project_key,
                        "stderr": result.stderr[-1000:],  # Last 1000 chars
                        "stdout": result.stdout[-1000:],
                    },
                )

            # Parse output for task ID if waiting
            if wait:
                # Try to extract task ID from output
                # SonarQube usually prints something like "More about the report at: http://.../dashboard?id=<key>"
                # The task ID is typically not directly visible in Maven output
                # For task tracking, user should use get_task_info with a recent task ID
                return None

            return None

        except subprocess.TimeoutExpired as exc:
            raise VDSClientError(
                f"Scan timed out after {timeout} seconds",
                context={"project_dir": str(project_dir), "timeout": timeout},
            ) from exc
        except FileNotFoundError as exc:
            raise VDSClientError(
                "Maven not found. Please install Maven or ensure it's in PATH.",
                context={"command": "mvn"},
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            raise VDSClientError(
                f"Failed to run Maven scan: {exc}",
                context={"project_dir": str(project_dir)},
            ) from exc

    # -------------------------------------------------------------------------
    # Sonar-Scanner CLI
    # -------------------------------------------------------------------------

    def scan_scanner(
        self,
        project_dir: Path | str,
        project_key: str,
        branch: str | None = None,
        wait: bool = False,
        timeout: int = DEFAULT_SCAN_TIMEOUT,
        extra_args: list[str] | None = None,
    ) -> str | None:
        """Run a sonar-scanner CLI scan.

        Args:
            project_dir: Path to the project directory.
            project_key: SonarQube project key.
            branch: Optional branch name.
            wait: Reserved for future use (wait for scan completion).
            timeout: Maximum time to wait for scan completion (seconds).
            extra_args: Additional arguments for sonar-scanner.

        Returns:
            Task ID if wait=True and task was found, None otherwise.

        Raises:
            VDSClientError: If scan execution fails.
        """
        project_dir = Path(project_dir)
        if not project_dir.exists():
            raise VDSClientError(
                f"Project directory does not exist: {project_dir}",
                context={"project_dir": str(project_dir)},
            )

        # Build sonar-scanner command
        cmd = [
            "sonar-scanner",
            f"-Dsonar.projectKey={project_key}",
            f"-Dsonar.host.url={self.config.base_url}",
        ]

        # Add authentication
        if self.config.token:
            cmd.append(f"-Dsonar.token={self.config.token}")
        elif self.config.user and self.config.password:
            cmd.extend(
                [
                    f"-Dsonar.login={self.config.user}",
                    f"-Dsonar.password={self.config.password}",
                ]
            )

        # Add branch if specified
        if branch:
            cmd.append(f"-Dsonar.branch.name={branch}")

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        # Execute scan
        try:
            env = os.environ.copy()

            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            # Check for errors
            if result.returncode != 0:
                raise VDSClientError(
                    f"sonar-scanner failed with exit code {result.returncode}",
                    context={
                        "project_dir": str(project_dir),
                        "project_key": project_key,
                        "stderr": result.stderr[-1000:],
                        "stdout": result.stdout[-1000:],
                    },
                )

            return None

        except subprocess.TimeoutExpired as exc:
            raise VDSClientError(
                f"Scan timed out after {timeout} seconds",
                context={"project_dir": str(project_dir), "timeout": timeout},
            ) from exc
        except FileNotFoundError as exc:
            raise VDSClientError(
                "sonar-scanner not found. Please install sonar-scanner or ensure it's in PATH.",
                context={"command": "sonar-scanner"},
            ) from exc
        except VDSClientError:
            raise
        except Exception as exc:
            raise VDSClientError(
                f"Failed to run sonar-scanner: {exc}",
                context={"project_dir": str(project_dir)},
            ) from exc

    # -------------------------------------------------------------------------
    # Task Polling
    # -------------------------------------------------------------------------

    def wait_for_task(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ) -> dict[str, Any]:
        """Wait for a scan task to complete.

        Args:
            task_id: SonarQube task ID.
            timeout: Maximum time to wait (seconds).
            poll_interval: Time between status checks (seconds).

        Returns:
            Task info dict with final status.

        Raises:
            VDSClientError: If task doesn't complete in time.
        """
        import time

        from vds_sonarqube_orchestrator.client import SonarqubeClient

        start_time = time.time()

        with SonarqubeClient(self.config) as client:
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise VDSClientError(
                        f"Task {task_id} did not complete within {timeout} seconds",
                        context={"task_id": task_id, "elapsed": elapsed},
                    )

                try:
                    task_info = client.get_task_info(task_id)
                    status = task_info.get("status", "UNKNOWN")

                    if status in ("SUCCESS", "CANCELED", "FAILED"):
                        return task_info

                except Exception:
                    # Don't fail on transient errors, just log and retry
                    pass

                time.sleep(poll_interval)


__all__ = ["SonarqubeScanner"]
