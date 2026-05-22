"""CRAP and DRY analysis."""

from agentic_test_forge.analysis.crap import (
    CoverageDataMissingError,
    CrapFinding,
    CrapReport,
    analyze_crap,
    compute_crap_score,
)

__all__ = [
    "CoverageDataMissingError",
    "CrapFinding",
    "CrapReport",
    "analyze_crap",
    "compute_crap_score",
]
