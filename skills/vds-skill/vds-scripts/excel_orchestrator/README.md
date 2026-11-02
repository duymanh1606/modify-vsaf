# VDS Excel Orchestrator

Excel (.xlsx) file manipulation orchestrator for the VDS platform. Provides comprehensive capabilities for reading, writing, sheet management, cell manipulation, formatting, and data conversion.

## Features

- ✅ **File Operations**: Open, create, save Excel files
- ✅ **Sheet Management**: List, create, delete, rename, copy sheets
- ✅ **Cell Operations**: Read, write, clear cell values and formulas
- ✅ **Range Operations**: Read and write ranges of cells
- ✅ **Formatting**: Apply fonts, colors, alignment, borders, number formats
- ✅ **Data Conversion**: Convert Excel to/from JSON and CSV
- ✅ **Validation**: Validate Excel file structure and format
- ✅ **CLI Integration**: Integrated with unified VDS CLI

## Installation

```bash
cd vds-scripts/excel_orchestrator
uv sync --project excel_orchestrator
```

## Usage

### Via Unified VDS CLI (Recommended)

```bash
# List all sheets
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- sheet list --file data.xlsx

# Get cell value
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- cell get --file data.xlsx --sheet Sheet1 --cell A1

# Set cell value
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- cell set --file data.xlsx --sheet Sheet1 --cell A1 --value "Hello"

# Read range
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- range read --file data.xlsx --sheet Sheet1 --range A1:C10

# Create sheet
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- sheet create --file data.xlsx --name "NewSheet"

# Delete sheet
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- sheet delete --file data.xlsx --name "OldSheet"

# Rename sheet
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- sheet rename --file data.xlsx --old "OldName" --new "NewName"

# Copy sheet
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- sheet copy --file data.xlsx --source "Sheet1" --target "CopySheet"

# Apply formatting
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- format apply --file data.xlsx --sheet Sheet1 --cell A1 --bold --fill FFFF00

# Convert to JSON
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- convert --file data.xlsx --output data.json --format json

# Convert to CSV
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- convert --file data.xlsx --output data.csv --format csv

# Validate file
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- validate --file data.xlsx

# Generate target-state status workbook (Insurance defaults)
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- target-state-status

# Generate VDS-owned ULNC aligned workbook (strict reference presentation)
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- ulnc-align \
  --strict-presentation \
  --coverage-policy warn \
  --json

# Generate target-state status with custom paths
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- target-state-status \
  --arch-root WHO-project/insurance-document/projects/INSURANCE/analysis/target-state/architecture \
  --output WHO-project/insurance-document/projects/INSURANCE/analysis/target-state/target-state-status.xlsx \
  --brd-report WHO-project/vds-scripts/scripts/brd_coverage_report.json
```

`target-state-status` also honors `VDS_INSURANCE_DOCS_ROOT` before falling back to WHO-first repo discovery.

### Direct Orchestrator Access

```bash
cd vds-scripts/excel_orchestrator
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel --help

# List sheets
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel sheet list data.xlsx

# Get cell
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel cell get data.xlsx --sheet Sheet1 --cell A1

# Create sheet
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel sheet create data.xlsx --name "NewSheet"

# Generate target-state status workbook (Insurance defaults)
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel target-state-status

# Generate VDS-owned ULNC aligned workbook
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel ulnc-align --strict-presentation --json
```

## API Usage

### Basic Operations

```python
from vds_excel_orchestrator.excel_client import ExcelClient

# Create new workbook
with ExcelClient("output.xlsx") as client:
    client.create()
    client.set_cell("Sheet1", "A1", "Hello")
    client.set_cell("Sheet1", "B1", "World")
    client.save()

# Open existing workbook
with ExcelClient("data.xlsx", read_only=True) as client:
    client.open()
    sheets = client.list_sheets()
    value = client.get_cell("Sheet1", "A1")
    data = client.read_range("Sheet1", "A1:C10")
```

### Sheet Management

```python
with ExcelClient("data.xlsx") as client:
    client.open()

    # Create sheet
    client.create_sheet("NewSheet")

    # Rename sheet
    client.rename_sheet("Sheet1", "RenamedSheet")

    # Copy sheet
    client.copy_sheet("RenamedSheet", "CopySheet")

    # Delete sheet
    client.delete_sheet("CopySheet")

    client.save()
```

### Formatting

```python
from vds_excel_orchestrator.formatters import CellFormatter
from vds_excel_orchestrator.excel_client import ExcelClient

with ExcelClient("data.xlsx") as client:
    client.open()
    sheet = client.get_sheet("Sheet1")

    # Apply font
    CellFormatter.apply_font(sheet, "A1", name="Arial", size=12, bold=True)

    # Apply fill color
    CellFormatter.apply_fill(sheet, "A1", fill_color="FFFF00")

    # Apply alignment
    CellFormatter.apply_alignment(sheet, "A1", horizontal="center", vertical="center")

    # Apply number format
    CellFormatter.apply_currency_format(sheet, "B1")

    client.save()
```

### Data Conversion

```python
from vds_excel_orchestrator.converters import ExcelConverter

# Excel to JSON
data = ExcelConverter.to_json("data.xlsx", sheet_name="Sheet1", output_path="output.json")

# Excel to CSV
data = ExcelConverter.to_csv("data.xlsx", sheet_name="Sheet1", output_path="output.csv")

# JSON to Excel
ExcelConverter.from_json([{"name": "John", "age": 30}], "output.xlsx", sheet_name="Data")

# CSV to Excel
ExcelConverter.from_csv("data.csv", "output.xlsx", sheet_name="Data")
```

### Validation

```python
from vds_excel_orchestrator.validators import ExcelValidator

# Validate file
result = ExcelValidator.validate_file("data.xlsx")
print(f"Valid: {result['valid']}")
print(f"Sheets: {result['sheet_count']}")

# Validate sheet name
ExcelValidator.validate_sheet_name("MySheet")

# Validate cell reference
ExcelValidator.validate_cell_ref("A1")

# Validate range reference
ExcelValidator.validate_range_ref("A1:C10")
```

## Command Reference

### Sheet Commands

- `sheet list` - List all sheets in Excel file
- `sheet create` - Create a new sheet
- `sheet delete` - Delete a sheet
- `sheet rename` - Rename a sheet
- `sheet copy` - Copy a sheet

### Cell Commands

- `cell get` - Get cell value
- `cell set` - Set cell value

### Range Commands

- `range read` - Read range of cells
- `range write` - Write data to range (from JSON file)

### Format Commands

- `format apply` - Apply formatting to a cell

### Utility Commands

- `convert` - Convert Excel to JSON or CSV
- `validate` - Validate Excel file structure
- `target-state-status` - Generate target-state-status.xlsx from target-state task files
- `target-state-status-vi` - Generate target-state-status-vi.xlsx from target-state task files
- `ulnc-align` - Generate VDS-owned ULNC workbook aligned to ULNL reference format/presentation with coverage and buffer reporting

## Dependencies

- `openpyxl==3.1.5` - Primary Excel manipulation library
- `xlsxwriter==3.2.9` - Advanced writing features (optional)
- `typer==0.24.1` - CLI framework
- `pydantic==2.12.5` - Data validation
- `structlog==25.5.0` - Structured logging
- `rich==14.3.3` - Console output

## Testing

```bash
cd vds-scripts/excel_orchestrator
uv run pytest tests/ -v
```

## Error Handling

The orchestrator provides comprehensive error handling with custom exception classes:

- `ExcelOrchestratorError` - Base exception
- `ExcelFileError` - File operation errors
- `ExcelFileNotFoundError` - File not found
- `ExcelFileInvalidError` - Invalid file format
- `ExcelSheetError` - Sheet operation errors
- `ExcelSheetNotFoundError` - Sheet not found
- `ExcelSheetExistsError` - Sheet already exists
- `ExcelCellError` - Cell operation errors
- `ExcelRangeError` - Range operation errors
- `ExcelValidationError` - Validation errors
- `ExcelConversionError` - Conversion errors

## Examples

See the `examples/` directory for sample scripts demonstrating various use cases.

## Integration

The Excel orchestrator is integrated with the unified VDS CLI. All commands are accessible via:

```bash
./scripts/worktree_uv.sh run --project vds_cli vds-cli excel -- <command> [options]
```

## License

Part of the VDS Platform orchestrator ecosystem.
