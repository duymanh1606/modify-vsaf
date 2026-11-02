"""Domain errors for Excel orchestrator (consistent with VDS orchestrators)."""

from __future__ import annotations

from typing import Any


class ExcelOrchestratorError(RuntimeError):
    """Base class for Excel orchestrator errors."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ExcelFileError(ExcelOrchestratorError):
    """Raised when Excel file operations fail."""

    pass


class ExcelFileNotFoundError(ExcelFileError):
    """Raised when Excel file is not found."""

    pass


class ExcelFileInvalidError(ExcelFileError):
    """Raised when Excel file format is invalid."""

    pass


class ExcelSheetError(ExcelOrchestratorError):
    """Raised when sheet operations fail."""

    pass


class ExcelSheetNotFoundError(ExcelSheetError):
    """Raised when a sheet is not found."""

    pass


class ExcelSheetExistsError(ExcelSheetError):
    """Raised when attempting to create a sheet that already exists."""

    pass


class ExcelCellError(ExcelOrchestratorError):
    """Raised when cell operations fail."""

    pass


class ExcelRangeError(ExcelOrchestratorError):
    """Raised when range operations fail."""

    pass


class ExcelValidationError(ExcelOrchestratorError):
    """Raised when validation fails."""

    pass


class ExcelConversionError(ExcelOrchestratorError):
    """Raised when conversion operations fail."""

    pass


__all__ = [
    "ExcelOrchestratorError",
    "ExcelFileError",
    "ExcelFileNotFoundError",
    "ExcelFileInvalidError",
    "ExcelSheetError",
    "ExcelSheetNotFoundError",
    "ExcelSheetExistsError",
    "ExcelCellError",
    "ExcelRangeError",
    "ExcelValidationError",
    "ExcelConversionError",
]
