"""VDS BRD Orchestrator - BRD coverage validation for VDS."""

from vds_brd_orchestrator.validator import (
    HIGH_PRIORITY_SERVICES,
    REQUIRED_BRD_SECTIONS,
    validate_brd_coverage,
    write_report,
)

__all__ = [
    "HIGH_PRIORITY_SERVICES",
    "REQUIRED_BRD_SECTIONS",
    "validate_brd_coverage",
    "write_report",
]

__version__ = "0.1.0"
