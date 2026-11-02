# VDS CLI Common

Shared CLI infrastructure for VDS orchestrator CLIs.

## Overview

`vds-cli-common` provides a unified set of building blocks for creating consistent CLI applications across the VDS ecosystem. It standardizes output formatting, error handling, shell completions, and testing patterns.

## Features

- **CLIContext**: Dataclass for passing CLI state (verbosity, output format, color settings)
- **OutputManager**: Rich-based output formatting with JSON/table/text modes
- **ErrorHandler**: Consistent error handling with exit codes
- **Version Callback**: Factory for `--version` flags
- **Completers**: Shell completion helpers for common patterns
- **Testing Fixtures**: pytest fixtures for CLI testing

## Installation

```bash
# Add as dependency in pyproject.toml
dependencies = [
    "vds-cli-common @ file:///${PROJECT_ROOT}/../vds_cli_common",
]

# Or install directly
uv add ../vds_cli_common
```

## Quick Start

```python
from vds_cli_common import CLIContext, OutputManager, ExitCodes, create_version_callback

# Create context with CLI options
ctx = CLIContext(verbose=True, output_format="json", no_color=False)

# Use OutputManager for consistent output
output = OutputManager(ctx)
output.success("Operation completed")
output.print_json({"key": "value"})

# Handle errors consistently
from vds_cli_common import ErrorHandler
handler = ErrorHandler(ctx)
handler.handle_error(some_exception)
```

## Modules

### `context`

```python
from vds_cli_common import CLIContext

ctx = CLIContext(
    verbose=False,      # Enable verbose output
    debug=False,        # Enable debug output
    quiet=False,        # Suppress non-essential output
    output_format="text",  # text, json, table
    no_color=False,     # Disable colored output
)
```

### `output`

```python
from vds_cli_common import OutputManager

output = OutputManager(ctx)
output.info("Information message")
output.success("Success message")
output.warning("Warning message")
output.error("Error message")
output.debug("Debug message")  # Only shown if ctx.debug=True
output.verbose("Verbose message")  # Only shown if ctx.verbose=True

# Structured output
output.print_json(data)
output.print_table(rows, columns=["Name", "Value"])
```

### `errors`

```python
from vds_cli_common import ErrorHandler, ExitCodes, CLIError

# Standard exit codes
ExitCodes.SUCCESS  # 0
ExitCodes.GENERAL_ERROR  # 1
ExitCodes.CONFIG_ERROR  # 2
ExitCodes.AUTH_ERROR  # 3
ExitCodes.NETWORK_ERROR  # 4
ExitCodes.NOT_FOUND  # 5
ExitCodes.VALIDATION_ERROR  # 6

# Custom CLI errors
raise CLIError("Something went wrong", exit_code=ExitCodes.VALIDATION_ERROR)

# Error handler
handler = ErrorHandler(ctx)
exit_code = handler.handle_error(exception)
```

### `version`

```python
from vds_cli_common import create_version_callback
import typer

app = typer.Typer()

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        callback=create_version_callback("my-cli", "1.0.0"),
        is_eager=True,
    ),
):
    pass
```

### `completers`

```python
from vds_cli_common import complete_from_list, complete_path, complete_choice

# Static list completion
@app.command()
def cmd(
    project: str = typer.Option(
        ..., 
        autocompletion=complete_from_list(["lep", "insurance", "saving"]),
    ),
):
    pass

# Path completion
@app.command()
def cmd(
    file: str = typer.Option(..., autocompletion=complete_path()),
):
    pass
```

### `testing`

```python
import pytest
from vds_cli_common.testing import cli_runner, captured_output, mock_context

def test_my_command(cli_runner):
    result = cli_runner.invoke(app, ["my-command"])
    assert result.exit_code == 0

def test_output(captured_output):
    output = OutputManager(mock_context())
    output.success("Done")
    assert "Done" in captured_output.getvalue()
```

## Development

```bash
cd WHO-project/vds-scripts/vds_cli_common

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=vds_cli_common --cov-report=term-missing

# Lint
uv run ruff check src tests
uv run ruff format src tests
```

## Requirements

- Python >= 3.11
- typer>=0.24.1
- rich>=14.3.3

## License

MIT
