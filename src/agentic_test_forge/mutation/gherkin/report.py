"""Structured reports for Gherkin scenario mutation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast

from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.reporting.threshold import (
    ThresholdFinding,
    ThresholdReportLabels,
    build_threshold_report,
)

_GHERKIN_LABELS = ThresholdReportLabels(
    no_selection_summary="No changed Gherkin scenarios require mutation testing.",
    completed_summary=lambda count: f"Mutation testing completed for {count} scenario(s).",
    violation_summary=lambda violations, threshold, aggregate: (
        f"{violations} scenario(s) below mutation threshold {threshold}% "
        f"(aggregate score {aggregate:.1f}%)."
    ),
    pass_summary=lambda count, threshold, aggregate: (
        f"All {count} mutated scenario(s) meet mutation threshold "
        f"{threshold}% (aggregate score {aggregate:.1f}%)."
    ),
)


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
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


def build_gherkin_mutation_report(
    *,
    threshold: float,
    findings: list[GherkinFinding],
    skipped_unchanged: list[str],
    selected_count: int,
) -> GherkinMutationReport:
    return cast(
        GherkinMutationReport,
        build_threshold_report(
            tool="gherkin_mutation",
            report_cls=cast(Any, GherkinMutationReport),
            threshold=threshold,
            findings=cast(Sequence[ThresholdFinding], findings),
            skipped_unchanged=skipped_unchanged,
            selected_count=selected_count,
            labels=_GHERKIN_LABELS,
        ),
    )
