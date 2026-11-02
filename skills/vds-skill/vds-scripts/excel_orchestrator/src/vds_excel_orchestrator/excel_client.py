"""Main Excel client for file and sheet manipulation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import Cell
from openpyxl.worksheet.worksheet import Worksheet

from .errors import (
    ExcelCellError,
    ExcelFileError,
    ExcelFileInvalidError,
    ExcelFileNotFoundError,
    ExcelRangeError,
    ExcelSheetError,
    ExcelSheetExistsError,
    ExcelSheetNotFoundError,
)
from .logging import get_logger

logger = get_logger(__name__)


class ExcelClient:
    """Main client for Excel file operations."""

    def __init__(self, file_path: str | Path, read_only: bool = False, data_only: bool = False) -> None:
        """Initialize Excel client.

        Args:
            file_path: Path to Excel file
            read_only: Open file in read-only mode
            data_only: Only read cell values, ignore formulas
        """
        self.file_path = Path(file_path)
        self.read_only = read_only
        self.data_only = data_only
        self._workbook: Workbook | None = None
        self._is_new = False

    def open(self) -> None:
        """Open existing Excel file."""
        if not self.file_path.exists():
            raise ExcelFileNotFoundError(
                f"Excel file not found: {self.file_path}",
                context={"path": str(self.file_path)},
            )

        try:
            self._workbook = load_workbook(
                filename=str(self.file_path),
                read_only=self.read_only,
                data_only=self.data_only,
                keep_vba=False,
            )
            logger.info("Excel file opened", path=str(self.file_path), read_only=self.read_only)
        except Exception as exc:
            raise ExcelFileInvalidError(
                f"Failed to open Excel file: {exc}",
                context={"path": str(self.file_path)},
            ) from exc

    def create(self) -> None:
        """Create a new Excel workbook."""
        self._workbook = Workbook()
        self._is_new = True
        logger.info("New Excel workbook created")

    def save(self, output_path: str | Path | None = None) -> None:
        """Save workbook to file.

        Args:
            output_path: Optional output path (defaults to original file_path)
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        save_path = Path(output_path) if output_path else self.file_path
        try:
            self._workbook.save(str(save_path))
            logger.info("Excel file saved", path=str(save_path))
        except Exception as exc:
            raise ExcelFileError(f"Failed to save Excel file: {exc}", context={"path": str(save_path)}) from exc

    def close(self) -> None:
        """Close workbook."""
        if self._workbook:
            self._workbook.close()
            self._workbook = None
            logger.info("Excel workbook closed")

    def __enter__(self) -> ExcelClient:
        """Context manager entry."""
        # Check if file exists and has content (valid Excel file)
        if self.file_path.exists() and self.file_path.stat().st_size > 0:
            # File exists and has content - try to open it
            try:
                self.open()
            except ExcelFileInvalidError:
                # File exists but is invalid - create new workbook
                self.create()
        else:
            # File doesn't exist or is empty - create new workbook
            self.create()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if not self.read_only and self._workbook:
            self.save()
        self.close()

    # Sheet operations

    def list_sheets(self) -> list[str]:
        """List all sheet names.

        Returns:
            List of sheet names
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        return self._workbook.sheetnames

    def get_sheet(self, sheet_name: str) -> Worksheet:
        """Get worksheet by name.

        Args:
            sheet_name: Name of the sheet

        Returns:
            Worksheet object

        Raises:
            ExcelSheetNotFoundError: If sheet doesn't exist
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        if sheet_name not in self._workbook.sheetnames:
            raise ExcelSheetNotFoundError(
                f"Sheet '{sheet_name}' not found",
                context={"sheet": sheet_name, "available": self._workbook.sheetnames},
            )

        return self._workbook[sheet_name]

    def create_sheet(self, sheet_name: str, index: int | None = None) -> Worksheet:
        """Create a new sheet.

        Args:
            sheet_name: Name for the new sheet
            index: Optional position index (defaults to end)

        Returns:
            Created Worksheet object

        Raises:
            ExcelSheetExistsError: If sheet already exists
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        if sheet_name in self._workbook.sheetnames:
            raise ExcelSheetExistsError(f"Sheet '{sheet_name}' already exists", context={"sheet": sheet_name})

        sheet = self._workbook.create_sheet(title=sheet_name, index=index)
        logger.info("Sheet created", sheet=sheet_name, index=index)
        return sheet

    def delete_sheet(self, sheet_name: str) -> None:
        """Delete a sheet.

        Args:
            sheet_name: Name of sheet to delete

        Raises:
            ExcelSheetNotFoundError: If sheet doesn't exist
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        if sheet_name not in self._workbook.sheetnames:
            raise ExcelSheetNotFoundError(f"Sheet '{sheet_name}' not found", context={"sheet": sheet_name})

        if len(self._workbook.sheetnames) == 1:
            raise ExcelSheetError(
                "Cannot delete the last sheet in workbook",
                context={"sheet": sheet_name},
            )

        del self._workbook[sheet_name]
        logger.info("Sheet deleted", sheet=sheet_name)

    def rename_sheet(self, old_name: str, new_name: str) -> None:
        """Rename a sheet.

        Args:
            old_name: Current sheet name
            new_name: New sheet name

        Raises:
            ExcelSheetNotFoundError: If old sheet doesn't exist
            ExcelSheetExistsError: If new name already exists
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        if old_name not in self._workbook.sheetnames:
            raise ExcelSheetNotFoundError(f"Sheet '{old_name}' not found", context={"sheet": old_name})

        if new_name in self._workbook.sheetnames:
            raise ExcelSheetExistsError(f"Sheet '{new_name}' already exists", context={"sheet": new_name})

        self._workbook[old_name].title = new_name
        logger.info("Sheet renamed", old_name=old_name, new_name=new_name)

    def copy_sheet(self, source_name: str, target_name: str) -> Worksheet:
        """Copy a sheet.

        Args:
            source_name: Source sheet name
            target_name: Target sheet name

        Returns:
            Copied Worksheet object

        Raises:
            ExcelSheetNotFoundError: If source sheet doesn't exist
            ExcelSheetExistsError: If target name already exists
        """
        if self._workbook is None:
            raise ExcelFileError("No workbook loaded. Call open() or create() first.")

        if source_name not in self._workbook.sheetnames:
            raise ExcelSheetNotFoundError(f"Sheet '{source_name}' not found", context={"sheet": source_name})

        if target_name in self._workbook.sheetnames:
            raise ExcelSheetExistsError(f"Sheet '{target_name}' already exists", context={"sheet": target_name})

        source_sheet = self._workbook[source_name]
        target_sheet = self._workbook.copy_worksheet(source_sheet)
        target_sheet.title = target_name
        logger.info("Sheet copied", source=source_name, target=target_name)
        return target_sheet

    # Cell operations

    def get_cell(self, sheet_name: str, cell_ref: str) -> Any:
        """Get cell value.

        Args:
            sheet_name: Name of the sheet
            cell_ref: Cell reference (e.g., 'A1')

        Returns:
            Cell value
        """
        sheet = self.get_sheet(sheet_name)
        try:
            cell = sheet[cell_ref]
            return cell.value
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to get cell {cell_ref}: {exc}",
                context={"sheet": sheet_name, "cell": cell_ref},
            ) from exc

    def set_cell(self, sheet_name: str, cell_ref: str, value: Any) -> None:
        """Set cell value.

        Args:
            sheet_name: Name of the sheet
            cell_ref: Cell reference (e.g., 'A1')
            value: Value to set
        """
        if self.read_only:
            raise ExcelFileError("Cannot modify read-only workbook")

        sheet = self.get_sheet(sheet_name)
        try:
            sheet[cell_ref] = value
            logger.debug("Cell set", sheet=sheet_name, cell=cell_ref, value=value)
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to set cell {cell_ref}: {exc}",
                context={"sheet": sheet_name, "cell": cell_ref, "value": value},
            ) from exc

    def clear_cell(self, sheet_name: str, cell_ref: str) -> None:
        """Clear cell value.

        Args:
            sheet_name: Name of the sheet
            cell_ref: Cell reference (e.g., 'A1')
        """
        if self.read_only:
            raise ExcelFileError("Cannot modify read-only workbook")

        sheet = self.get_sheet(sheet_name)
        try:
            sheet[cell_ref] = None
            logger.debug("Cell cleared", sheet=sheet_name, cell=cell_ref)
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to clear cell {cell_ref}: {exc}",
                context={"sheet": sheet_name, "cell": cell_ref},
            ) from exc

    def get_formula(self, sheet_name: str, cell_ref: str) -> str | None:
        """Get cell formula.

        Args:
            sheet_name: Name of the sheet
            cell_ref: Cell reference (e.g., 'A1')

        Returns:
            Formula string or None if cell has no formula
        """
        sheet = self.get_sheet(sheet_name)
        try:
            cell = sheet[cell_ref]
            return cell.value if isinstance(cell, Cell) and str(cell.value).startswith("=") else None
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to get formula from cell {cell_ref}: {exc}",
                context={"sheet": sheet_name, "cell": cell_ref},
            ) from exc

    def set_formula(self, sheet_name: str, cell_ref: str, formula: str) -> None:
        """Set cell formula.

        Args:
            sheet_name: Name of the sheet
            cell_ref: Cell reference (e.g., 'A1')
            formula: Formula string (with or without '=' prefix)
        """
        if self.read_only:
            raise ExcelFileError("Cannot modify read-only workbook")

        if not formula.startswith("="):
            formula = f"={formula}"

        sheet = self.get_sheet(sheet_name)
        try:
            sheet[cell_ref] = formula
            logger.debug("Formula set", sheet=sheet_name, cell=cell_ref, formula=formula)
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to set formula in cell {cell_ref}: {exc}",
                context={"sheet": sheet_name, "cell": cell_ref, "formula": formula},
            ) from exc

    # Range operations

    def read_range(self, sheet_name: str, range_ref: str) -> list[list[Any]]:
        """Read range of cells.

        Args:
            sheet_name: Name of the sheet
            range_ref: Range reference (e.g., 'A1:C10')

        Returns:
            2D list of cell values
        """
        sheet = self.get_sheet(sheet_name)
        try:
            cells = sheet[range_ref]
            if isinstance(cells, tuple):
                # Multiple rows
                return [[cell.value for cell in row] for row in cells]
            else:
                # Single row
                return [[cell.value for cell in cells]]
        except Exception as exc:
            raise ExcelRangeError(
                f"Failed to read range {range_ref}: {exc}",
                context={"sheet": sheet_name, "range": range_ref},
            ) from exc

    def write_range(self, sheet_name: str, start_cell: str, data: list[list[Any]]) -> None:
        """Write data to range of cells.

        Args:
            sheet_name: Name of the sheet
            start_cell: Starting cell reference (e.g., 'A1')
            data: 2D list of values to write
        """
        if self.read_only:
            raise ExcelFileError("Cannot modify read-only workbook")

        sheet = self.get_sheet(sheet_name)
        try:
            from openpyxl.utils import get_column_letter

            start_col, start_row = sheet[start_cell].column, sheet[start_cell].row

            for row_idx, row_data in enumerate(data):
                for col_idx, value in enumerate(row_data):
                    col_letter = get_column_letter(start_col + col_idx)
                    cell_ref = f"{col_letter}{start_row + row_idx}"
                    sheet[cell_ref] = value

            logger.debug("Range written", sheet=sheet_name, start_cell=start_cell, rows=len(data))
        except Exception as exc:
            raise ExcelRangeError(
                f"Failed to write range starting at {start_cell}: {exc}",
                context={"sheet": sheet_name, "start_cell": start_cell},
            ) from exc

    def clear_range(self, sheet_name: str, range_ref: str) -> None:
        """Clear range of cells.

        Args:
            sheet_name: Name of the sheet
            range_ref: Range reference (e.g., 'A1:C10')
        """
        if self.read_only:
            raise ExcelFileError("Cannot modify read-only workbook")

        sheet = self.get_sheet(sheet_name)
        try:
            cells = sheet[range_ref]
            if isinstance(cells, tuple):
                for row in cells:
                    for cell in row:
                        cell.value = None
            else:
                for cell in cells:
                    cell.value = None
            logger.debug("Range cleared", sheet=sheet_name, range=range_ref)
        except Exception as exc:
            raise ExcelRangeError(
                f"Failed to clear range {range_ref}: {exc}",
                context={"sheet": sheet_name, "range": range_ref},
            ) from exc


__all__ = ["ExcelClient"]
