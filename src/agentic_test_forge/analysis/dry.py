"""Advisory DRY duplication detection using normalized AST comparison."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.scope import iter_files_by_suffix, normalize_paths, resolve_search_root

DEFAULT_DRY_THRESHOLD = 0.82
DEFAULT_DRY_MIN_LINES = 4
DEFAULT_DRY_MIN_NODES = 20


@dataclass(frozen=True)
class DryFinding:
    """One structurally similar function pair detected in the codebase."""

    qualified_name: str
    filepath: str
    duplicate_of: str
    duplicate_filepath: str
    similarity_score: float
    start_line: int
    end_line: int
    node_count: int


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


@dataclass(frozen=True)
class FunctionUnit:
    """One analyzable function body with normalized structural fingerprints."""

    qualified_name: str
    filepath: str
    fingerprints: frozenset[str]
    start_line: int
    end_line: int
    node_count: int
    source_lines: int


@dataclass(frozen=True)
class SimilarPair:
    """Two functions exceeding the similarity threshold."""

    name: str
    filepath: str
    other_name: str
    other_filepath: str

    @property
    def reverse(self) -> SimilarPair:
        return SimilarPair(
            name=self.other_name,
            filepath=self.other_filepath,
            other_name=self.name,
            other_filepath=self.filepath,
        )

    def normalized(self) -> SimilarPair:
        left = (self.name, self.filepath)
        right = (self.other_name, self.other_filepath)
        if left <= right:
            return self
        return self.reverse


def _round_score(score: float) -> float:
    return round(score, 2)


def _jaccard(left: set[str] | frozenset[str], right: set[str] | frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = set(left) | set(right)
    if not union:
        return 1.0
    return len(set(left) & set(right)) / len(union)


def _qualified_name(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str) -> str:
    return f"{prefix}.{node.name}" if prefix else node.name


def _body_module(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Module:
    return ast.Module(body=list(node.body), type_ignores=[])


def _constant_type_tag(value: object) -> str:
    if value is None:
        return "_none_"
    if isinstance(value, bool):
        return "_bool_"
    if isinstance(value, int):
        return "_int_"
    if isinstance(value, float):
        return "_float_"
    if isinstance(value, str):
        return "_str_"
    if isinstance(value, bytes):
        return "_bytes_"
    return "_const_"


class _AstNormalizer(ast.NodeTransformer):
    """Replace incidental identifiers and literals with generic structural markers."""

    def visit_Name(self, node: ast.Name) -> ast.Name:
        return ast.copy_location(ast.Name(id="_", ctx=node.ctx), node)

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        return ast.copy_location(ast.Constant(value=_constant_type_tag(node.value)), node)

    def visit_Attribute(self, node: ast.Attribute) -> ast.Attribute:
        return ast.copy_location(
            ast.Attribute(value=self.visit(node.value), attr="_", ctx=node.ctx),
            node,
        )

    def visit_keyword(self, node: ast.keyword) -> ast.keyword:
        return ast.copy_location(
            ast.keyword(arg="_" if node.arg is not None else None, value=self.visit(node.value)),
            node,
        )

    def visit_MatchAs(self, node: ast.MatchAs) -> ast.MatchAs:
        pattern = self.visit(node.pattern) if node.pattern is not None else None
        return ast.copy_location(ast.MatchAs(name="_", pattern=pattern), node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        return ast.copy_location(
            ast.ExceptHandler(
                type=self.visit(node.type) if node.type is not None else None,
                name="_" if node.name is not None else None,
                body=[self.visit(statement) for statement in node.body],
            ),
            node,
        )


class _FingerprintCollector(ast.NodeVisitor):
    """Collect structural fingerprint strings from a normalized syntax tree."""

    def __init__(self) -> None:
        self.fingerprints: set[str] = set()

    def generic_visit(self, node: ast.AST) -> None:
        self.fingerprints.add(ast.dump(node, include_attributes=False))
        super().generic_visit(node)


class _NodeCounter(ast.NodeVisitor):
    """Count syntax nodes in a normalized tree."""

    def __init__(self) -> None:
        self.count = 0

    def generic_visit(self, node: ast.AST) -> None:
        self.count += 1
        super().generic_visit(node)


def _normalize_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.Module:
    """Return normalized module wrapping a function body."""
    normalized = _AstNormalizer().visit(_body_module(node))
    if not isinstance(normalized, ast.Module):
        msg = "expected normalized function body to remain a Module"
        raise TypeError(msg)
    return normalized


def _collect_fingerprints(normalized_body: ast.Module) -> set[str]:
    """Collect structural fingerprints for a normalized function body module."""
    collector = _FingerprintCollector()
    collector.visit(normalized_body)
    return collector.fingerprints


def _count_normalized_nodes(normalized_body: ast.Module) -> int:
    counter = _NodeCounter()
    counter.visit(normalized_body)
    return counter.count


def _function_line_range(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int]:
    start = node.lineno
    end = node.end_lineno if node.end_lineno is not None else start
    return start, end


def _source_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    start, end = _function_line_range(node)
    return end - start + 1


def _function_unit(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    qualified_name: str,
    filepath: Path,
) -> FunctionUnit:
    normalized = _normalize_body(node)
    start_line, end_line = _function_line_range(node)
    return FunctionUnit(
        qualified_name=qualified_name,
        filepath=str(filepath),
        fingerprints=frozenset(_collect_fingerprints(normalized)),
        start_line=start_line,
        end_line=end_line,
        node_count=_count_normalized_nodes(normalized),
        source_lines=_source_line_count(node),
    )


class _FunctionCollector(ast.NodeVisitor):
    """Collect function units with class-aware qualified names."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.units: list[FunctionUnit] = []
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
        self.units.append(_function_unit(node, qualified_name=name, filepath=self.filepath))
        self.generic_visit(node)


def _collect_function_units(tree: ast.AST, filepath: Path) -> list[FunctionUnit]:
    collector = _FunctionCollector(filepath)
    collector.visit(tree)
    return collector.units


def _parse_python_file(filepath: Path) -> ast.AST | None:
    try:
        return ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _index_function_units(python_files: list[Path]) -> tuple[list[FunctionUnit], tuple[str, ...]]:
    units: list[FunctionUnit] = []
    skipped: list[str] = []
    for filepath in python_files:
        tree = _parse_python_file(filepath)
        if tree is None:
            skipped.append(str(filepath))
            continue
        units.extend(_collect_function_units(tree, filepath))
    return units, tuple(sorted(skipped))


def _finding_from_similar_pair(
    pair: SimilarPair,
    *,
    score: float,
    lookup: dict[tuple[str, str], FunctionUnit],
) -> DryFinding:
    primary = lookup[(pair.name, pair.filepath)]
    return DryFinding(
        qualified_name=pair.name,
        filepath=pair.filepath,
        duplicate_of=pair.other_name,
        duplicate_filepath=pair.other_filepath,
        similarity_score=_round_score(score),
        start_line=primary.start_line,
        end_line=primary.end_line,
        node_count=primary.node_count,
    )


def _unit_lookup(units: list[FunctionUnit]) -> dict[tuple[str, str], FunctionUnit]:
    return {(unit.qualified_name, unit.filepath): unit for unit in units}


def _find_similar_pairs(
    units: list[FunctionUnit],
    *,
    threshold: float,
    min_lines: int,
    min_nodes: int,
) -> list[DryFinding]:
    findings: list[DryFinding] = []
    seen_pairs: set[SimilarPair] = set()
    lookup = _unit_lookup(units)
    eligible = [
        unit
        for unit in units
        if unit.source_lines >= min_lines and unit.node_count >= min_nodes
    ]
    for index, left in enumerate(eligible):
        for right in eligible[index + 1 :]:
            score = _jaccard(left.fingerprints, right.fingerprints)
            if score < threshold:
                continue
            pair = SimilarPair(
                name=left.qualified_name,
                filepath=left.filepath,
                other_name=right.qualified_name,
                other_filepath=right.filepath,
            ).normalized()
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            findings.append(
                _finding_from_similar_pair(pair, score=score, lookup=lookup),
            )
    findings.sort(
        key=lambda item: (-item.similarity_score, item.filepath, item.qualified_name),
    )
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
    threshold: float = DEFAULT_DRY_THRESHOLD,
    min_lines: int = DEFAULT_DRY_MIN_LINES,
    min_nodes: int = DEFAULT_DRY_MIN_NODES,
) -> DryReport:
    """Detect structurally similar function bodies under paths (advisory only)."""
    root = resolve_search_root(search_root)
    resolved_paths = normalize_paths([str(path) for path in paths], root)
    python_files = iter_files_by_suffix(resolved_paths, ".py")
    units, skipped = _index_function_units(python_files)
    findings = _find_similar_pairs(
        units,
        threshold=threshold,
        min_lines=min_lines,
        min_nodes=min_nodes,
    )
    return _build_dry_report(findings, skipped_parse_files=skipped)
