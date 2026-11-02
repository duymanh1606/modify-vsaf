#!/usr/bin/env python3
"""
Demo script for the dynamic library selector implementation.

This script demonstrates the library selector's capabilities including:
- Dynamic library selection based on operation type
- Performance recommendations
- Library information and benchmarking
- AI workflow detection
"""

import sys
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vds_pdf_orchestrator.performance.library_selector import (
    OperationType,
    create_library_selector,
    select_library_for_ai_workflow,
    select_library_for_text_extraction,
)

from vds_pdf_orchestrator.config import load_settings


def demo_library_selection() -> None:
    """Demonstrate library selection capabilities."""

    # Load settings
    settings = load_settings()
    selector = create_library_selector(settings)

    # Demo different operation types
    operations = [
        (OperationType.TEXT_EXTRACTION, "Standard text extraction"),
        (OperationType.AI_WORKFLOW, "AI-powered document processing"),
        (OperationType.HIGH_VOLUME, "High-volume batch processing"),
        (OperationType.TABLE_EXTRACTION, "Table extraction"),
        (OperationType.METADATA_EXTRACTION, "Metadata extraction"),
    ]

    for operation, _description in operations:
        library = selector.select_optimal_library(operation)
        selector.get_performance_recommendations(operation)

    # Demo AI workflow hints

    selector.select_optimal_library(
        OperationType.TEXT_EXTRACTION, ai_workflow_hint=True
    )

    selector.select_optimal_library(OperationType.TEXT_EXTRACTION)

    # Demo library information

    for library in ["pymupdf", "pypdfium2", "pymupdf4llm"]:
        if library in selector._get_available_libraries():
            selector.get_library_info(library)


def demo_convenience_functions() -> None:
    """Demonstrate convenience functions."""

    settings = load_settings()

    # Text extraction
    select_library_for_text_extraction(settings)

    # AI workflow text extraction
    select_library_for_text_extraction(settings, ai_workflow=True)

    # AI workflow
    select_library_for_ai_workflow(settings)


def demo_performance_benchmarks() -> None:
    """Demonstrate performance benchmarking."""

    benchmarks = {
        "pypdfium2": {"speed": 0.003, "accuracy": 0.85, "memory_efficiency": 0.95},
        "pymupdf4llm": {"speed": 0.12, "accuracy": 0.95, "memory_efficiency": 0.80},
        "pymupdf": {"speed": 0.15, "accuracy": 0.92, "memory_efficiency": 0.85},
        "pypdf": {"speed": 1.11, "accuracy": 0.88, "memory_efficiency": 0.70},
    }

    for _library, _metrics in benchmarks.items():
        pass


def main() -> int:
    """Run the demo."""
    try:
        demo_library_selection()
        demo_convenience_functions()
        demo_performance_benchmarks()

    except Exception:
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
