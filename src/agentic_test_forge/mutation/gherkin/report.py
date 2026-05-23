"""Structured reports for Gherkin scenario mutation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from agentic_test_forge.mutation.code.report import compute_mutation_score
from agentic_test_forge.reporting.status import ReportStatus


@dataclass(frozen=True)
class GherkinFinding:
    """Mutation score for one scenario."""

    scenario_id: str
    score: float
    killed: int
    total: int
    above_threshold: bool


@dataclass(frozen=True)
class GherkinMutationReport:
    """Aggregate Gherkin mutation testing report."""

    tool: str
    status: ReportStatus
    threshold: float
    findings: tuple[GherkinFinding, ...]
    summary: str
    skipped_unchanged: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(finding) for finding in self.findings]
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def build_gherkin_mutation_report(
    *,
    threshold: float,
    findings: list[GherkinFinding],
    skipped_unchanged: list[str],
    selected_count: int,
) -> GherkinMutationReport:
    if selected_count == 0:
        summary = "No changed Gherkin scenarios require mutation testing."
        return GherkinMutationReport(
            tool="gherkin_mutation",
            status=ReportStatus.PASS,
            threshold=threshold,
            findings=tuple(findings),
            summary=summary,
            skipped_unchanged=tuple(skipped_unchanged),
        )

    if not findings:
        summary = f"Mutation testing completed for {selected_count} scenario(s)."
        return GherkinMutationReport(
            tool="gherkin_mutation",
            status=ReportStatus.PASS,
            threshold=threshold,
            findings=(),
            summary=summary,
            skipped_unchanged=tuple(skipped_unchanged),
        )

    violations = [finding for finding in findings if finding.above_threshold]
    aggregate_killed = sum(finding.killed for finding in findings)
    aggregate_total = sum(finding.total for finding in findings)
    aggregate_score = compute_mutation_score(aggregate_killed, aggregate_total)
    status = (
        ReportStatus.FAIL
        if violations or aggregate_score < threshold
        else ReportStatus.PASS
    )

    if violations:
        summary = (
            f"{len(violations)} scenario(s) below mutation threshold {threshold}% "
            f"(aggregate score {aggregate_score:.1f}%)."
        )
    else:
        summary = (
            f"All {len(findings)} mutated scenario(s) meet mutation threshold "
            f"{threshold}% (aggregate score {aggregate_score:.1f}%)."
        )

    return GherkinMutationReport(
        tool="gherkin_mutation",
        status=status,
        threshold=threshold,
        findings=tuple(findings),
        summary=summary,
        skipped_unchanged=tuple(skipped_unchanged),
    )
