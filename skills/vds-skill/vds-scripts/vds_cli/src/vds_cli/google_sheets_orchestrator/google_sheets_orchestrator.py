from pathlib import Path

import gspread
import structlog
import typer
from rich.console import Console
from vds_cli_common.paths import get_vds_config_root

console = Console()
app = typer.Typer(help="Google Sheets orchestrator operations.")
logger = structlog.get_logger(__name__)

GOOGLE_SHEETS_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _build_client(auth_method: str, credentials_path: Path | None):
    method = auth_method.strip().lower()
    if method == "service_account":
        resolved_path = credentials_path or (get_vds_config_root() / "google_credentials.json")
        if not resolved_path.exists():
            console.print(f"[bold red]Error:[/bold red] Service account credentials file not found at {resolved_path}")
            raise typer.Exit(code=1) from None

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            str(resolved_path),
            GOOGLE_SHEETS_SCOPE,
        )
        client = gspread.service_account(credentials=creds)
        console.print(f"[bold green]Authenticated using service account: [/bold green]{resolved_path}")
        return client

    if method == "oauth":
        resolved_path = credentials_path or (get_vds_config_root() / "gspread_oauth.json")
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        client = gspread.oauth(
            scopes=GOOGLE_SHEETS_SCOPE,
            credentials_filename=resolved_path,
            authorized_user_filename=resolved_path.with_name("authorized_user.json"),
        )
        console.print(f"[bold green]Authenticated using OAuth: [/bold green]{resolved_path}")
        return client

    if method == "none":
        # gspread still needs a client object even when opening public sheets.
        console.print("[bold green]Attempting to read as a public sheet.[/bold green]")
        return gspread.service_account()

    console.print(
        "[bold red]Error:[/bold red] Invalid authentication method: "
        f"{auth_method}. Choose 'service_account', 'oauth', or 'none'."
    )
    raise typer.Exit(code=1) from None


@app.command()
def read(
    spreadsheet_url: str = typer.Option(
        ...,
        "--spreadsheet-url",
        "-u",
        help="URL of the Google Spreadsheet.",
    ),
    sheet_name: str = typer.Option(
        "Sheet1",
        "--sheet-name",
        "-n",
        help="Name of the worksheet to read.",
    ),
    auth_method: str = typer.Option(
        "service_account",
        "--auth-method",
        "-a",
        help="Authentication method: 'service_account', 'oauth', or 'none' (for public sheets).",
    ),
    credentials_path: Path | None = typer.Option(
        None,
        "--credentials-path",
        "-c",
        help="Path to the Google credentials file (e.g., service_account.json).",
    ),
):
    """Read data from a specified Google Sheet and print it to the console."""
    client = _build_client(auth_method, credentials_path)
    try:
        spreadsheet = client.open_by_url(spreadsheet_url)
        worksheet = spreadsheet.worksheet(sheet_name)
        data = worksheet.get_all_values()

        if data:
            console.print(
                f"[bold green]Successfully read data from '{sheet_name}' in '{spreadsheet.title}':[/bold green]"
            )
            for row_idx, row in enumerate(data, start=1):
                logger.info(f"Row {row_idx}", row=row)
        else:
            console.print(f"[bold yellow]No data found in sheet '{sheet_name}' in '{spreadsheet.title}'.[/bold yellow]")

    except gspread.exceptions.SpreadsheetNotFound:
        console.print(f"[bold red]Error:[/bold red] Spreadsheet not found at URL: {spreadsheet_url}")
        logger.exception("Spreadsheet not found", url=spreadsheet_url)
        raise typer.Exit(code=1) from None
    except gspread.exceptions.WorksheetNotFound:
        console.print(f"[bold red]Error:[/bold red] Worksheet '{sheet_name}' not found in the spreadsheet.")
        logger.exception("Worksheet not found", sheet_name=sheet_name, url=spreadsheet_url)
        console.print("[bold yellow]Available worksheets:[/bold yellow]")
        try:
            spreadsheet = client.open_by_url(spreadsheet_url)
            for worksheet in spreadsheet.worksheets():
                console.print(f"- {worksheet.title}")
        except Exception as exc:
            logger.exception("Failed to list worksheets")
            console.print(f"[bold red]Could not list worksheets: {exc}[/bold red]")
        raise typer.Exit(code=1) from None
    except gspread.exceptions.APIError as exc:
        console.print(f"[bold red]Error:[/bold red] Google Sheets API error: {exc}")
        logger.exception("Google Sheets API error", error=str(exc), auth_method=auth_method)
        console.print("[bold yellow]Please check your credentials and spreadsheet permissions.[/bold yellow]")
        if "Request had insufficient authentication scopes." in str(exc) and auth_method == "service_account":
            console.print(
                "[bold yellow]Ensure your service account has editor access to the spreadsheet "
                "and Google Drive API is enabled.[/bold yellow]"
            )
        if "Requested entity was not found" in str(exc) and auth_method == "none":
            console.print(
                "[bold yellow]The spreadsheet might not be publicly accessible. Try "
                "'oauth' or 'service_account' authentication.[/bold yellow]"
            )
        raise typer.Exit(code=1) from None
    except Exception as exc:
        logger.exception("An unexpected error occurred")
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


@app.command(name="list-worksheets")
def list_worksheets(
    spreadsheet_url: str = typer.Option(
        ...,
        "--spreadsheet-url",
        "-u",
        help="URL of the Google Spreadsheet.",
    ),
    auth_method: str = typer.Option(
        "service_account",
        "--auth-method",
        "-a",
        help="Authentication method: 'service_account', 'oauth', or 'none' (for public sheets).",
    ),
    credentials_path: Path | None = typer.Option(
        None,
        "--credentials-path",
        "-c",
        help="Path to the Google credentials file (e.g., service_account.json).",
    ),
):
    """List all worksheets in a specified Google Spreadsheet."""
    client = _build_client(auth_method, credentials_path)
    try:
        spreadsheet = client.open_by_url(spreadsheet_url)
        console.print(f"[bold green]Worksheets in '{spreadsheet.title}':[/bold green]")
        for worksheet in spreadsheet.worksheets():
            console.print(f"- {worksheet.title}")
    except Exception as exc:
        logger.exception("Failed to list worksheets")
        console.print(f"[bold red]An error occurred while listing worksheets:[/bold red] {exc}")
        raise typer.Exit(code=1) from None


if __name__ == "__main__":
    app()
