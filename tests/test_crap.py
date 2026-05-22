"""Tests for CRAP analysis."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_test_forge.analysis.crap import (
    CoverageDataMissingError,
    analyze_crap,
    compute_crap_score,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "crap_sample"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_compute_crap_score_standard() -> None:
    assert compute_crap_score(10, 1.0, "standard") == 10.0
    assert compute_crap_score(10, 0.0, "standard") == 110.0


def test_compute_crap_score_simplified() -> None:
    assert compute_crap_score(5, 1.0, "simplified") == 5.0
    assert compute_crap_score(5, 0.0, "simplified") == 6.0


def test_analyze_crap_missing_coverage(tmp_path: Path) -> None:
    module = tmp_path / "mod.py"
    module.write_text("def foo():\n    return 1\n", encoding="utf-8")
    with pytest.raises(CoverageDataMissingError):
        analyze_crap([module], threshold=30, search_root=tmp_path)


def _venv_python() -> Path:
    windows = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if windows.is_file():
        return windows
    unix = PROJECT_ROOT / ".venv" / "bin" / "python"
    if unix.is_file():
        return unix
    return Path(sys.executable)


def _run_fixture_coverage() -> Path:
    coverage_file = FIXTURE_ROOT / ".coverage"
    if coverage_file.exists():
        coverage_file.unlink()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(FIXTURE_ROOT / "src")
    subprocess.run(
        [
            str(_venv_python()),
            "-m",
            "pytest",
            "tests",
            "--cov=src",
            "-q",
            "--rootdir",
            str(FIXTURE_ROOT),
        ],
        cwd=FIXTURE_ROOT,
        env=env,
        check=True,
    )
    assert coverage_file.is_file()
    return coverage_file


def test_analyze_crap_fixture() -> None:
    coverage_file = _run_fixture_coverage()
    report = analyze_crap(
        [FIXTURE_ROOT / "src"],
        threshold=6,
        formula="standard",
        coverage_file=coverage_file,
        search_root=FIXTURE_ROOT,
    )

    by_name = {finding.qualified_name: finding for finding in report.findings}
    assert "simple" in by_name
    assert "complex_uncovered" in by_name
    assert by_name["simple"].coverage == 1.0
    assert by_name["complex_uncovered"].coverage == 0.0
    assert by_name["complex_uncovered"].crap_score > 6
    assert report.status == "fail"
    assert report.to_json().startswith("{")


def test_analyze_crap_passes_with_high_threshold() -> None:
    coverage_file = FIXTURE_ROOT / ".coverage"
    if not coverage_file.is_file():
        _run_fixture_coverage()
    report = analyze_crap(
        [FIXTURE_ROOT / "src"],
        threshold=10_000,
        coverage_file=coverage_file,
        search_root=FIXTURE_ROOT,
    )
    assert report.status == "pass"
