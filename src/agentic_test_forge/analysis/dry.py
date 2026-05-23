"""Advisory DRY duplication detection using AST comparison."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.reporting.status import ReportStatus


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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(finding) for finding in self.findings]
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def _iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix == ".py":
            files.append(resolved)
        elif resolved.is_dir():
            files.extend(sorted(resolved.rglob("*.py")))
    return files


def _qualified_name(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str) -> str:
    return f"{prefix}.{node.name}" if prefix else node.name


def _body_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    module = ast.Module(body=list(node.body), type_ignores=[])
    return ast.dump(module, include_attributes=False)


def _collect_functions(
    tree: ast.AST,
    filepath: Path,
    prefix: str = "",
) -> list[tuple[str, str, str]]:
    """Return (qualified_name, filepath, body_fingerprint) for each function."""
    collected: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            name = _qualified_name(node, prefix)
            collected.append((name, str(filepath), _body_fingerprint(node)))
    return collected


def analyze_dry(
    paths: list[str | Path],
    *,
    search_root: Path | None = None,
) -> DryReport:
    """Detect duplicate function bodies under paths (advisory only)."""
    root = (search_root or Path.cwd()).resolve()
    resolved_paths: list[Path] = []
    for path in paths:
        candidate = Path(path)
        if candidate.is_absolute():
            resolved_paths.append(candidate)
        else:
            resolved_paths.append((root / candidate).resolve())

    fingerprints: dict[str, list[tuple[str, str]]] = {}
    for filepath in _iter_python_files(resolved_paths):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for name, file_str, fingerprint in _collect_functions(tree, filepath):
            fingerprints.setdefault(fingerprint, []).append((name, file_str))

    findings: list[DryFinding] = []
    seen_pairs: set[tuple[str, str, str, str]] = set()
    for entries in fingerprints.values():
        if len(entries) < 2:
            continue
        for index, (name, file_str) in enumerate(entries):
            for other_name, other_file in entries[index + 1 :]:
                pair = (name, file_str, other_name, other_file)
                reverse = (other_name, other_file, name, file_str)
                if pair in seen_pairs or reverse in seen_pairs:
                    continue
                seen_pairs.add(pair)
                findings.append(
                    DryFinding(
                        qualified_name=name,
                        filepath=file_str,
                        duplicate_of=other_name,
                        duplicate_filepath=other_file,
                    ),
                )

    findings.sort(key=lambda item: (item.filepath, item.qualified_name))
    if not findings:
        summary = "No duplicate function bodies detected."
    else:
        summary = f"{len(findings)} potential DRY violation(s) detected (advisory)."
    return DryReport(
        tool="dry",
        status=ReportStatus.PASS,
        findings=tuple(findings),
        summary=summary,
    )
