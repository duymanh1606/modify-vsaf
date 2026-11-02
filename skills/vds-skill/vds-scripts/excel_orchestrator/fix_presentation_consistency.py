"""
Fix Presentation Consistency

This script ensures consistent formatting across all rows and columns:
1. Headers: Bold, colored background, centered, bordered
2. Summary: Properly formatted with borders
3. Data rows: Consistent borders and alignment
4. Column widths: Appropriate widths for each column
"""

from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

EXCEL_PATH = Path(
    "../../insurance-document/projects/INSURANCE/analysis/reference/vietin/estimation/Estimation_HTBH.xlsx"
)


def fix_presentation_consistency(excel_path: Path):
    """Fix presentation consistency across all rows and columns."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("=" * 80)
    print("Fixing Presentation Consistency")
    print("=" * 80)

    # Define styles
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    summary_header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    summary_header_font = Font(bold=True, color="FFFFFF", size=12)
    summary_label_font = Font(bold=True, size=11)

    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    separator_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")

    # Step 1: Fix header row (row 1)
    print("\nStep 1: Fixing header row...")
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = border
    print("  ✅ Header row formatted")

    # Step 2: Fix summary rows (rows 2-7)
    print("\nStep 2: Fixing summary rows...")
    for row in range(2, 8):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row, col)
            cell.border = border

            # First row of summary (TỔNG KẾT)
            if row == 2 and col == 1:
                cell.fill = summary_header_fill
                cell.font = summary_header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # Label column (column 1)
            elif col == 1:
                cell.font = summary_label_font
                cell.alignment = Alignment(horizontal="left", vertical="center")
            # Value column (column 2) - numbers
            elif col == 2:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0.00"
    print("  ✅ Summary rows formatted")

    # Step 3: Fix separator row (row 8)
    print("\nStep 3: Fixing separator row...")
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(8, col)
        cell.fill = separator_fill
        cell.border = border
    print("  ✅ Separator row formatted")

    # Step 4: Fix data rows (rows 9+)
    print("\nStep 4: Fixing data rows...")
    border_fixed = 0
    alignment_fixed = 0
    format_fixed = 0

    for row in range(9, ws.max_row + 1):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row, col)

            # Always apply border (ensure consistency)
            cell.border = border
            if not cell.border:
                border_fixed += 1

            # Apply alignment based on column type
            if col in [1, 5]:  # Service ID, Task ID - center
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if not cell.alignment:
                    alignment_fixed += 1
            elif col in [9, 11, 12]:  # Numbers - right align
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if isinstance(cell.value, (int, float)):
                    if col in [9, 11]:
                        cell.number_format = "#,##0.00"
                        format_fixed += 1
                    elif col == 12:
                        cell.number_format = "#,##0"
                        format_fixed += 1
            else:  # Text columns - left align
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                if not cell.alignment:
                    alignment_fixed += 1

    print("  ✅ Applied borders to all data cells")
    print("  ✅ Applied alignment to all data cells")
    print(f"  ✅ Applied number formats to {format_fixed} cells")

    # Step 5: Set column widths
    print("\nStep 5: Setting column widths...")
    column_widths = {
        1: 12,  # Service ID
        2: 40,  # Service Name
        3: 15,  # Responsibility
        4: 25,  # Task Category
        5: 12,  # Task ID
        6: 60,  # Task Name
        7: 25,  # BRD Reference
        8: 18,  # Complexity
        9: 18,  # Base Effort
        10: 35,  # Multiplier
        11: 18,  # Final Days
        12: 18,  # Final Hours
        13: 30,  # Dependencies
        14: 60,  # Notes
    }

    for col, width in column_widths.items():
        if col <= ws.max_column:
            ws.column_dimensions[chr(64 + col)].width = width
            print(f"  Column {col}: {width}")

    # Step 6: Ensure consistent row heights
    print("\nStep 6: Setting row heights...")
    # Header row
    ws.row_dimensions[1].height = 30
    # Summary rows
    for row in range(2, 8):
        ws.row_dimensions[row].height = 20
    # Data rows
    for row in range(9, ws.max_row + 1):
        ws.row_dimensions[row].height = 18

    print("  ✅ Row heights set")

    wb.save(excel_path)
    print("\n✅ Presentation consistency fixed")


def verify_presentation(excel_path: Path):
    """Verify presentation consistency."""
    wb = load_workbook(excel_path, data_only=False)
    ws = wb["VDS_Task_Breakdown_Detailed"]

    print("\n" + "=" * 80)
    print("Verifying Presentation Consistency")
    print("=" * 80)

    # Check header
    header_ok = True
    for col in range(1, ws.max_column + 1):
        cell = ws.cell(1, col)
        if not (cell.fill and cell.font and cell.border and cell.alignment):
            header_ok = False
            break

    print(f"\nHeader row: {'✅ Consistent' if header_ok else '⚠️ Issues found'}")

    # Check summary
    summary_ok = True
    for row in range(2, 8):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row, col)
            if not cell.border:
                summary_ok = False
                break

    print(f"Summary rows: {'✅ Consistent' if summary_ok else '⚠️ Issues found'}")

    # Check data rows (sample)
    data_ok = True
    sample_size = min(100, ws.max_row - 8)
    for row in range(9, 9 + sample_size):
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row, col)
            if not cell.border:
                data_ok = False
                break

    print(f"Data rows (sample {sample_size}): {'✅ Consistent' if data_ok else '⚠️ Issues found'}")

    # Check column widths
    print("\nColumn widths:")
    for col in range(1, min(15, ws.max_column + 1)):
        width = ws.column_dimensions[chr(64 + col)].width
        print(f"  Column {col}: {width}")

    print("\n" + "=" * 80)
    if header_ok and summary_ok and data_ok:
        print("✅ Presentation is consistent!")
    else:
        print("⚠️ Some issues found")
    print("=" * 80)


def main():
    """Main execution."""
    fix_presentation_consistency(EXCEL_PATH)
    verify_presentation(EXCEL_PATH)


if __name__ == "__main__":
    main()
