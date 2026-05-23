"""Shared threshold-gated mutation report builder."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from agentic_test_forge.reporting.status import ReportStatus


def compute_mutation_score(killed: int, total: int) -> float:
    if total == 0:
        return 100.0
    return (killed / total) * 100.0


class ThresholdFinding(Protocol):
    """Finding with aggregate score inputs and threshold flag."""

    above_threshold: bool
    killed: int
    total: int


class ThresholdReport(Protocol):
    """Report envelope produced by ``build_threshold_report``."""

    tool: str
    status: ReportStatus
    threshold: float
    summary: str
    skipped_unchanged: tuple[str, ...]


@dataclass(frozen=True)
class ThresholdReportLabels:
    """Summary templates for threshold-gated mutation reports."""

    no_selection_summary: str
    completed_summary: Callable[[int], str]
    violation_summary: Callable[[int, float, float], str]
    pass_summary: Callable[[int, float, float], str]


def build_threshold_report(
    *,
    tool: str,
    report_cls: Callable[..., ThresholdReport],
    threshold: float,
    findings: Sequence[ThresholdFinding],
    skipped_unchanged: Sequence[str],
    selected_count: int,
    labels: ThresholdReportLabels,
) -> ThresholdReport:
    """Build a pass/fail report from threshold-scored findings."""
    skipped = tuple(skipped_unchanged)

    if selected_count == 0:
        return report_cls(
            tool=tool,
            status=ReportStatus.PASS,
            threshold=threshold,
            findings=tuple(findings),
            summary=labels.no_selection_summary,
            skipped_unchanged=skipped,
        )

    if not findings:
        return report_cls(
            tool=tool,
            status=ReportStatus.PASS,
            threshold=threshold,
            findings=(),
            summary=labels.completed_summary(selected_count),
            skipped_unchanged=skipped,
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
        summary = labels.violation_summary(
            len(violations),
            threshold,
            aggregate_score,
        )
    else:
        summary = labels.pass_summary(len(findings), threshold, aggregate_score)

    return report_cls(
        tool=tool,
        status=status,
        threshold=threshold,
        findings=tuple(findings),
        summary=summary,
        skipped_unchanged=skipped,
    )
