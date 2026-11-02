"""Tests for validators."""

from __future__ import annotations

from pathlib import Path

import pytest

from vds_excel_orchestrator.errors import ExcelValidationError
from vds_excel_orchestrator.validators import ExcelValidator


def test_validate_file(temp_excel_file: Path) -> None:
    """Test file validation."""
    result = ExcelValidator.validate_file(temp_excel_file)
    assert result["valid"] is True
    assert "sheet_count" in result
    assert "sheet_names" in result


def test_validate_sheet_name() -> None:
    """Test sheet name validation."""
    ExcelValidator.validate_sheet_name("ValidSheet")
    ExcelValidator.validate_sheet_name("Sheet_123")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_sheet_name("")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_sheet_name("A" * 32)  # Too long

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_sheet_name("Sheet:Name")  # Invalid character


def test_validate_cell_ref() -> None:
    """Test cell reference validation."""
    ExcelValidator.validate_cell_ref("A1")
    ExcelValidator.validate_cell_ref("AA100")
    ExcelValidator.validate_cell_ref("Z999")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_cell_ref("")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_cell_ref("1A")  # Wrong order

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_cell_ref("A")  # Missing number


def test_validate_range_ref() -> None:
    """Test range reference validation."""
    ExcelValidator.validate_range_ref("A1:C10")
    ExcelValidator.validate_range_ref("AA1:ZZ100")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_range_ref("")

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_range_ref("A1")  # Missing colon

    with pytest.raises(ExcelValidationError):
        ExcelValidator.validate_range_ref("A1:C10:D20")  # Too many parts
