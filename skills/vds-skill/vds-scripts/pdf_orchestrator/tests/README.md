# VDS PDF Orchestrator - Testing Guide

This comprehensive testing guide covers the test framework, test execution, and best practices for the VDS PDF Orchestrator project.

## Table of Contents

1. [Test Framework Overview](#test-framework-overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Writing Tests](#writing-tests)
6. [CI/CD Integration](#cicd-integration)
7. [Test Data Management](#test-data-management)
8. [Troubleshooting](#troubleshooting)

## Test Framework Overview

The VDS PDF Orchestrator uses **pytest** as its primary testing framework, complemented by several specialized plugins:

### Core Dependencies
- **pytest 8.0+**: Test framework and execution engine
- **pytest-cov**: Code coverage reporting
- **pytest-html**: HTML test reports
- **pytest-mock**: Mocking and patching utilities
- **pytest-xdist**: Parallel test execution

### Testing Features
- **Comprehensive Fixtures**: Shared test setup and teardown
- **Mock Services**: Isolated testing with mock dependencies
- **Container Testing**: Docker-based integration tests
- **Performance Testing**: Memory and timing benchmarks
- **Security Testing**: Vulnerability and security validation
- **Coverage Analysis**: Line and branch coverage tracking

## Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── pytest.ini               # Pytest configuration
├── requirements.txt           # Test dependencies
├── run_tests.py              # Custom test runner
├── README.md                 # This file
├── test_data/               # Test data files
├── test_reports/            # Generated test reports
├── unit/                    # Unit tests
│   ├── test_config.py
│   ├── test_logging.py
│   ├── test_memory_monitor.py
│   ├── test_error_handling.py
│   └── test_enhanced_security.py
├── integration/             # Integration tests
│   ├── test_integration.py
│   ├── test_redis_session.py
│   └── test_health_monitoring.py
├── container/               # Container tests
│   ├── test_container_deployment.py
│   ├── test_container_networking.py
│   └── test_container_performance.py
├── e2e/                     # End-to-end tests
│   ├── test_user_workflows.py
│   ├── test_api_endpoints.py
│   └── test_batch_processing.py
├── security/               # Security tests
│   ├── test_pdf_validation.py
│   ├── test_malicious_content.py
│   └── test_authorization.py
└── performance/            # Performance tests
    ├── test_memory_usage.py
    ├── test_processing_speed.py
    └── test_concurrent_load.py
```

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --container
python tests/run_tests.py --security
```

### Advanced Usage

```bash
# Run tests with coverage
python tests/run_tests.py --coverage

# Run with verbose output
python tests/run_tests.py --verbose

# Run tests in parallel
pytest -n auto

# Run tests by marker
pytest -m "unit or integration"
pytest -m "security"
pytest -m "slow"

# Run specific test file
pytest tests/unit/test_config.py

# Run with timeout
pytest --timeout=300

# Generate HTML report
pytest --html=test-reports/report.html
```

### Docker-based Testing

```bash
# Run tests in Docker container
docker run --rm -v $(pwd):/app vds-pdf-orchestrator:latest python tests/run_tests.py

# Run container tests specifically
python tests/run_tests.py --container
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components and functions in isolation
- **Scope**: Fast, focused tests without external dependencies
- **Examples**:
  - Configuration validation
  - Memory monitoring logic
  - Error handling mechanisms
  - Security pattern detection

### Integration Tests (`tests/integration/`)
- **Purpose**: Test interactions between multiple components
- **Scope**: Medium complexity tests with real dependencies
- **Examples**:
  - Redis session management
  - Health monitoring integration
  - Error recovery workflows
  - Security validation pipeline

### Container Tests (`tests/container/`)
- **Purpose**: Test the complete containerized application
- **Scope**: End-to-end container functionality
- **Examples**:
  - Docker image building
  - Service startup and health checks
  - Resource limits and security
  - Multi-service composition

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows
- **Scope**: Full application functionality
- **Examples**:
  - PDF processing workflows
  - API endpoint integration
  - Batch processing scenarios
  - User interaction flows

### Security Tests (`tests/security/`)
- **Purpose**: Validate security features and vulnerabilities
- **Scope**: Security-focused testing
- **Examples**:
  - PDF security validation
  - Malicious content detection
  - Authentication and authorization
  - Data privacy protection

### Performance Tests (`tests/performance/`)
- **Purpose**: Measure performance characteristics
- **Scope**: Resource usage and timing metrics
- **Examples**:
  - Memory usage analysis
  - Processing speed benchmarks
  - Concurrent load testing
  - Resource limit validation

## Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from vds_pdf_orchestrator.memory_monitor import MemoryMonitor

class TestMemoryMonitor:
    """Test memory monitoring functionality."""

    def test_memory_usage_detection(self):
        """Test memory usage detection."""
        monitor = MemoryMonitor()

        usage = monitor.get_memory_usage()

        assert isinstance(usage, dict)
        assert "memory_mb" in usage
        assert "platform" in usage

    def test_memory_recommendations(self):
        """Test memory optimization recommendations."""
        monitor = MemoryMonitor()

        recommendation = monitor.get_memory_recommendation()

        assert isinstance(recommendation, dict)
        assert "should_use_optimized" in recommendation
        assert "recommendations" in recommendation

    @pytest.mark.parametrize("memory_mb,expected", [
        (100, False),
        (1500, True),
        (2000, True)
    ])
    def test_memory_pressure_detection(self, memory_mb, expected):
        """Test memory pressure detection."""
        monitor = MemoryMonitor()

        with patch.object(monitor, 'get_memory_usage') as mock_usage:
            mock_usage.return_value = {"memory_mb": memory_mb, "platform": "unix"}

            recommendation = monitor.get_memory_recommendation()

            assert recommendation["should_use_optimized"] == expected
```

### Using Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def sample_markdown_file(tmp_path):
    """Create a sample markdown file for testing."""
    content = """# Test Document

This is a test markdown file.

## Features
- **Bold text**
- *Italic text*
"""

    md_file = tmp_path / "sample.md"
    md_file.write_text(content)
    return md_file

@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    client = Mock()
    client.ping.return_value = True
    client.get.return_value = None
    client.set.return_value = True
    return client
```

### Mocking External Dependencies

```python
import pytest
from unittest.mock import patch

def test_redis_integration(mock_redis):
    """Test Redis integration with mocked client."""
    from vds_pdf_orchestrator.redis_session import RedisSessionManager

    with patch('vds_pdf_orchestrator.redis_session.redis.Redis', return_value=mock_redis):
        manager = RedisSessionManager(host="localhost", port=6379)

        session_id = manager.create_session("/test/input.md")
        assert session_id is not None

        # Verify Redis calls were made
        mock_redis.set.assert_called()
```

### Security Testing

```python
import pytest
from vds_pdf_orchestrator.enhanced_security import get_enhanced_security_validator

@pytest.mark.security
class TestSecurityValidation:
    """Test security validation features."""

    def test_pii_detection(self):
        """Test personally identifiable information detection."""
        validator = get_enhanced_security_validator()

        text_with_pii = "Contact John at john@example.com"
        findings = validator.detect_pii_patterns(text_with_pii)

        assert len(findings) > 0
        assert any("email" in f.finding_type for f in findings)

    def test_malicious_content_detection(self):
        """Test malicious content detection."""
        validator = get_enhanced_security_validator()

        malicious_text = "<script>alert('xss')</script>"
        findings = validator.detect_malicious_patterns(malicious_text)

        assert len(findings) > 0
        assert any("script_injection" in f.finding_type for f in findings)
```

### Performance Testing

```python
import pytest
import time
from vds_pdf_orchestrator.vds_styling_optimized import convert_markdown_to_vds_pdf_optimized

@pytest.mark.performance
@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics."""

    def test_processing_speed(self, sample_markdown_file, tmp_path):
        """Test PDF processing speed."""
        output_path = tmp_path / "output.pdf"

        start_time = time.time()
        result = convert_markdown_to_vds_pdf_optimized(
            sample_markdown_file, output_path
        )
        duration = time.time() - start_time

        assert result["success"]
        assert duration < 30.0  # Should complete within 30 seconds
        assert output_path.exists()

    def test_memory_usage(self, large_markdown_file, tmp_path):
        """Test memory usage during processing."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        output_path = tmp_path / "large_output.pdf"

        result = convert_markdown_to_vds_pdf_optimized(
            large_markdown_file, output_path,
            max_memory_mb=512
        )

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        assert result["success"]
        assert memory_increase < 100 * 1024 * 1024  # Less than 100MB increase
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'

    - name: Install dependencies
      run: |
        pip install -e .
        pip install -r tests/requirements.txt

    - name: Run tests
      run: |
        python tests/run_tests.py --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./test-reports/coverage.xml
```

### Docker CI/CD

```dockerfile
# Dockerfile.ci - CI testing image
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY pyproject.toml .
RUN pip install -e .

# Install test dependencies
COPY tests/requirements.txt ./tests/
RUN pip install -r tests/requirements.txt

# Copy source code
COPY src/ ./src/
COPY tests/ ./tests/

# Run tests
CMD ["python", "tests/run_tests.py", "--all"]
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    stages {
        stage('Test')
    }

    stage('Test') {
        parallel {
            stage('Unit Tests') {
                steps {
                    sh 'python tests/run_tests.py --unit --coverage'
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov'
                    ])
                }
            }

            stage('Integration Tests') {
                steps {
                    sh 'python tests/run_tests.py --integration'
                }
            }

            stage('Security Tests') {
                steps {
                    sh 'python tests/run_tests.py --security'
                }
            }
        }
    }
}
```

## Test Data Management

### Test Data Organization

```
tests/test_data/
├── markdown/
│   ├── simple.md
│   ├── large.md
│   └── suspicious.md
├── pdf/
│   ├── sample.pdf
│   ├── encrypted.pdf
│   └── corrupted.pdf
├── images/
│   ├── logo.png
│   └── photo.jpg
└── configs/
    ├── valid.json
    └── invalid.json
```

### Test Data Best Practices

1. **Size Management**: Keep test data files small and focused
2. **Version Control**: Include only necessary test data in repository
3. **Privacy**: Avoid real PII or sensitive information
4. **Format**: Use standard, well-formatted test data
5. **Cleanup**: Remove temporary test files after use

### Dynamic Test Data Generation

```python
@pytest.fixture
def generate_large_markdown(size: str = "medium") -> str:
    """Generate markdown content of specified size."""
    if size == "small":
        return "# Small Document\n\nContent here."

    elif size == "medium":
        content = ["# Medium Document\n\n"]
        for i in range(10):
            content.extend([f"## Section {i}\n\n", "Content.\n\n"])
        return "".join(content)

    elif size == "large":
        content = ["# Large Document\n\n"]
        for i in range(100):
            content.extend([f"## Section {i}\n\n", "Content. " * 20, "\n\n"])
        return "".join(content)
```

## Troubleshooting

### Common Issues

#### Test Failures Due to Missing Dependencies

**Problem**: Tests fail with import errors
```bash
ModuleNotFoundError: No module named 'pytest'
```

**Solution**:
```bash
pip install -r tests/requirements.txt
```

#### Redis Connection Failures

**Problem**: Integration tests fail with Redis connection errors
```bash
redis.exceptions.ConnectionError: Error 111 connecting to Redis
```

**Solution**:
1. Start Redis service: `docker run -d -p 6379:6379 redis:alpine`
2. Skip Redis tests: `pytest -m "not requires_redis"`
3. Use mock Redis in tests

#### Docker Test Failures

**Problem**: Container tests fail with Docker errors
```bash
docker.errors.DockerException: Error while fetching server API version
```

**Solution**:
1. Ensure Docker is running and accessible
2. Check Docker permissions
3. Use container-specific test markers

#### Memory Test Failures

**Problem**: Performance tests fail due to insufficient memory
```bash
MemoryError: Unable to allocate array
```

**Solution**:
1. Increase available memory
2. Reduce test data size
3. Use memory-optimized test settings

#### Coverage Reporting Issues

**Problem**: Coverage reports are incomplete or inaccurate
```bash
Coverage.py warning: No data was collected.
```

**Solution**:
1. Ensure tests import the modules you want to cover
2. Check `.coveragerc` configuration
3. Run tests with `--cov` flag

### Debugging Tips

1. **Verbose Output**: Use `--verbose` flag for detailed test output
2. **Debug Mode**: Use `--pdb` to drop into debugger on failures
3. **Stop on First Failure**: Use `--maxfail=1` to stop at first error
4. **Print Logs**: Add print statements or use logging in tests
5. **Check Test Order**: Use `--collect-only` to see test collection order

### Performance Optimization

1. **Parallel Execution**: Use pytest-xdist for parallel test runs
2. **Test Isolation**: Ensure tests don't interfere with each other
3. **Fixture Optimization**: Use scope-appropriate fixtures
4. **Mocking**: Mock slow external dependencies
5. **Test Selection**: Run only relevant tests for changes

### Test Environment Setup

1. **Isolated Environment**: Use virtual environments for testing
2. **Consistent Dependencies**: Pin test dependency versions
3. **Clean State**: Ensure clean test environment before runs
4. **Resource Monitoring**: Monitor system resources during testing
5. **Log Analysis**: Review test logs for issues

## Best Practices

### Test Writing

1. **Arrange-Act-Assert**: Structure tests clearly with AAA pattern
2. **Descriptive Names**: Use clear, descriptive test and function names
3. **Single Responsibility**: Each test should verify one behavior
4. **Independent Tests**: Tests should not depend on each other
5. **Idempotent**: Tests should produce the same result on repeated runs

### Test Organization

1. **Logical Grouping**: Group related tests in classes
2. **Marker Usage**: Use pytest markers for test categorization
3. **Fixture Usage**: Use fixtures for shared setup/teardown
4. **Parameterization**: Use parameterized tests for multiple scenarios
5. **Documentation**: Add docstrings explaining test purpose

### CI/CD Integration

1. **Fast Feedback**: Run fast tests first for quick feedback
2. **Parallel Execution**: Use parallel execution for faster CI runs
3. **Coverage Gates**: Set minimum coverage thresholds
4. **Test Reporting**: Generate comprehensive test reports
5. **Failure Notifications**: Configure alerts for test failures

### Security Testing

1. **Vulnerability Scanning**: Include security vulnerability tests
2. **Data Privacy**: Ensure test data doesn't contain real PII
3. **Authentication Testing**: Test authentication and authorization
4. **Input Validation**: Test input validation and sanitization
5. **Penetration Testing**: Include security-focused test scenarios

---

For more information about testing practices, refer to:
- [pytest documentation](https://docs.pytest.org/)
- [Python testing best practices](https://docs.python.org/3/library/unittest.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Framework**: pytest 8.0+