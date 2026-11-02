"""Example script demonstrating basic Excel operations."""

from pathlib import Path

from vds_excel_orchestrator.converters import ExcelConverter
from vds_excel_orchestrator.excel_client import ExcelClient
from vds_excel_orchestrator.formatters import CellFormatter
from vds_excel_orchestrator.validators import ExcelValidator


def main() -> None:
    """Demonstrate basic Excel operations."""
    # Create a new workbook
    output_file = Path("example_output.xlsx")

    print("Creating new Excel workbook...")
    with ExcelClient(output_file) as client:
        client.create()

        # Set some cell values
        client.set_cell("Sheet1", "A1", "Name")
        client.set_cell("Sheet1", "B1", "Age")
        client.set_cell("Sheet1", "C1", "City")

        client.set_cell("Sheet1", "A2", "John")
        client.set_cell("Sheet1", "B2", 30)
        client.set_cell("Sheet1", "C2", "New York")

        client.set_cell("Sheet1", "A3", "Jane")
        client.set_cell("Sheet1", "B3", 25)
        client.set_cell("Sheet1", "C3", "London")

        # Apply formatting to header row
        sheet = client.get_sheet("Sheet1")
        CellFormatter.apply_font(sheet, "A1", bold=True, size=12)
        CellFormatter.apply_font(sheet, "B1", bold=True, size=12)
        CellFormatter.apply_font(sheet, "C1", bold=True, size=12)
        CellFormatter.apply_fill(sheet, "A1", fill_color="CCCCCC")
        CellFormatter.apply_fill(sheet, "B1", fill_color="CCCCCC")
        CellFormatter.apply_fill(sheet, "C1", fill_color="CCCCCC")

        # Create a new sheet
        client.create_sheet("Summary")
        client.set_cell("Summary", "A1", "Total Records")
        client.set_cell("Summary", "B1", 2)

        client.save()

    print(f"Excel file created: {output_file}")

    # Read data back
    print("\nReading data from Excel file...")
    with ExcelClient(output_file, read_only=True) as client:
        client.open()

        # List sheets
        sheets = client.list_sheets()
        print(f"Sheets: {', '.join(sheets)}")

        # Read a range
        data = client.read_range("Sheet1", "A1:C3")
        print("\nData from Sheet1:")
        for row in data:
            print(f"  {row}")

        # Get a specific cell
        value = client.get_cell("Summary", "B1")
        print(f"\nTotal records: {value}")

    # Convert to JSON
    print("\nConverting to JSON...")
    json_data = ExcelConverter.to_json(output_file, sheet_name="Sheet1", include_headers=True)
    print(f"JSON data: {json_data}")

    # Validate file
    print("\nValidating file...")
    validation_result = ExcelValidator.validate_file(output_file)
    print(f"Valid: {validation_result['valid']}")
    print(f"Sheet count: {validation_result['sheet_count']}")

    print("\nExample completed successfully!")


if __name__ == "__main__":
    main()
