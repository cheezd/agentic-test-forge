"""Undefined-step preflight against behave / pytest-bdd decorator patterns."""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.mutation.gherkin.preflight import collect_parsed_scenarios
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.scope import iter_files_by_suffix, normalize_paths, resolve_search_root

STEP_DECORATOR_NAMES = frozenset({"given", "when", "then", "step"})


@dataclass(frozen=True)
class UndefinedStepFinding:
    """A feature step with no matching step-definition pattern."""

    filepath: str
    scenario_name: str
    start_line: int
    step: str
    message: str


@dataclass(frozen=True)
class GherkinValidateStepsReport:
    """Undefined-step report. Findings fail the gate."""

    tool: str
    status: ReportStatus
    findings: tuple[UndefinedStepFinding, ...]
    summary: str
    step_file_count: int
    pattern_count: int

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


def analyze_gherkin_validate_steps(
    paths: Sequence[str | Path],
    *,
    search_root: Path | None = None,
    steps_paths: Sequence[str | Path] | None = None,
) -> GherkinValidateStepsReport:
    """Report feature steps that do not match registered decorator patterns."""
    root = resolve_search_root(search_root)
    scenarios = collect_parsed_scenarios(paths, search_root=root)
    step_files = _collect_step_files(paths, steps_paths=steps_paths, search_root=root)
    patterns = _load_step_patterns(step_files)
    findings: list[UndefinedStepFinding] = []

    for parsed in scenarios:
        for step in parsed.steps:
            if _step_matches(step, patterns):
                continue
            findings.append(
                UndefinedStepFinding(
                    filepath=parsed.scenario.filepath,
                    scenario_name=parsed.scenario.name,
                    start_line=parsed.scenario.start_line,
                    step=step,
                    message=f"Undefined step: {step}",
                ),
            )

    if scenarios and not step_files:
        findings.insert(
            0,
            UndefinedStepFinding(
                filepath="",
                scenario_name="",
                start_line=0,
                step="",
                message="No step definition files found; pass --steps-path or add features/steps/.",
            ),
        )

    ordered = tuple(findings)
    status = ReportStatus.FAIL if ordered else ReportStatus.PASS
    if not scenarios:
        summary = "No Gherkin scenarios found."
    elif ordered:
        summary = f"{len(ordered)} undefined step(s) across {len(scenarios)} scenario(s)."
    else:
        summary = (
            f"All steps bound ({len(scenarios)} scenario(s), "
            f"{len(step_files)} step file(s), {len(patterns)} pattern(s))."
        )
    return GherkinValidateStepsReport(
        tool="gherkin-validate-steps",
        status=status,
        findings=ordered,
        summary=summary,
        step_file_count=len(step_files),
        pattern_count=len(patterns),
    )


def _collect_step_files(
    feature_paths: Sequence[str | Path],
    *,
    steps_paths: Sequence[str | Path] | None,
    search_root: Path,
) -> list[Path]:
    if steps_paths:
        roots = normalize_paths([str(p) for p in steps_paths], search_root)
        return iter_files_by_suffix(roots, ".py")

    roots: list[Path] = []
    for raw in normalize_paths([str(p) for p in feature_paths], search_root):
        if raw.is_file():
            raw = raw.parent
        steps_dir = raw / "steps"
        if steps_dir.is_dir():
            roots.append(steps_dir)
    return iter_files_by_suffix(roots, ".py")


def _load_step_patterns(step_files: Sequence[Path]) -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for path in step_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                extracted = _decorator_pattern(decorator)
                if extracted is None:
                    continue
                kind, value = extracted
                if kind == "regex":
                    patterns.append(re.compile(f"^{value}$"))
                else:
                    patterns.append(_template_to_regex(value))
    return patterns


def _decorator_pattern(decorator: ast.AST) -> tuple[str, str] | None:
    if not isinstance(decorator, ast.Call):
        return None
    name = _call_name(decorator.func)
    if name not in STEP_DECORATOR_NAMES:
        return None
    if not decorator.args:
        return None
    first = decorator.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return ("parse", first.value)
    if isinstance(first, ast.Call) and first.args:
        inner = first.args[0]
        if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
            callee = _call_name(first.func)
            if callee in {"re", "compile"}:
                return ("regex", inner.value)
            return ("parse", inner.value)
    return None


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id.lower()
    if isinstance(func, ast.Attribute):
        return func.attr.lower()
    return ""


def _template_to_regex(template: str) -> re.Pattern[str]:
    pieces = re.split(r"(\{[^}]+\}|<[^>]+>)", template)
    escaped: list[str] = []
    for piece in pieces:
        if piece.startswith("{") or piece.startswith("<"):
            token = piece[1:-1]
            if token == "int":
                escaped.append(r"-?\d+")
            elif token == "float":
                escaped.append(r"-?\d+(?:\.\d+)?")
            elif token == "word":
                escaped.append(r"\S+")
            else:
                escaped.append(r".+")
        else:
            escaped.append(re.escape(piece))
    return re.compile("^" + "".join(escaped) + "$")


def _step_matches(step: str, patterns: Sequence[re.Pattern[str]]) -> bool:
    return any(pattern.fullmatch(step) is not None for pattern in patterns)
