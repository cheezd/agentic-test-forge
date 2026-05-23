"""Tests for CRAP analysis."""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from pathlib import Path

import coverage
import pytest
from radon.complexity import cc_visit
from radon.visitors import Function

from agentic_test_forge.analysis.crap import (
    CoverageDataMissingError,
    _coverage_lines_for_file,
    _finding_from_radon_block,
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


def _function_block(source: str) -> Function:
    block = next(item for item in cc_visit(source) if isinstance(item, Function))
    return block


def test_coverage_lines_for_file_returns_empty_when_unmatched(tmp_path: Path) -> None:
    module = tmp_path / "mod.py"
    module.write_text("def foo():\n    return 1\n", encoding="utf-8")

    cov = coverage.Coverage(data_file=str(tmp_path / ".coverage"))
    cov.start()
    cov.stop()
    cov.save()

    assert _coverage_lines_for_file(cov.get_data(), module) == set()


def test_coverage_lines_for_file_resolves_measured_lines(tmp_path: Path) -> None:
    module = tmp_path / "mod.py"
    module.write_text("def foo():\n    return 1\n", encoding="utf-8")

    cov = coverage.Coverage(
        data_file=str(tmp_path / ".coverage"),
        source=[str(tmp_path)],
    )
    cov.start()
    runpy.run_path(str(module))
    cov.stop()
    cov.save()

    lines = _coverage_lines_for_file(cov.get_data(), module)
    assert lines == {1}


def test_finding_from_radon_block_uses_coverage_and_threshold() -> None:
    block = _function_block("def foo():\n    return 1\n")
    finding = _finding_from_radon_block(
        block,
        Path("sample.py"),
        {1, 2},
        threshold=6,
        formula="standard",
    )

    assert finding.qualified_name == "foo"
    assert finding.filepath == "sample.py"
    assert finding.coverage == 1.0
    assert finding.crap_score == float(block.complexity)
    assert finding.above_threshold is False


def test_finding_from_radon_block_marks_uncovered_above_threshold() -> None:
    block = _function_block(
        "def complex_uncovered(value):\n"
        "    if value > 0:\n"
        "        if value > 10:\n"
        "            return value * 2\n"
        "        return value\n"
        "    return 0\n",
    )
    finding = _finding_from_radon_block(
        block,
        Path("uncovered.py"),
        set(),
        threshold=6,
        formula="standard",
    )

    assert finding.coverage == 0.0
    assert finding.crap_score > 6
    assert finding.above_threshold is True


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
