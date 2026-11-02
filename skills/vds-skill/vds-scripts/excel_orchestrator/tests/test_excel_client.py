"""Tests for ExcelClient."""

from __future__ import annotations

import pytest

from vds_excel_orchestrator.errors import (
    ExcelFileNotFoundError,
    ExcelSheetExistsError,
    ExcelSheetNotFoundError,
)
from vds_excel_orchestrator.excel_client import ExcelClient


def test_create_workbook(temp_excel_file: Path) -> None:
    """Test creating a new workbook."""
    new_file = temp_excel_file.parent / "new.xlsx"
    with ExcelClient(new_file) as client:
        client.create()
        assert client.list_sheets() == ["Sheet"]
        client.save()

    assert new_file.exists()
    new_file.unlink()


def test_open_workbook(temp_excel_file: Path) -> None:
    """Test opening an existing workbook."""
    with ExcelClient(temp_excel_file, read_only=True) as client:
        client.open()
        sheets = client.list_sheets()
        assert len(sheets) > 0


def test_list_sheets(temp_excel_file: Path) -> None:
    """Test listing sheets."""
    with ExcelClient(temp_excel_file, read_only=True) as client:
        client.open()
        sheets = client.list_sheets()
        assert isinstance(sheets, list)
        assert len(sheets) > 0


def test_create_sheet(temp_excel_file: Path) -> None:
    """Test creating a new sheet."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        client.create_sheet("TestSheet")
        sheets = client.list_sheets()
        assert "TestSheet" in sheets
        client.save()


def test_delete_sheet(temp_excel_file: Path) -> None:
    """Test deleting a sheet."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        client.create_sheet("ToDelete")
        client.delete_sheet("ToDelete")
        sheets = client.list_sheets()
        assert "ToDelete" not in sheets
        client.save()


def test_rename_sheet(temp_excel_file: Path) -> None:
    """Test renaming a sheet."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        client.create_sheet("OldName")
        client.rename_sheet("OldName", "NewName")
        sheets = client.list_sheets()
        assert "NewName" in sheets
        assert "OldName" not in sheets
        client.save()


def test_copy_sheet(temp_excel_file: Path) -> None:
    """Test copying a sheet."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        client.copy_sheet("Sheet", "CopySheet")
        sheets = client.list_sheets()
        assert "CopySheet" in sheets
        client.save()


def test_get_set_cell(temp_excel_file: Path) -> None:
    """Test getting and setting cell values."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        client.set_cell("Sheet", "B2", "Test Value")
        value = client.get_cell("Sheet", "B2")
        assert value == "Test Value"
        client.save()


def test_read_write_range(temp_excel_file: Path) -> None:
    """Test reading and writing ranges."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        data = [["A", "B", "C"], [1, 2, 3], [4, 5, 6]]
        client.write_range("Sheet", "A1", data)
        read_data = client.read_range("Sheet", "A1:C3")
        assert len(read_data) == 3
        client.save()


def test_sheet_not_found_error(temp_excel_file: Path) -> None:
    """Test error handling for non-existent sheet."""
    with ExcelClient(temp_excel_file, read_only=True) as client:
        client.open()
        with pytest.raises(ExcelSheetNotFoundError):
            client.get_sheet("NonExistentSheet")


def test_sheet_exists_error(temp_excel_file: Path) -> None:
    """Test error handling for existing sheet."""
    with ExcelClient(temp_excel_file) as client:
        client.open()
        with pytest.raises(ExcelSheetExistsError):
            client.create_sheet("Sheet")
        client.save()


def test_file_not_found_error() -> None:
    """Test error handling for non-existent file."""
    client = ExcelClient("/nonexistent/file.xlsx")
    with pytest.raises(ExcelFileNotFoundError):
        client.open()
