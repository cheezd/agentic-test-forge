"""Advisory DRY duplication detection using AST comparison."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.scope import iter_files_by_suffix, normalize_paths, resolve_search_root


@dataclass(frozen=True)
class DryFinding:
    """One duplicated function body detected in the codebase."""

    qualified_name: str
    filepath: str
    duplicate_of: str
    duplicate_filepath: str


@dataclass(frozen=True)
class DryReport:
    """Advisory DRY report (does not fail quality gates by default)."""

    tool: str
    status: ReportStatus
    findings: tuple[DryFinding, ...]
    summary: str
    advisory: bool = True
    skipped_parse_files: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


FunctionRecord = tuple[str, str, str]
FingerprintEntry = tuple[str, str]


@dataclass(frozen=True)
class DuplicatePair:
    """Two functions sharing the same body fingerprint."""

    name: str
    filepath: str
    other_name: str
    other_filepath: str

    @property
    def reverse(self) -> DuplicatePair:
        return DuplicatePair(
            name=self.other_name,
            filepath=self.other_filepath,
            other_name=self.name,
            other_filepath=self.filepath,
        )

    def normalized(self) -> DuplicatePair:
        left = (self.name, self.filepath)
        right = (self.other_name, self.other_filepath)
        if left <= right:
            return self
        return self.reverse


def _qualified_name(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str) -> str:
    return f"{prefix}.{node.name}" if prefix else node.name


def _body_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    module = ast.Module(body=list(node.body), type_ignores=[])
    return ast.dump(module, include_attributes=False)


class _FunctionCollector(ast.NodeVisitor):
    """Collect functions with class-aware qualified names."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.functions: list[FunctionRecord] = []
        self._prefix_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._prefix_stack.append(node.name)
        self.generic_visit(node)
        self._prefix_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not node.body:
            return
        prefix = ".".join(self._prefix_stack)
        name = _qualified_name(node, prefix)
        self.functions.append((name, str(self.filepath), _body_fingerprint(node)))
        self.generic_visit(node)


def _collect_functions(tree: ast.AST, filepath: Path) -> list[FunctionRecord]:
    collector = _FunctionCollector(filepath)
    collector.visit(tree)
    return collector.functions


def _parse_python_file(filepath: Path) -> ast.AST | None:
    try:
        return ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _register_file_fingerprints(
    fingerprints: dict[str, list[FingerprintEntry]],
    tree: ast.AST,
    filepath: Path,
) -> None:
    for name, file_str, fingerprint in _collect_functions(tree, filepath):
        fingerprints.setdefault(fingerprint, []).append((name, file_str))


def _index_function_fingerprints(
    python_files: list[Path],
) -> tuple[dict[str, list[FingerprintEntry]], tuple[str, ...]]:
    fingerprints: dict[str, list[FingerprintEntry]] = {}
    skipped: list[str] = []
    for filepath in python_files:
        tree = _parse_python_file(filepath)
        if tree is None:
            skipped.append(str(filepath))
            continue
        _register_file_fingerprints(fingerprints, tree, filepath)
    return fingerprints, tuple(sorted(skipped))


def _pairs_from_fingerprint_entries(
    entries: list[FingerprintEntry],
) -> list[DuplicatePair]:
    pairs: list[DuplicatePair] = []
    for index, (name, file_str) in enumerate(entries):
        for other_name, other_file in entries[index + 1 :]:
            pairs.append(
                DuplicatePair(
                    name=name,
                    filepath=file_str,
                    other_name=other_name,
                    other_filepath=other_file,
                ),
            )
    return pairs


def _finding_from_duplicate_pair(pair: DuplicatePair) -> DryFinding:
    return DryFinding(
        qualified_name=pair.name,
        filepath=pair.filepath,
        duplicate_of=pair.other_name,
        duplicate_filepath=pair.other_filepath,
    )


def _find_duplicate_pairs(
    fingerprints: dict[str, list[FingerprintEntry]],
) -> list[DryFinding]:
    findings: list[DryFinding] = []
    seen_pairs: set[DuplicatePair] = set()
    for entries in fingerprints.values():
        if len(entries) < 2:
            continue
        for pair in _pairs_from_fingerprint_entries(entries):
            canonical = pair.normalized()
            if canonical in seen_pairs:
                continue
            seen_pairs.add(canonical)
            findings.append(_finding_from_duplicate_pair(pair))
    findings.sort(key=lambda item: (item.filepath, item.qualified_name))
    return findings


def _build_dry_report(
    findings: list[DryFinding],
    *,
    skipped_parse_files: tuple[str, ...],
) -> DryReport:
    if not findings:
        summary = "No duplicate function bodies detected."
    else:
        summary = f"{len(findings)} potential DRY violation(s) detected (advisory)."
    return DryReport(
        tool="dry",
        status=ReportStatus.PASS,
        findings=tuple(findings),
        summary=summary,
        skipped_parse_files=skipped_parse_files,
    )


def analyze_dry(
    paths: list[str | Path],
    *,
    search_root: Path | None = None,
) -> DryReport:
    """Detect duplicate function bodies under paths (advisory only)."""
    root = resolve_search_root(search_root)
    resolved_paths = normalize_paths([str(path) for path in paths], root)
    python_files = iter_files_by_suffix(resolved_paths, ".py")
    fingerprints, skipped = _index_function_fingerprints(python_files)
    findings = _find_duplicate_pairs(fingerprints)
    return _build_dry_report(findings, skipped_parse_files=skipped)
