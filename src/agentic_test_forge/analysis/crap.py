"""CRAP score analysis using radon and coverage.py."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import coverage
from radon.complexity import cc_visit
from radon.visitors import Function

from agentic_test_forge.config.models import CrapFormula

ReportStatus = Literal["pass", "fail"]


class CoverageDataMissingError(FileNotFoundError):
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
        payload = asdict(self)
        payload["findings"] = [asdict(f) for f in self.findings]
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


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


def _iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix == ".py":
            files.append(resolved)
        elif resolved.is_dir():
            files.extend(sorted(resolved.rglob("*.py")))
    return files


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


def analyze_crap(
    paths: list[str | Path],
    *,
    threshold: float,
    formula: CrapFormula = "standard",
    coverage_file: str | Path = ".coverage",
    search_root: Path | None = None,
) -> CrapReport:
    """Analyze Python functions under paths and return a CRAP report."""
    root = (search_root or Path.cwd()).resolve()
    resolved_paths: list[Path] = []
    for path in paths:
        candidate = Path(path)
        if candidate.is_absolute():
            resolved_paths.append(candidate)
        else:
            resolved_paths.append((root / candidate).resolve())
    python_files = _iter_python_files(resolved_paths)
    coverage_path = _resolve_coverage_path(Path(coverage_file), root)

    cov = coverage.Coverage(data_file=str(coverage_path))
    cov.load()
    data = cov.get_data()

    findings: list[CrapFinding] = []
    for filepath in python_files:
        source = filepath.read_text(encoding="utf-8")
        covered_key = _match_coverage_path(data, filepath)
        line_set: set[int] = set()
        if covered_key is not None:
            raw_lines = data.lines(covered_key) or []
            line_set = set(raw_lines)

        for block in cc_visit(source):
            if not isinstance(block, Function):
                continue
            end_line = block.endline or block.lineno
            fn_coverage = _function_coverage(line_set, block.lineno, end_line)
            score = compute_crap_score(block.complexity, fn_coverage, formula)
            findings.append(
                CrapFinding(
                    qualified_name=_qualified_name(block),
                    filepath=str(filepath),
                    complexity=float(block.complexity),
                    coverage=fn_coverage,
                    crap_score=score,
                    above_threshold=score > threshold,
                ),
            )

    findings.sort(key=lambda item: item.crap_score, reverse=True)
    violations = [finding for finding in findings if finding.above_threshold]
    status: ReportStatus = "fail" if violations else "pass"
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
