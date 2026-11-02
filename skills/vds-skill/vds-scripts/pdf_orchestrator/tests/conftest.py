"""
Pytest configuration and fixtures for VDS PDF Orchestrator testing.

Provides shared test fixtures, configuration, and utilities for
unit, integration, and container testing.
"""

import json
import os
import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vds_pdf_orchestrator.config import PDFSettings as Settings
from vds_pdf_orchestrator.config import load_settings


class MemoryMonitor:
    """Minimal memory monitor test double."""

    def snapshot(self) -> dict[str, int]:
        return {"rss": 0}


class RedisSessionManager:
    """Minimal Redis session manager test double."""

    def __init__(self, client: Any):
        self.client = client


class _ErrorHandler:
    """Simple in-memory error handler for tests."""

    def __init__(self) -> None:
        self.history: list[str] = []

    def clear_history(self) -> None:
        self.history.clear()


_ERROR_HANDLER = _ErrorHandler()


def get_error_handler() -> _ErrorHandler:
    return _ERROR_HANDLER


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Test data directory fixture."""
    test_dir = Path(__file__).parent / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path]:
    """Temporary directory fixture."""
    temp_path = Path(tempfile.mkdtemp(prefix="vds_pdf_test_"))
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path)


@pytest.fixture
def sample_markdown_file(test_data_dir: Path) -> Path:
    """Create a sample markdown file for testing."""
    content = """# Test Document

This is a sample markdown document for testing purposes.

## Features

- **Bold text**
- *Italic text*
- `Code snippets`

## Table Example

| Name | Age | City |
|------|-----|------|
| John | 30  | NYC  |
| Jane | 25  | LA   |

## Code Block

```python
def hello_world():
    print("Hello, World!")
    return True
```

## List

1. First item
2. Second item
   - Nested item
   - Another nested item

> This is a blockquote for testing purposes.

---

*Document created for VDS PDF Orchestrator testing*
"""

    md_file = test_data_dir / "sample.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def large_markdown_file(test_data_dir: Path) -> Path:
    """Create a large markdown file for memory testing."""
    content_parts = ["# Large Test Document\n\n"]

    # Generate a large document
    for i in range(1000):
        content_parts.append(f"## Section {i}\n\n")
        content_parts.append(f"This is section {i} with some content. ")
        content_parts.append(
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        )
        content_parts.append(
            "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n\n"
        )

        # Add a table in every 10th section
        if i % 10 == 0:
            content_parts.append("| Column 1 | Column 2 | Column 3 |\n")
            content_parts.append("|----------|----------|----------|\n")
            for j in range(5):
                content_parts.append(
                    f"| Row {j}-{i} | Data {j}-{i} | Value {j}-{i} |\n"
                )
            content_parts.append("\n")

    content = "".join(content_parts)

    md_file = test_data_dir / "large.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def suspicious_markdown_file(test_data_dir: Path) -> Path:
    """Create a markdown file with potentially malicious content for security testing."""
    content = """# Suspicious Document

This document contains various security test patterns.

## Email Addresses
- admin@company.com
- john.doe@external.org

## Phone Numbers
- +1-555-123-4567
- (555) 987-6543

## URLs
- https://legitimate-site.com
- http://192.168.1.1/admin  # IP address URL
- https://suspicious-domain.org/malware

## JavaScript Patterns
```javascript
<script>alert('XSS attempt')</script>
eval('malicious code')
Function('dangerous code')()
```

## System Commands
- rm -rf /
- /etc/passwd
- ${HOME}/.ssh/id_rsa

## Base64 Content
SGVsbG8gV29ybGQ=  # "Hello World"
PHNjcmlwdD5hbGVydCgneHNzJyk8L3NjcmlwdD4=  # XSS attempt

## API Keys and Tokens
- AKIA1234567890123456  # AWS-like key
- ghp_1234567890abcdef1234567890abcdef123456  # GitHub-like token
- Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # JWT-like token
"""

    md_file = test_data_dir / "suspicious.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture
def test_settings() -> Settings:
    """Test settings fixture."""
    return load_settings()


@pytest.fixture
def memory_monitor() -> MemoryMonitor:
    """Memory monitor fixture."""
    return MemoryMonitor()


@pytest.fixture
def mock_redis():
    """Mock Redis fixture for testing."""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = False
    mock_client.expire.return_value = True
    mock_client.hset.return_value = 1
    mock_client.hget.return_value = json.dumps({"status": "completed"})
    mock_client.hgetall.return_value = {
        "status": json.dumps("completed"),
        "created_at": json.dumps(1234567890),
    }
    return mock_client


@pytest.fixture
def redis_session_manager(mock_redis):
    """Redis session manager fixture with mock Redis."""
    return RedisSessionManager(client=mock_redis)


@pytest.fixture
def error_handler():
    """Error handler fixture."""
    return get_error_handler()


@pytest.fixture(autouse=True)
def reset_error_handler():
    """Reset error handler before each test."""
    handler = get_error_handler()
    handler.clear_history()
    yield
    handler.clear_history()


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Sample PDF bytes for testing."""
    # This is a minimal valid PDF header
    return b"""%PDF-1.7
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 5 0 R
>>
>>
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj

5 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj

xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000370 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
456
%%EOF"""


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, json_data: dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = json.dumps(json_data)

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@pytest.fixture
def mock_http_response():
    """Mock HTTP response fixture."""

    def _create_response(data: dict[str, Any], status: int = 200) -> MockResponse:
        return MockResponse(data, status)

    return _create_response


@pytest.fixture
def container_test_config():
    """Container test configuration."""
    return {
        "image_name": "vds-pdf-orchestrator:test",
        "container_name": "vds-pdf-test",
        "ports": {"api": "18080:8080", "mcp": "18000:8000", "metrics": "19090:9090"},
        "environment": {
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG",
            "MAX_FILE_SIZE": "10485760",  # 10MB
            "REDIS_HOST": "test-redis",
        },
        "volumes": {"test_data": "/app/test_data", "test_logs": "/app/logs"},
        "health_check": {"endpoint": "/health", "timeout": 30, "retries": 3},
    }


# Test utilities
def create_test_file(path: Path, content: str, encoding: str = "utf-8") -> Path:
    """Create a test file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=encoding)
    return path


def create_test_binary_file(path: Path, content: bytes) -> Path:
    """Create a test binary file with given content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def assert_pdf_valid(pdf_path: Path):
    """Assert that a PDF file is valid."""
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
    # Check PDF header
    with open(pdf_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"


def assert_log_contains(log_file: Path, content: str):
    """Assert that log file contains specific content."""
    if log_file.exists():
        log_content = log_file.read_text()
        assert content in log_content


# Skip conditions — env-var gated, NO live probing at import/collection time.
def skip_if_no_docker():
    """True when Docker tests should be skipped (env var not set)."""
    return os.environ.get("VDS_PDF_TEST_DOCKER") != "1"


def skip_if_no_redis():
    """True when Redis tests should be skipped (env var not set)."""
    return os.environ.get("VDS_PDF_TEST_REDIS") != "1"


def skip_if_no_internet():
    """True when internet tests should be skipped (env var not set)."""
    return os.environ.get("VDS_PDF_TEST_INTERNET") != "1"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "container: marks tests as container tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "security: marks tests as security-focused")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line(
        "markers", "requires_docker: marks tests that require Docker"
    )
    config.addinivalue_line("markers", "requires_redis: marks tests that require Redis")
    config.addinivalue_line(
        "markers", "requires_internet: marks tests that require internet"
    )


def pytest_collection_modifyitems(config, items):
    """Add skip markers using env-var gating — NO live service probing.

    Set ``VDS_PDF_TEST_DOCKER=1``, ``VDS_PDF_TEST_REDIS=1``, or
    ``VDS_PDF_TEST_INTERNET=1`` to enable respective test categories.
    """
    docker_enabled = os.environ.get("VDS_PDF_TEST_DOCKER") == "1"
    redis_enabled = os.environ.get("VDS_PDF_TEST_REDIS") == "1"
    internet_enabled = os.environ.get("VDS_PDF_TEST_INTERNET") == "1"

    for item in items:
        if "requires_docker" in item.keywords and not docker_enabled:
            item.add_marker(
                pytest.mark.skip(
                    reason="Docker tests disabled — set VDS_PDF_TEST_DOCKER=1"
                )
            )
        if "requires_redis" in item.keywords and not redis_enabled:
            item.add_marker(
                pytest.mark.skip(
                    reason="Redis tests disabled — set VDS_PDF_TEST_REDIS=1"
                )
            )
        if "requires_internet" in item.keywords and not internet_enabled:
            item.add_marker(
                pytest.mark.skip(
                    reason="Internet tests disabled — set VDS_PDF_TEST_INTERNET=1"
                )
            )


# Test data generators
def generate_test_markdown(size: str = "small") -> str:
    """Generate test markdown content of different sizes."""
    if size == "small":
        return """# Small Test Document

This is a small test document.
- Item 1
- Item 2
"""
    elif size == "medium":
        content = ["# Medium Test Document\n\n"]
        for i in range(10):
            content.extend(
                [
                    f"## Section {i}\n\n",
                    "This is section content with some text.\n\n",
                    f"- List item {i}.1\n",
                    f"- List item {i}.2\n\n",
                ]
            )
        return "".join(content)
    elif size == "large":
        content = ["# Large Test Document\n\n"]
        for i in range(100):
            content.extend(
                [
                    f"## Section {i}\n\n",
                    "This is a large section with substantial content. " * 10,
                    "\n\n",
                    f"### Subsection {i}.1\n\n",
                    "More content here to make the document larger. " * 5,
                    "\n\n",
                ]
            )
        return "".join(content)
    else:
        raise ValueError(f"Unknown size: {size}")


# Test environment setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment."""
    load_settings()

    yield

    # Cleanup
    pass
