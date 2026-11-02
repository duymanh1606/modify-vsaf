import markdown
from weasyprint import CSS, HTML


def create_styled_pdf(markdown_file, output_pdf):
    """
    Reads a Markdown file, converts it to styled HTML, and generates a PDF.
    """
    # --- 1. Read Markdown Content ---
    try:
        with open(markdown_file, encoding="utf-8") as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"Error: Markdown file not found at {markdown_file}")
        return

    # --- 2. Convert Markdown to HTML ---
    # Using extensions for better compatibility, e.g., for tables
    html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    # --- 3. Apply Professional CSS Styling ---
    # This CSS is designed for professional reports, with better fonts and spacing.
    # It uses common system fonts that are likely to support a wide range of characters.
    css_styles = """
    @page {
        size: A4;
        margin: 2cm;
    }
    body {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        line-height: 1.5;
        color: #333;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Georgia', serif;
        color: #2c3e50;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
    }
    h1 { border-bottom: 2px solid #ddd; padding-bottom: 5px; }
    h2 { border-bottom: 1px solid #eee; padding-bottom: 5px; }
    p {
        margin-bottom: 1em;
    }
    code {
        font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
        background-color: #f8f8f8;
        padding: 2px 4px;
        border-radius: 3px;
        font-size: 0.9em;
    }
    pre {
        background-color: #f8f8f8;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 1em;
        overflow-x: auto;
    }
    pre code {
        background-color: transparent;
        padding: 0;
        border-radius: 0;
        font-size: 0.9em;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    """

    # --- 4. Generate PDF with WeasyPrint ---
    try:
        html = HTML(string=html_content)
        css = CSS(string=css_styles)
        html.write_pdf(output_pdf, stylesheets=[css])
        print(f"Successfully generated PDF: {output_pdf}")
    except Exception as e:
        print(f"Error during PDF generation with WeasyPrint: {e}")


if __name__ == "__main__":
    create_styled_pdf("AGENTS.md", "AGENTS_styled.pdf")
