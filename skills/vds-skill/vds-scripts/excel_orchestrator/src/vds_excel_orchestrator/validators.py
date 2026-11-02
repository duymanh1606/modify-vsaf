"""Validation utilities for Excel files and data."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .errors import ExcelFileInvalidError, ExcelFileNotFoundError, ExcelValidationError
from .logging import get_logger

logger = get_logger(__name__)


class ExcelValidator:
    """Utility class for validating Excel files and data."""

    @staticmethod
    def validate_file(file_path: str | Path, max_size_mb: int = 100) -> dict[str, Any]:
        """Validate Excel file structure and format.

        Args:
            file_path: Path to Excel file
            max_size_mb: Maximum file size in MB

        Returns:
            Dictionary with validation results

        Raises:
            ExcelFileNotFoundError: If file doesn't exist
            ExcelFileInvalidError: If file is invalid
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ExcelFileNotFoundError(f"File not found: {file_path}", context={"path": str(file_path)})

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ExcelFileInvalidError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum ({max_size_mb} MB)",
                context={
                    "path": str(file_path),
                    "size_mb": file_size_mb,
                    "max_mb": max_size_mb,
                },
            )

        # Check if it's a valid ZIP file (xlsx is a ZIP archive)
        try:
            with zipfile.ZipFile(file_path, "r") as zip_file:
                zip_file.testzip()
        except zipfile.BadZipFile as exc:
            raise ExcelFileInvalidError(
                f"File is not a valid ZIP archive: {exc}",
                context={"path": str(file_path)},
            ) from exc

        # Try to open with openpyxl
        try:
            workbook = load_workbook(filename=str(file_path), read_only=True, data_only=True)
            sheet_count = len(workbook.sheetnames)
            workbook.close()

            result = {
                "valid": True,
                "path": str(file_path),
                "size_mb": round(file_size_mb, 2),
                "sheet_count": sheet_count,
                "sheet_names": workbook.sheetnames,
            }

            logger.info("File validated", **result)
            return result

        except Exception as exc:
            raise ExcelFileInvalidError(f"Failed to open Excel file: {exc}", context={"path": str(file_path)}) from exc

    @staticmethod
    def validate_sheet_name(sheet_name: str) -> bool:
        """Validate sheet name.

        Args:
            sheet_name: Sheet name to validate

        Returns:
            True if valid

        Raises:
            ExcelValidationError: If sheet name is invalid
        """
        if not sheet_name:
            raise ExcelValidationError("Sheet name cannot be empty")

        if len(sheet_name) > 31:
            raise ExcelValidationError(f"Sheet name too long (max 31 characters): {sheet_name}")

        invalid_chars = [":", "\\", "/", "?", "*", "[", "]"]
        for char in invalid_chars:
            if char in sheet_name:
                raise ExcelValidationError(f"Sheet name contains invalid character '{char}': {sheet_name}")

        return True

    @staticmethod
    def validate_cell_ref(cell_ref: str) -> bool:
        """Validate cell reference.

        Args:
            cell_ref: Cell reference (e.g., 'A1')

        Returns:
            True if valid

        Raises:
            ExcelValidationError: If cell reference is invalid
        """
        if not cell_ref:
            raise ExcelValidationError("Cell reference cannot be empty")

        # Basic validation - should match pattern like A1, AA100, etc.
        import re

        pattern = r"^[A-Z]+[0-9]+$"
        if not re.match(pattern, cell_ref.upper()):
            raise ExcelValidationError(f"Invalid cell reference format: {cell_ref}")

        return True

    @staticmethod
    def validate_range_ref(range_ref: str) -> bool:
        """Validate range reference.

        Args:
            range_ref: Range reference (e.g., 'A1:C10')

        Returns:
            True if valid

        Raises:
            ExcelValidationError: If range reference is invalid
        """
        if not range_ref:
            raise ExcelValidationError("Range reference cannot be empty")

        # Should contain colon separator
        if ":" not in range_ref:
            raise ExcelValidationError(f"Range reference must contain ':' separator: {range_ref}")

        parts = range_ref.split(":")
        if len(parts) != 2:
            raise ExcelValidationError(f"Range reference must have exactly two parts: {range_ref}")

        # Validate both cell references
        ExcelValidator.validate_cell_ref(parts[0])
        ExcelValidator.validate_cell_ref(parts[1])

        return True


__all__ = ["ExcelValidator"]
