"""CRAP score analysis using radon and coverage.py."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import coverage
from radon.complexity import cc_visit
from radon.visitors import Function

from agentic_test_forge.config.models import CrapFormula
from agentic_test_forge.errors import ForgeToolError
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.scope import iter_files_by_suffix, normalize_paths, resolve_search_root


class CoverageDataMissingError(ForgeToolError, FileNotFoundError):
    """Raised when coverage data is required but not found."""


@dataclass(frozen=True)
class CrapFinding:
    """CRAP result for a single function."""

    qualified_name: str
    filepath: str
    complexity: float
    coverage: float
    crap_score: float
    above_threshold: bool


@dataclass(frozen=True)
class CrapReport:
    """Aggregate CRAP analysis report."""

    tool: str
    status: ReportStatus
    threshold: float
    formula: CrapFormula
    findings: tuple[CrapFinding, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


def compute_crap_score(
    complexity: float,
    coverage_fraction: float,
    formula: CrapFormula = "standard",
) -> float:
    """Compute CRAP score for one function."""
    cov = max(0.0, min(1.0, coverage_fraction))
    if formula == "simplified":
        return complexity + (1.0 - cov) ** 3
    return complexity**2 * (1.0 - cov) ** 3 + complexity


def _resolve_coverage_path(coverage_file: Path, search_root: Path) -> Path:
    candidate = coverage_file if coverage_file.is_absolute() else search_root / coverage_file
    resolved = candidate.resolve()
    if resolved.is_file():
        return resolved
    raise CoverageDataMissingError(
        f"Coverage data not found at '{coverage_file}'. "
        "Run tests with coverage first (e.g. pytest --cov=src).",
    )


def _qualified_name(function: Function) -> str:
    name = str(function.name)
    if function.classname:
        return f"{function.classname}.{name}"
    return name


def _function_coverage(
    covered_lines: set[int],
    start_line: int,
    end_line: int,
) -> float:
    if end_line < start_line:
        return 1.0
    executable = range(start_line, end_line + 1)
    total = len(executable)
    if total == 0:
        return 1.0
    covered = sum(1 for line in executable if line in covered_lines)
    return covered / total


def _match_coverage_path(data: coverage.CoverageData, filepath: Path) -> str | None:
    resolved = str(filepath.resolve())
    measured = data.measured_files()
    if resolved in measured:
        return resolved
    for measured_path in measured:
        if Path(measured_path).resolve() == filepath.resolve():
            return measured_path
        if Path(measured_path).name == filepath.name:
            return measured_path
    return None


def _coverage_lines_for_file(data: coverage.CoverageData, filepath: Path) -> set[int]:
    covered_key = _match_coverage_path(data, filepath)
    if covered_key is None:
        return set()
    raw_lines = data.lines(covered_key) or []
    return set(raw_lines)


def _function_blocks_from_source(source: str) -> list[Function]:
    return [block for block in cc_visit(source) if isinstance(block, Function)]


def _finding_from_radon_block(
    block: Function,
    filepath: Path,
    line_set: set[int],
    *,
    threshold: float,
    formula: CrapFormula,
) -> CrapFinding:
    end_line = block.endline or block.lineno
    fn_coverage = _function_coverage(line_set, block.lineno, end_line)
    score = compute_crap_score(block.complexity, fn_coverage, formula)
    return CrapFinding(
        qualified_name=_qualified_name(block),
        filepath=str(filepath),
        complexity=float(block.complexity),
        coverage=fn_coverage,
        crap_score=score,
        above_threshold=score > threshold,
    )


def _findings_for_file(
    filepath: Path,
    data: coverage.CoverageData,
    *,
    threshold: float,
    formula: CrapFormula,
) -> list[CrapFinding]:
    line_set = _coverage_lines_for_file(data, filepath)
    source = filepath.read_text(encoding="utf-8")
    blocks = _function_blocks_from_source(source)
    return [
        _finding_from_radon_block(
            block,
            filepath,
            line_set,
            threshold=threshold,
            formula=formula,
        )
        for block in blocks
    ]


def _collect_crap_findings(
    python_files: list[Path],
    data: coverage.CoverageData,
    *,
    threshold: float,
    formula: CrapFormula,
) -> list[CrapFinding]:
    findings: list[CrapFinding] = []
    for filepath in python_files:
        findings.extend(
            _findings_for_file(
                filepath,
                data,
                threshold=threshold,
                formula=formula,
            ),
        )
    findings.sort(key=lambda item: item.crap_score, reverse=True)
    return findings


def _build_crap_report(
    findings: list[CrapFinding],
    *,
    threshold: float,
    formula: CrapFormula,
) -> CrapReport:
    violations = [finding for finding in findings if finding.above_threshold]
    status = ReportStatus.FAIL if violations else ReportStatus.PASS
    if not findings:
        summary = "No functions found to analyze."
    elif violations:
        summary = f"{len(violations)} function(s) exceed CRAP threshold {threshold}."
    else:
        summary = f"All {len(findings)} function(s) are at or below CRAP threshold {threshold}."
    return CrapReport(
        tool="crap",
        status=status,
        threshold=threshold,
        formula=formula,
        findings=tuple(findings),
        summary=summary,
    )


def analyze_crap(
    paths: list[str | Path],
    *,
    threshold: float,
    formula: CrapFormula = "standard",
    coverage_file: str | Path = ".coverage",
    search_root: Path | None = None,
) -> CrapReport:
    """Analyze Python functions under paths and return a CRAP report."""
    root = resolve_search_root(search_root)
    resolved_paths = normalize_paths([str(path) for path in paths], root)
    python_files = iter_files_by_suffix(resolved_paths, ".py")
    coverage_path = _resolve_coverage_path(Path(coverage_file), root)

    cov = coverage.Coverage(data_file=str(coverage_path))
    cov.load()
    findings = _collect_crap_findings(
        python_files,
        cov.get_data(),
        threshold=threshold,
        formula=formula,
    )
    return _build_crap_report(findings, threshold=threshold, formula=formula)
