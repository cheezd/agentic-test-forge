"""CRAP score analysis using radon and coverage.py."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import coverage
from coverage.parser import PythonParser
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


@lru_cache(maxsize=1)
def _exclude_regex() -> str:
    """Combined regex for excluded lines, per the project's coverage config.

    ``Coverage()`` reads .coveragerc/pyproject.toml from the current
    directory, so the user's ``exclude_lines`` settings (and the default
    ``pragma: no cover``) apply here the same way they do in coverage.py's
    own reports.
    """
    exclude_list = coverage.Coverage().config.exclude_list
    return "|".join(f"(?:{pattern})" for pattern in exclude_list)


def _executable_lines(source: str) -> set[int]:
    """Return executable statement lines using coverage.py's own parser."""
    parser = PythonParser(text=source, exclude=_exclude_regex())
    parser.parse_source()
    return set(parser.statements)


def _function_coverage(
    covered_lines: set[int],
    statement_lines: set[int],
    start_line: int,
    end_line: int,
) -> float:
    """Fraction of executable statements in the line range that were covered.

    The denominator is coverage.py's statement set, so docstrings, blank
    lines, and comments do not dilute the score.
    """
    if end_line < start_line:
        return 1.0
    executable = {line for line in statement_lines if start_line <= line <= end_line}
    if not executable:
        return 1.0
    covered = len(executable & covered_lines)
    return covered / len(executable)


def _match_coverage_path(data: coverage.CoverageData, filepath: Path) -> str | None:
    resolved = filepath.resolve()
    measured = data.measured_files()
    if str(resolved) in measured:
        return str(resolved)
    for measured_path in measured:
        if Path(measured_path).resolve() == resolved:
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
    statement_lines: set[int],
    *,
    threshold: float,
    formula: CrapFormula,
) -> CrapFinding:
    end_line = block.endline or block.lineno
    fn_coverage = _function_coverage(line_set, statement_lines, block.lineno, end_line)
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
    statement_lines = _executable_lines(source)
    blocks = _function_blocks_from_source(source)
    return [
        _finding_from_radon_block(
            block,
            filepath,
            line_set,
            statement_lines,
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
