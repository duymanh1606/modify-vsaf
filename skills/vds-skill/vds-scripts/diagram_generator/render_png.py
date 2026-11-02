#!/usr/bin/env python3
"""Render PlantUML diagrams to PNG files."""

import subprocess
from pathlib import Path


def render_puml_to_png(puml_path: Path) -> Path | None:
    """Render a single PUML file to PNG.

    Returns the PNG path if successful, None otherwise.
    """
    png_path = puml_path.with_suffix(".png")

    try:
        result = subprocess.run(
            ["plantuml", "-tpng", str(puml_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and png_path.exists():
            return png_path
        print(f"  Error rendering {puml_path.name}: {result.stderr}")
        return None
    except subprocess.TimeoutExpired:
        print(f"  Timeout rendering {puml_path.name}")
        return None
    except FileNotFoundError:
        print("  PlantUML not found. Install with: brew install plantuml")
        return None


def main():
    """Render all PUML files in the INSURANCE analysis directory."""
    base_path = Path(__file__).parent.parent.parent / "docs-nttc/projects/INSURANCE/analysis/current-state"

    puml_files = list(base_path.rglob("*.puml"))
    print(f"Found {len(puml_files)} PUML files to render")

    success_count = 0
    error_count = 0

    for puml_file in puml_files:
        print(f"Rendering {puml_file.name}...")
        png_path = render_puml_to_png(puml_file)
        if png_path:
            success_count += 1
            print(f"  Created: {png_path.name}")
        else:
            error_count += 1

    print("\n=== Summary ===")
    print(f"Successfully rendered: {success_count}")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    main()
