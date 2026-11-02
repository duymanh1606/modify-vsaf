"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vds_excel_orchestrator.excel_client import ExcelClient


@pytest.fixture
def temp_excel_file() -> Path:
    """Create a temporary Excel file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = Path(f.name)

    # Create a simple workbook
    with ExcelClient(temp_path) as client:
        client.create()
        client.set_cell("Sheet", "A1", "Test")
        client.save()

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
