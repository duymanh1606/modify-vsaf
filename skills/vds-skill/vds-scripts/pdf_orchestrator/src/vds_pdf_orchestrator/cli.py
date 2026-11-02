"""Typer CLI for VDS PDF orchestrator."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

import typer
from markdown import markdown as markdown_to_html
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rich.console import Console
from rich.table import Table

from .config import load_settings

app = typer.Typer(help="VDS PDF orchestrator operations.")
console = Console()

UNICODE_FONT_CANDIDATES = [
    # Common Linux/macOS font paths (prefer Unicode-capable fonts).
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/local/share/fonts/DejaVuSans.ttf",
    "/opt/homebrew/share/fonts/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode MS.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",
    "/System/Library/Fonts/Supplemental/NotoSans-Regular.ttf",
]

ADVANCED_RENDER_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
  @bottom-right {
    content: "Trang " counter(page);
    font-size: 9pt;
    color: #6b7280;
  }
}
* {
  box-sizing: border-box;
}
body {
  font-family: "Arial Unicode MS", "Arial Unicode", "DejaVu Sans", "Noto Sans", sans-serif;
  color: #111827;
  line-height: 1.5;
  font-size: 11pt;
}
h1 {
  margin: 0 0 8px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #0f4c81;
  color: #0f4c81;
  font-size: 24pt;
  line-height: 1.2;
}
h2 {
  margin: 26px 0 8px 0;
  padding: 6px 10px;
  border-left: 4px solid #0f4c81;
  background: #f3f8fd;
  color: #0b3d66;
  font-size: 16pt;
}
h3 {
  margin: 18px 0 8px 0;
  color: #1e3a5f;
  font-size: 13pt;
}
h4, h5, h6 {
  margin: 12px 0 6px 0;
  color: #1f2937;
}
p {
  margin: 6px 0;
}
ul, ol {
  margin: 6px 0 10px 20px;
}
li {
  margin: 3px 0;
}
strong {
  color: #0b3d66;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0 14px 0;
  font-size: 10.5pt;
}
th {
  background: #eaf2fb;
  color: #0b3d66;
  border: 1px solid #d6e3f5;
  padding: 8px;
  text-align: left;
}
td {
  border: 1px solid #e5e7eb;
  padding: 8px;
  vertical-align: top;
}
blockquote {
  margin: 10px 0;
  padding: 8px 12px;
  border-left: 3px solid #2f6fab;
  background: #f8fbff;
  color: #1f2937;
}
code {
  background: #f3f4f6;
  padding: 1px 4px;
  border-radius: 4px;
  font-family: "Menlo", "Consolas", monospace;
  font-size: 10pt;
}
hr {
  border: none;
  border-top: 1px solid #d1d5db;
  margin: 16px 0;
}
.page-break {
  break-before: page;
}
"""


def _load_weasyprint_html() -> type | None:
    """Best-effort dynamic loader for WeasyPrint HTML renderer.

    Some environments miss native dependencies; suppress import noise and fall back cleanly.
    """
    stderr_buffer = io.StringIO()
    with contextlib.redirect_stderr(stderr_buffer):
        try:
            from weasyprint import HTML as WeasyHTML  # type: ignore
        except Exception:
            return None
    return WeasyHTML


def _parse_pages(pages: str, total_pages: int) -> list[int]:
    selected: set[int] = set()
    for chunk in [item.strip() for item in pages.split(",") if item.strip()]:
        if "-" in chunk:
            start_text, end_text = chunk.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            for page_number in range(start, end + 1):
                if 1 <= page_number <= total_pages:
                    selected.add(page_number)
        else:
            page_number = int(chunk)
            if 1 <= page_number <= total_pages:
                selected.add(page_number)
    return sorted(selected)


def _register_unicode_font() -> str:
    """Register a Unicode-capable TTF font and return its name.

    Falls back to Helvetica when no candidate font is available.
    """
    for idx, candidate in enumerate(UNICODE_FONT_CANDIDATES):
        font_path = Path(candidate)
        if not font_path.exists():
            continue
        font_name = f"VDSUnicodeFont{idx}"
        try:
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
        except Exception:
            continue
    return "Helvetica"


def _render_markdown_to_pdf_legacy(markdown_text: str, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    # invariant=1 pins the creation timestamp so byte-identical input → byte-identical PDF
    pdf_canvas = canvas.Canvas(str(output_file), pagesize=A4, invariant=1)
    width, height = A4
    cursor_y = height - 52
    margin_x = 48
    font_name = _register_unicode_font()
    bottom_margin = 40

    def ensure_space(min_space: int) -> None:
        nonlocal cursor_y
        if cursor_y <= bottom_margin + min_space:
            pdf_canvas.showPage()
            cursor_y = height - 52

    def draw_wrapped_text(
        text: str,
        *,
        font_size: float = 11,
        x_offset: float = 0,
        color: colors.Color = colors.black,
        leading_factor: float = 1.35,
    ) -> None:
        nonlocal cursor_y
        normalized_text = (
            text.replace("**", "")
            .replace("__", "")
            .replace("`", "")
            .replace("&nbsp;", " ")
            .strip()
        )
        if not normalized_text:
            return
        line_height = max(13, int(font_size * leading_factor))
        draw_x = margin_x + x_offset
        max_text_width = width - draw_x - margin_x
        wrapped_lines = simpleSplit(
            normalized_text, font_name, font_size, max_text_width
        )
        pdf_canvas.setFont(font_name, font_size)
        pdf_canvas.setFillColor(color)
        for wrapped_line in wrapped_lines:
            ensure_space(line_height + 2)
            pdf_canvas.drawString(draw_x, cursor_y, wrapped_line)
            cursor_y -= line_height
        pdf_canvas.setFillColor(colors.black)

    def draw_horizontal_rule() -> None:
        nonlocal cursor_y
        ensure_space(12)
        pdf_canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        pdf_canvas.setLineWidth(1)
        pdf_canvas.line(margin_x, cursor_y, width - margin_x, cursor_y)
        pdf_canvas.setStrokeColor(colors.black)
        cursor_y -= 12

    lines = markdown_text.splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index].replace("\t", "    ").rstrip()
        stripped = raw_line.strip()

        if not stripped:
            cursor_y -= 8
            index += 1
            continue

        if stripped == '<div class="page-break"></div>':
            pdf_canvas.showPage()
            cursor_y = height - 52
            index += 1
            continue

        if stripped in {"---", "***"}:
            draw_horizontal_rule()
            index += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            table_rows: list[list[str]] = []
            while index < len(lines):
                row_text = lines[index].strip()
                if not (row_text.startswith("|") and row_text.endswith("|")):
                    break
                if (
                    set(
                        row_text.replace("|", "")
                        .replace("-", "")
                        .replace(":", "")
                        .strip()
                    )
                    == set()
                ):
                    index += 1
                    continue
                cells = [cell.strip() for cell in row_text.strip("|").split("|")]
                table_rows.append(cells)
                index += 1

            if table_rows:
                header = " | ".join(table_rows[0])
                draw_wrapped_text(
                    header,
                    font_size=10.6,
                    x_offset=4,
                    color=colors.HexColor("#0B3D66"),
                    leading_factor=1.3,
                )
                draw_horizontal_rule()
                for row in table_rows[1:]:
                    draw_wrapped_text(
                        " | ".join(row),
                        font_size=10.0,
                        x_offset=8,
                        color=colors.HexColor("#1F2937"),
                        leading_factor=1.3,
                    )
                    cursor_y -= 1
                cursor_y -= 4
            continue

        if stripped.startswith("# "):
            draw_wrapped_text(
                stripped[2:].strip(),
                font_size=20,
                color=colors.HexColor("#0F4C81"),
                leading_factor=1.2,
            )
            draw_horizontal_rule()
            index += 1
            continue

        if stripped.startswith("## "):
            draw_wrapped_text(
                stripped[3:].strip(),
                font_size=15,
                color=colors.HexColor("#0B3D66"),
                leading_factor=1.25,
            )
            cursor_y -= 2
            index += 1
            continue

        if stripped.startswith("### "):
            draw_wrapped_text(
                stripped[4:].strip(),
                font_size=12.4,
                color=colors.HexColor("#1E3A5F"),
                leading_factor=1.3,
            )
            index += 1
            continue

        if stripped.startswith(">"):
            quote_text = stripped.lstrip(">").strip()
            draw_wrapped_text(
                f"• {quote_text}",
                font_size=10.5,
                x_offset=10,
                color=colors.HexColor("#374151"),
                leading_factor=1.35,
            )
            index += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            draw_wrapped_text(
                f"• {stripped[2:].strip()}",
                font_size=11,
                x_offset=10,
                color=colors.HexColor("#111827"),
            )
            index += 1
            continue

        numeric_prefix, separator, remaining = stripped.partition(". ")
        if separator and numeric_prefix.isdigit() and remaining:
            draw_wrapped_text(
                f"{numeric_prefix}. {remaining}",
                font_size=11,
                x_offset=6,
                color=colors.HexColor("#111827"),
            )
            index += 1
            continue

        draw_wrapped_text(
            stripped,
            font_size=11,
            color=colors.HexColor("#111827"),
            leading_factor=1.38,
        )
        index += 1

    pdf_canvas.save()


def _render_markdown_to_pdf(markdown_text: str, output_file: Path) -> None:
    """Render markdown to PDF with advanced styling and graceful fallback."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    if os.getenv("VDS_PDF_ENABLE_WEASYPRINT", "0") != "1":
        _render_markdown_to_pdf_legacy(markdown_text, output_file)
        return

    weasy_html = _load_weasyprint_html()
    if weasy_html is None:
        _render_markdown_to_pdf_legacy(markdown_text, output_file)
        return

    try:
        rendered_html = markdown_to_html(
            markdown_text,
            extensions=["extra", "sane_lists", "tables", "nl2br"],
        )
        html_document = (
            "<!DOCTYPE html>"
            "<html lang='vi'>"
            "<head>"
            "<meta charset='utf-8' />"
            f"<style>{ADVANCED_RENDER_CSS}</style>"
            "</head>"
            "<body>"
            f"{rendered_html}"
            "</body>"
            "</html>"
        )
        weasy_html(string=html_document, base_url=str(Path.cwd())).write_pdf(
            str(output_file)
        )
        return
    except Exception as render_error:
        console.print(
            f"[yellow]⚠️ Advanced render failed; using legacy renderer:[/yellow] {render_error}"
        )
        _render_markdown_to_pdf_legacy(markdown_text, output_file)


def _trim_trailing_blank_pages(pdf_path: Path) -> None:
    """Remove trailing blank pages produced by render pagination."""
    reader = PdfReader(str(pdf_path))
    if len(reader.pages) <= 1:
        return

    keep_until = len(reader.pages)
    while keep_until > 1:
        last_page_text = reader.pages[keep_until - 1].extract_text() or ""
        if last_page_text.strip():
            break
        keep_until -= 1

    if keep_until == len(reader.pages):
        return

    writer = PdfWriter()
    for page_index in range(keep_until):
        writer.add_page(reader.pages[page_index])
    with pdf_path.open("wb") as output_stream:
        writer.write(output_stream)


@app.command("version")
def version() -> None:
    """Show PDF orchestrator version."""
    console.print("[cyan]vds-pdf-orchestrator v0.1.0[/cyan]")


@app.command("md2pdf")
def md2pdf(
    markdown_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path | None = typer.Option(None, "-o", "--output"),
) -> None:
    """Convert Markdown file to PDF."""
    settings = load_settings()
    target_output = output or (settings.pdf_output_dir / f"{markdown_path.stem}.pdf")
    markdown_text = markdown_path.read_text(encoding="utf-8")
    _render_markdown_to_pdf(markdown_text, target_output)
    _trim_trailing_blank_pages(target_output)
    console.print(f"[green]✅ PDF created:[/green] {target_output}")


@app.command("validate")
def validate(
    pdf_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    strict: bool = typer.Option(False, "--strict"),
    format: str = typer.Option("table", "--format"),
) -> None:
    """Validate a PDF by attempting parse and basic policy checks."""
    reader = PdfReader(str(pdf_path))
    findings: list[str] = []
    if reader.is_encrypted:
        findings.append("PDF is encrypted")
    if strict and len(reader.pages) == 0:
        findings.append("PDF has zero pages")

    result = {
        "path": str(pdf_path),
        "valid": len(findings) == 0,
        "pages": len(reader.pages),
        "strict": strict,
        "findings": findings,
    }

    if format.lower() == "json":
        console.print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        table = Table(title="PDF Validation")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Path", result["path"])
        table.add_row("Valid", "✅ Yes" if result["valid"] else "❌ No")
        table.add_row("Pages", str(result["pages"]))
        table.add_row("Strict", "✅ Enabled" if strict else "❌ Disabled")
        table.add_row("Findings", ", ".join(findings) if findings else "None")
        console.print(table)

    if not result["valid"]:
        raise typer.Exit(1) from None


@app.command("extract-text")
def extract_text(
    pdf_path: Path = typer.Argument(..., exists=True, dir_okay=False),
    pages: str | None = typer.Option(None, "--pages", help="Page selection like 1-3,5"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Extract text from PDF pages."""
    reader = PdfReader(str(pdf_path))
    selected_pages = (
        _parse_pages(pages, len(reader.pages))
        if pages
        else list(range(1, len(reader.pages) + 1))
    )

    extracted_chunks: list[str] = []
    for page_number in selected_pages:
        text = reader.pages[page_number - 1].extract_text() or ""
        extracted_chunks.append(f"--- Page {page_number} ---\n{text}".rstrip())
    extracted_text_blob = "\n\n".join(extracted_chunks).strip()

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(extracted_text_blob, encoding="utf-8")
        console.print(f"[green]✅ Extracted text written:[/green] {output}")
    else:
        console.print(extracted_text_blob)


def main() -> None:
    """CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
