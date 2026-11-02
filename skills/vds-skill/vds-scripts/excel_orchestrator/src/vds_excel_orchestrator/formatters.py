"""Formatting utilities for Excel cells and ranges."""

from __future__ import annotations

from typing import Any

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from .errors import ExcelCellError
from .logging import get_logger

logger = get_logger(__name__)


class CellFormatter:
    """Utility class for applying formatting to Excel cells."""

    @staticmethod
    def apply_font(sheet: Worksheet, cell_ref: str, **font_kwargs: Any) -> None:
        """Apply font formatting to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            **font_kwargs: Font properties (name, size, bold, italic, color, etc.)
        """
        try:
            cell = sheet[cell_ref]
            font = Font(**font_kwargs) if font_kwargs else Font()
            if cell.font:
                # Merge with existing font
                font = Font(
                    name=font_kwargs.get("name", cell.font.name),
                    size=font_kwargs.get("size", cell.font.size),
                    bold=font_kwargs.get("bold", cell.font.bold),
                    italic=font_kwargs.get("italic", cell.font.italic),
                    color=font_kwargs.get("color", cell.font.color),
                )
            cell.font = font
            logger.debug("Font applied", cell=cell_ref, font_kwargs=font_kwargs)
        except Exception as exc:
            raise ExcelCellError(f"Failed to apply font to {cell_ref}: {exc}", context={"cell": cell_ref}) from exc

    @staticmethod
    def apply_fill(sheet: Worksheet, cell_ref: str, fill_color: str, pattern_type: str = "solid") -> None:
        """Apply fill (background color) to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            fill_color: Hex color code (e.g., 'FF0000' for red)
            pattern_type: Fill pattern type (default: 'solid')
        """
        try:
            cell = sheet[cell_ref]
            fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type=pattern_type)
            cell.fill = fill
            logger.debug("Fill applied", cell=cell_ref, color=fill_color)
        except Exception as exc:
            raise ExcelCellError(f"Failed to apply fill to {cell_ref}: {exc}", context={"cell": cell_ref}) from exc

    @staticmethod
    def apply_alignment(
        sheet: Worksheet,
        cell_ref: str,
        horizontal: str = "general",
        vertical: str = "bottom",
        wrap_text: bool = False,
    ) -> None:
        """Apply alignment to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            horizontal: Horizontal alignment ('left', 'center', 'right', 'general')
            vertical: Vertical alignment ('top', 'center', 'bottom')
            wrap_text: Enable text wrapping
        """
        try:
            cell = sheet[cell_ref]
            alignment = Alignment(horizontal=horizontal, vertical=vertical, wrap_text=wrap_text)
            cell.alignment = alignment
            logger.debug(
                "Alignment applied",
                cell=cell_ref,
                horizontal=horizontal,
                vertical=vertical,
            )
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to apply alignment to {cell_ref}: {exc}",
                context={"cell": cell_ref},
            ) from exc

    @staticmethod
    def apply_border(
        sheet: Worksheet,
        cell_ref: str,
        border_style: str = "thin",
        color: str = "000000",
    ) -> None:
        """Apply border to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            border_style: Border style ('thin', 'medium', 'thick', etc.)
            color: Border color hex code
        """
        try:
            cell = sheet[cell_ref]
            side = Side(style=border_style, color=color)
            border = Border(left=side, right=side, top=side, bottom=side)
            cell.border = border
            logger.debug("Border applied", cell=cell_ref, style=border_style)
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to apply border to {cell_ref}: {exc}",
                context={"cell": cell_ref},
            ) from exc

    @staticmethod
    def apply_number_format(sheet: Worksheet, cell_ref: str, number_format: str) -> None:
        """Apply number format to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            number_format: Number format string (e.g., '#,##0.00', 'mm/dd/yyyy', '0%')
        """
        try:
            cell = sheet[cell_ref]
            cell.number_format = number_format
            logger.debug("Number format applied", cell=cell_ref, format=number_format)
        except Exception as exc:
            raise ExcelCellError(
                f"Failed to apply number format to {cell_ref}: {exc}",
                context={"cell": cell_ref},
            ) from exc

    @staticmethod
    def apply_date_format(sheet: Worksheet, cell_ref: str) -> None:
        """Apply date format to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
        """
        CellFormatter.apply_number_format(sheet, cell_ref, "mm/dd/yyyy")

    @staticmethod
    def apply_currency_format(sheet: Worksheet, cell_ref: str, symbol: str = "$") -> None:
        """Apply currency format to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            symbol: Currency symbol (default: '$')
        """
        if symbol == "$":
            CellFormatter.apply_number_format(sheet, cell_ref, '"$"#,##0.00')
        else:
            CellFormatter.apply_number_format(sheet, cell_ref, f'"{symbol}"#,##0.00')

    @staticmethod
    def apply_percentage_format(sheet: Worksheet, cell_ref: str, decimals: int = 0) -> None:
        """Apply percentage format to a cell.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            decimals: Number of decimal places (default: 0)
        """
        format_str = f"0.{'0' * decimals}%" if decimals > 0 else "0%"
        CellFormatter.apply_number_format(sheet, cell_ref, format_str)

    @staticmethod
    def apply_style(
        sheet: Worksheet,
        cell_ref: str,
        font: dict[str, Any] | None = None,
        fill: dict[str, Any] | None = None,
        alignment: dict[str, Any] | None = None,
        border: dict[str, Any] | None = None,
        number_format: str | None = None,
    ) -> None:
        """Apply multiple formatting styles at once.

        Args:
            sheet: Worksheet object
            cell_ref: Cell reference (e.g., 'A1')
            font: Font properties dict
            fill: Fill properties dict
            alignment: Alignment properties dict
            border: Border properties dict
            number_format: Number format string
        """
        if font:
            CellFormatter.apply_font(sheet, cell_ref, **font)
        if fill:
            CellFormatter.apply_fill(sheet, cell_ref, **fill)
        if alignment:
            CellFormatter.apply_alignment(sheet, cell_ref, **alignment)
        if border:
            CellFormatter.apply_border(sheet, cell_ref, **border)
        if number_format:
            CellFormatter.apply_number_format(sheet, cell_ref, number_format)


__all__ = ["CellFormatter"]
