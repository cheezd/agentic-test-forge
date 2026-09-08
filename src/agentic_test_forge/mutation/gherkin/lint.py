"""Static lint for agent-authored Gherkin feature files."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.mutation.gherkin.preflight import (
    ParsedScenario,
    collect_parsed_scenarios,
)
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus

LEAKAGE_PATTERN = re.compile(
    r"\b(?:[a-z_][\w]*\.)+(?:models|views|serializers|services|tasks)\b"
    r"|[A-Z][A-Za-z0-9]+(?:View|Serializer|Service|Manager|Model)\b",
)


@dataclass(frozen=True)
class LintFinding:
    """One Gherkin lint violation."""

    rule: str
    severity: str
    filepath: str
    scenario_name: str
    start_line: int
    message: str


@dataclass(frozen=True)
class GherkinLintReport:
    """Lint report. Error-severity findings fail the gate."""

    tool: str
    status: ReportStatus
    findings: tuple[LintFinding, ...]
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


def analyze_gherkin_lint(
    paths: Sequence[str | Path],
    *,
    search_root: Path | None = None,
    require_tags: bool = False,
    flag_implementation_leakage: bool = False,
) -> GherkinLintReport:
    """Lint feature files under ``paths``."""
    scenarios = collect_parsed_scenarios(paths, search_root=search_root)
    findings: list[LintFinding] = []
    findings.extend(_duplicate_name_findings(scenarios))
    for parsed in scenarios:
        findings.extend(_scenario_findings(parsed, require_tags=require_tags))
        if flag_implementation_leakage:
            findings.extend(_leakage_findings(parsed))

    ordered = tuple(sorted(findings, key=lambda item: (item.filepath, item.start_line, item.rule)))
    errors = [item for item in ordered if item.severity == "error"]
    status = ReportStatus.FAIL if errors else ReportStatus.PASS
    if not scenarios:
        summary = "No Gherkin scenarios found."
    elif errors:
        summary = f"{len(errors)} Gherkin lint error(s) in {len(scenarios)} scenario(s)."
    else:
        warning_count = len(ordered) - len(errors)
        summary = (
            f"{len(scenarios)} scenario(s) passed Gherkin lint"
            + (f" ({warning_count} warning(s))." if warning_count else ".")
        )
    return GherkinLintReport(
        tool="gherkin-lint",
        status=status,
        findings=ordered,
        summary=summary,
    )


def _duplicate_name_findings(scenarios: Sequence[ParsedScenario]) -> list[LintFinding]:
    names_by_file: dict[str, list[str]] = {}
    for parsed in scenarios:
        names_by_file.setdefault(parsed.scenario.filepath, []).append(parsed.scenario.name)

    findings: list[LintFinding] = []
    seen: set[tuple[str, str]] = set()
    for parsed in scenarios:
        filepath = parsed.scenario.filepath
        name = parsed.scenario.name
        key = (filepath, name)
        if Counter(names_by_file[filepath])[name] < 2 or key in seen:
            continue
        seen.add(key)
        findings.append(
            LintFinding(
                rule="duplicate_name",
                severity="error",
                filepath=filepath,
                scenario_name=name,
                start_line=parsed.scenario.start_line,
                message=f"Duplicate scenario name '{name}' in {filepath}.",
            ),
        )
    return findings


def _scenario_findings(parsed: ParsedScenario, *, require_tags: bool) -> list[LintFinding]:
    findings: list[LintFinding] = []
    scenario = parsed.scenario
    if parsed.has_examples_keyword and scenario.examples is None:
        findings.append(
            LintFinding(
                rule="empty_examples",
                severity="error",
                filepath=scenario.filepath,
                scenario_name=scenario.name,
                start_line=scenario.start_line,
                message="Examples table has no data rows; mutation will skip this scenario.",
            ),
        )
    elif not parsed.has_examples:
        findings.append(
            LintFinding(
                rule="no_examples",
                severity="error",
                filepath=scenario.filepath,
                scenario_name=scenario.name,
                start_line=scenario.start_line,
                message="Scenario has no Examples table; mutation will skip it.",
            ),
        )
    if require_tags and not parsed.tags:
        findings.append(
            LintFinding(
                rule="missing_tags",
                severity="error",
                filepath=scenario.filepath,
                scenario_name=scenario.name,
                start_line=scenario.start_line,
                message="Scenario has no tags (--require-tags).",
            ),
        )
    return findings


def _leakage_findings(parsed: ParsedScenario) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for step in parsed.steps:
        if LEAKAGE_PATTERN.search(step) is None:
            continue
        findings.append(
            LintFinding(
                rule="implementation_leakage",
                severity="warning",
                filepath=parsed.scenario.filepath,
                scenario_name=parsed.scenario.name,
                start_line=parsed.scenario.start_line,
                message=f"Step looks implementation-specific: {step}",
            ),
        )
    return findings
