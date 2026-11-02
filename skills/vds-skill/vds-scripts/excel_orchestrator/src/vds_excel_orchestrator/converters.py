"""Data conversion utilities for Excel files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .errors import ExcelConversionError, ExcelFileError
from .excel_client import ExcelClient
from .logging import get_logger

logger = get_logger(__name__)


class ExcelConverter:
    """Utility class for converting Excel data to/from other formats."""

    @staticmethod
    def to_json(
        file_path: str | Path,
        sheet_name: str | None = None,
        include_headers: bool = True,
        output_path: str | Path | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Convert Excel sheet to JSON.

        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name (defaults to first sheet)
            include_headers: Use first row as headers
            output_path: Optional path to save JSON file

        Returns:
            Dictionary with sheet data or list of dictionaries (if include_headers=True)
        """
        try:
            with ExcelClient(file_path, read_only=True, data_only=True) as client:
                client.open()

                if sheet_name is None:
                    sheet_name = client.list_sheets()[0]

                # Get sheet and determine range
                sheet = client.get_sheet(sheet_name)
                # For read-only worksheets, calculate dimensions from max_row/max_column
                if hasattr(sheet, "dimensions"):
                    range_ref = sheet.dimensions
                else:
                    # ReadOnlyWorksheet - calculate from max_row and max_column
                    max_row = sheet.max_row
                    max_col = sheet.max_column
                    from openpyxl.utils import get_column_letter

                    if max_row > 0 and max_col > 0:
                        range_ref = f"A1:{get_column_letter(max_col)}{max_row}"
                    else:
                        range_ref = "A1:A1"  # Empty sheet

                data = client.read_range(sheet_name, range_ref)

                if include_headers and data:
                    headers = [str(cell) if cell is not None else f"Column{i + 1}" for i, cell in enumerate(data[0])]
                    rows = data[1:]
                    result = [dict(zip(headers, row, strict=False)) for row in rows]
                else:
                    result = data

                output = {sheet_name: result} if sheet_name else result

                if output_path:
                    Path(output_path).write_text(json.dumps(output, indent=2, default=str))
                    logger.info("JSON file saved", output_path=str(output_path))

                return output

        except Exception as exc:
            raise ExcelConversionError(
                f"Failed to convert Excel to JSON: {exc}",
                context={"file": str(file_path)},
            ) from exc

    @staticmethod
    def from_json(
        json_data: dict[str, Any] | list[dict[str, Any]],
        output_path: str | Path,
        sheet_name: str = "Sheet1",
    ) -> None:
        """Convert JSON data to Excel.

        Args:
            json_data: JSON data (dict with sheet names or list of records)
            output_path: Path to save Excel file
            sheet_name: Sheet name (if json_data is a list)
        """
        try:
            with ExcelClient(output_path) as client:
                client.create()

                if isinstance(json_data, list):
                    # List of records - single sheet
                    sheet = client.get_sheet(client.list_sheets()[0])
                    sheet.title = sheet_name

                    if json_data:
                        # Write headers
                        headers = list(json_data[0].keys())
                        client.write_range(sheet_name, "A1", [headers])

                        # Write data
                        rows = [[record.get(header, "") for header in headers] for record in json_data]
                        client.write_range(sheet_name, "A2", rows)

                elif isinstance(json_data, dict):
                    # Dictionary with sheet names
                    for name, data in json_data.items():
                        if isinstance(data, list) and data:
                            if name not in client.list_sheets():
                                client.create_sheet(name)
                            else:
                                sheet = client.get_sheet(name)

                            # Write headers
                            headers = list(data[0].keys()) if isinstance(data[0], dict) else []
                            if headers:
                                client.write_range(name, "A1", [headers])

                                # Write data
                                rows = [[record.get(header, "") for header in headers] for record in data]
                                client.write_range(name, "A2", rows)

                client.save()

            logger.info("Excel file created from JSON", output_path=str(output_path))

        except Exception as exc:
            raise ExcelConversionError(
                f"Failed to convert JSON to Excel: {exc}",
                context={"output": str(output_path)},
            ) from exc

    @staticmethod
    def to_csv(
        file_path: str | Path,
        sheet_name: str | None = None,
        output_path: str | Path | None = None,
    ) -> list[list[Any]]:
        """Convert Excel sheet to CSV.

        Args:
            file_path: Path to Excel file
            sheet_name: Sheet name (defaults to first sheet)
            output_path: Optional path to save CSV file

        Returns:
            List of rows (each row is a list of cell values)
        """
        try:
            with ExcelClient(file_path, read_only=True, data_only=True) as client:
                client.open()

                if sheet_name is None:
                    sheet_name = client.list_sheets()[0]

                sheet = client.get_sheet(sheet_name)
                data = client.read_range(sheet_name, sheet.dimensions)

                if output_path:
                    output_path = Path(output_path)
                    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
                        writer = csv.writer(csvfile)
                        for row in data:
                            writer.writerow([str(cell) if cell is not None else "" for cell in row])
                    logger.info("CSV file saved", output_path=str(output_path))

                return data

        except Exception as exc:
            raise ExcelConversionError(
                f"Failed to convert Excel to CSV: {exc}",
                context={"file": str(file_path)},
            ) from exc

    @staticmethod
    def from_csv(
        csv_path: str | Path,
        output_path: str | Path,
        sheet_name: str = "Sheet1",
    ) -> None:
        """Convert CSV to Excel.

        Args:
            csv_path: Path to CSV file
            output_path: Path to save Excel file
            sheet_name: Sheet name
        """
        try:
            csv_path = Path(csv_path)
            if not csv_path.exists():
                raise ExcelFileError(f"CSV file not found: {csv_path}")

            with csv_path.open("r", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                data = list(reader)

            with ExcelClient(output_path) as client:
                client.create()
                sheet = client.get_sheet(client.list_sheets()[0])
                sheet.title = sheet_name

                if data:
                    client.write_range(sheet_name, "A1", data)

                client.save()

            logger.info("Excel file created from CSV", output_path=str(output_path))

        except Exception as exc:
            raise ExcelConversionError(
                f"Failed to convert CSV to Excel: {exc}",
                context={"csv": str(csv_path), "output": str(output_path)},
            ) from exc


__all__ = ["ExcelConverter"]
