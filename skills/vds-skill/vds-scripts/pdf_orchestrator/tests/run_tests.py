#!/usr/bin/env python3
"""
Comprehensive test runner for VDS PDF Orchestrator.

Provides automated testing for unit, integration, and container environments
with detailed reporting and coverage analysis.
"""

import argparse
import contextlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class TestResult:
    """Test execution result."""

    suite: str
    passed: int
    failed: int
    skipped: int
    total: int
    duration: float
    output_file: str | None = None
    coverage_file: str | None = None


class TestRunner:
    """Comprehensive test runner for VDS PDF Orchestrator."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.reports_dir = project_root / "test_reports"
        self.results: list[TestResult] = []

        # Ensure directories exist
        self.reports_dir.mkdir(exist_ok=True)

    def run_unit_tests(
        self, coverage: bool = True, verbose: bool = False
    ) -> TestResult:
        """Run unit tests."""
        print("🧪 Running Unit Tests...")
        print("=" * 50)

        cmd = ["python", "-m", "pytest", "tests/unit"]

        if coverage:
            cmd.extend(
                [
                    "--cov=vds_pdf_orchestrator",
                    "--cov-report=html",
                    "--cov-report=xml",
                    "--cov-report=term-missing",
                ]
            )

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/unit-results.xml",
                "--html=test-reports/unit-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="unit",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/unit-results.xml",
                coverage_file="htmlcov/index.html" if coverage else None,
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ Unit tests timed out")
            return TestResult("unit", 0, 1, 0, 300)
        except Exception as e:
            print(f"❌ Unit test execution failed: {e}")
            return TestResult("unit", 0, 1, 0, 0)

    def run_integration_tests(self, verbose: bool = False) -> TestResult:
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        print("=" * 50)

        cmd = ["python", "-m", "pytest", "tests/integration"]

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/integration-results.xml",
                "--html=test-reports/integration-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="integration",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/integration-results.xml",
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ Integration tests timed out")
            return TestResult("integration", 0, 1, 0, 600)
        except Exception as e:
            print(f"❌ Integration test execution failed: {e}")
            return TestResult("integration", 0, 1, 0, 0)

    def run_container_tests(self, verbose: bool = False) -> TestResult:
        """Run container tests (requires Docker)."""
        print("\n🐳 Running Container Tests...")
        print("=" * 50)

        # Check Docker availability
        try:
            subprocess.run(["docker", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  Docker not available, skipping container tests")
            return TestResult("container", 0, 0, 1, 0)

        cmd = ["python", "-m", "pytest", "tests/container"]

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/container-results.xml",
                "--html=test-reports/container-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="container",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/container-results.xml",
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ Container tests timed out")
            return TestResult("container", 0, 1, 0, 1800)
        except Exception as e:
            print(f"❌ Container test execution failed: {e}")
            return TestResult("container", 0, 1, 0, 0)

    def run_end_to_end_tests(self, verbose: bool = False) -> TestResult:
        """Run end-to-end tests."""
        print("\n🔄 Running End-to-End Tests...")
        print("=" * 50)

        cmd = ["python", "-m", "pytest", "tests/e2e"]

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/e2e-results.xml",
                "--html=test-reports/e2e-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=900,  # 15 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="e2e",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/e2e-results.xml",
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ End-to-end tests timed out")
            return TestResult("e2e", 0, 1, 0, 900)
        except Exception as e:
            print(f"❌ End-to-end test execution failed: {e}")
            return TestResult("e2e", 0, 1, 0, 0)

    def run_security_tests(self, verbose: bool = False) -> TestResult:
        """Run security-focused tests."""
        print("\n🔒 Running Security Tests...")
        print("=" * 50)

        cmd = ["python", "-m", "pytest", "-m", "security"]

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/security-results.xml",
                "--html=test-reports/security-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="security",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/security-results.xml",
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ Security tests timed out")
            return TestResult("security", 0, 1, 0, 300)
        except Exception as e:
            print(f"❌ Security test execution failed: {e}")
            return TestResult("security", 0, 1, 0, 0)

    def run_performance_tests(self, verbose: bool = False) -> TestResult:
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")
        print("=" * 50)

        cmd = ["python", "-m", "pytest", "-m", "performance"]

        if verbose:
            cmd.append("-v")

        cmd.extend(
            [
                "--junitxml=test-reports/performance-results.xml",
                "--html=test-reports/performance-report.html",
                "--self-contained-html",
            ]
        )

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            duration = time.time() - start_time

            # Parse results
            passed, failed, skipped = self._parse_pytest_output(result.stdout)

            test_result = TestResult(
                suite="performance",
                passed=passed,
                failed=failed,
                skipped=skipped,
                total=passed + failed + skipped,
                duration=duration,
                output_file="test-reports/performance-results.xml",
            )

            self.results.append(test_result)
            self._print_test_result(test_result)

            return test_result

        except subprocess.TimeoutExpired:
            print("❌ Performance tests timed out")
            return TestResult("performance", 0, 1, 0, 600)
        except Exception as e:
            print(f"❌ Performance test execution failed: {e}")
            return TestResult("performance", 0, 1, 0, 0)

    def run_all_tests(
        self, coverage: bool = True, verbose: bool = False
    ) -> dict[str, Any]:
        """Run all test suites."""
        print("🚀 Running All Test Suites")
        print("=" * 60)

        start_time = time.time()

        # Run all test suites
        test_results = {
            "unit": self.run_unit_tests(coverage=coverage, verbose=verbose),
            "integration": self.run_integration_tests(verbose=verbose),
            "container": self.run_container_tests(verbose=verbose),
            "e2e": self.run_end_to_end_tests(verbose=verbose),
            "security": self.run_security_tests(verbose=verbose),
            "performance": self.run_performance_tests(verbose=verbose),
        }

        total_duration = time.time() - start_time

        # Generate summary report
        self._generate_summary_report(test_results, total_duration)

        return test_results

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output to get test counts."""
        passed = failed = skipped = 0

        # Look for summary line in pytest output
        # Example: "5 passed, 2 failed, 1 skipped in 10.23s"
        # Example: "287 passed in 2.80s"
        for line in output.split("\n"):
            if line.strip().startswith("==") and line.strip().endswith("=="):
                content = line.strip(" =")
                parts = content.split(",")

                for part in parts:
                    part = part.strip()
                    if "passed" in part:
                        with contextlib.suppress(ValueError, IndexError):
                            passed = int(part.split()[0])
                    elif "failed" in part:
                        with contextlib.suppress(ValueError, IndexError):
                            failed = int(part.split()[0])
                    elif "skipped" in part:
                        with contextlib.suppress(ValueError, IndexError):
                            skipped = int(part.split()[0])

                # If we found any stats, we're done
                if passed > 0 or failed > 0 or skipped > 0:
                    break

        return passed, failed, skipped

    def _print_test_result(self, result: TestResult):
        """Print test result summary."""
        status = "✅ PASSED" if result.failed == 0 else "❌ FAILED"

        print(f"Status: {status}")
        print(
            f"Tests:  {result.total} total, {result.passed} passed, {result.failed} failed, {result.skipped} skipped"
        )
        print(f"Time:   {result.duration:.2f}s")

        if result.coverage_file:
            print(f"Coverage: {result.coverage_file}")

        print("-" * 50)

    def _generate_summary_report(
        self, test_results: dict[str, TestResult], total_duration: float
    ):
        """Generate comprehensive summary report."""
        print("\n" + "=" * 60)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 60)

        # Calculate totals
        total_tests = sum(r.total for r in test_results.values())
        total_passed = sum(r.passed for r in test_results.values())
        total_failed = sum(r.failed for r in test_results.values())
        total_skipped = sum(r.skipped for r in test_results.values())

        # Overall status
        overall_status = (
            "✅ ALL TESTS PASSED" if total_failed == 0 else "❌ SOME TESTS FAILED"
        )
        print(f"Overall Status: {overall_status}")
        print(f"Total Duration: {total_duration:.2f}s")
        print()

        # Suite breakdown
        print("Suite Breakdown:")
        for suite_name, result in test_results.items():
            status = "✅" if result.failed == 0 else "❌"
            print(
                f"  {status} {suite_name.title():15}: {result.total:3d} total, "
                f"{result.passed:3d} passed, {result.failed:3d} failed, {result.skipped:3d} skipped "
                f"({result.duration:6.2f}s)"
            )

        print()
        print(
            f"Grand Totals: {total_tests:4d} total, {total_passed:4d} passed, "
            f"{total_failed:4d} failed, {total_skipped:4d} skipped"
        )

        # Generate JSON report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "duration": total_duration,
            "overall_status": "passed" if total_failed == 0 else "failed",
            "totals": {
                "tests": total_tests,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
            },
            "suites": {},
        }

        for suite_name, result in test_results.items():
            report_data["suites"][suite_name] = {
                "total": result.total,
                "passed": result.passed,
                "failed": result.failed,
                "skipped": result.skipped,
                "duration": result.duration,
                "output_file": result.output_file,
                "coverage_file": result.coverage_file,
            }

        # Save JSON report
        report_file = self.reports_dir / "test_summary.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 Detailed reports saved to: {self.reports_dir}")
        print(f"📊 Summary report: {report_file}")

        # Return exit code
        if total_failed > 0:
            sys.exit(1)


def check_dependencies() -> bool:
    """Check if required dependencies are available."""
    import importlib.util

    if importlib.util.find_spec("pytest") is None:
        print(
            "❌ pytest is not installed. Install with: pip install pytest pytest-cov pytest-html"
        )
        return False
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="VDS PDF Orchestrator Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s --unit --coverage    # Run unit tests with coverage
  %(prog)s --integration           # Run integration tests only
  %(prog)s --container             # Run container tests only
  %(prog)s --security              # Run security tests only
  %(prog)s --performance           # Run performance tests only
  %(prog)s --verbose               # Verbose output
        """,
    )

    # Test suite selection
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--unit", action="store_true", help="Run unit tests only")
    test_group.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    test_group.add_argument(
        "--container", action="store_true", help="Run container tests only"
    )
    test_group.add_argument(
        "--e2e", action="store_true", help="Run end-to-end tests only"
    )
    test_group.add_argument(
        "--security", action="store_true", help="Run security tests only"
    )
    test_group.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )

    # Options
    parser.add_argument(
        "--coverage",
        action="store_true",
        default=True,
        help="Enable test coverage reporting (default: True)",
    )
    parser.add_argument(
        "--no-coverage", action="store_true", help="Disable test coverage reporting"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    # Set project root
    project_root = args.project_root or Path(__file__).parent.parent

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Handle coverage flag
    coverage = args.coverage and not args.no_coverage

    # Create test runner
    runner = TestRunner(project_root)

    # Run tests based on selection
    try:
        if args.unit:
            runner.run_unit_tests(coverage=coverage, verbose=args.verbose)
        elif args.integration:
            runner.run_integration_tests(verbose=args.verbose)
        elif args.container:
            runner.run_container_tests(verbose=args.verbose)
        elif args.e2e:
            runner.run_end_to_end_tests(verbose=args.verbose)
        elif args.security:
            runner.run_security_tests(verbose=args.verbose)
        elif args.performance:
            runner.run_performance_tests(verbose=args.verbose)
        else:
            runner.run_all_tests(coverage=coverage, verbose=args.verbose)

    except KeyboardInterrupt:
        print("\n⚠️  Test execution interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
