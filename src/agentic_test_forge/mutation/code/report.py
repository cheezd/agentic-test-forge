"""Parse mutmut output into forge mutation reports."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from agentic_test_forge.mutation.code.exit_codes import classify_mutmut_exit_code
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus
from agentic_test_forge.reporting.threshold import (
    ThresholdFinding,
    ThresholdReportLabels,
    build_threshold_report,
    compute_mutation_score,
)

_MUTATION_LABELS = ThresholdReportLabels(
    no_selection_summary="No changed Python files require mutation testing.",
    completed_summary=lambda count: f"Mutation testing completed for {count} file(s).",
    violation_summary=lambda violations, threshold, aggregate: (
        f"{violations} file(s) below mutation threshold {threshold}% "
        f"(aggregate score {aggregate:.1f}%)."
    ),
    pass_summary=lambda count, threshold, aggregate: (
        f"All {count} mutated file(s) meet mutation threshold "
        f"{threshold}% (aggregate score {aggregate:.1f}%)."
    ),
)


@dataclass(frozen=True)
class MutationFinding:
    """Mutation score for one source file."""

    filepath: str
    score: float
    killed: int
    total: int
    above_threshold: bool


@dataclass(frozen=True)
class MutationReport:
    """Aggregate mutation testing report."""

    tool: str
    status: ReportStatus
    threshold: float
    findings: tuple[MutationFinding, ...]
    summary: str
    skipped_unchanged: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self)

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent)


def parse_mutmut_meta(meta_path: Path) -> tuple[int, int]:
    """Return killed and total mutant counts from a mutmut meta file."""
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    exit_codes = payload.get("exit_code_by_key", {})
    if not isinstance(exit_codes, dict):
        return 0, 0

    killed = 0
    total = 0
    for raw_code in exit_codes.values():
        if raw_code is None:
            continue
        total += 1
        if classify_mutmut_exit_code(int(raw_code)) == "killed":
            killed += 1
    return killed, total


def build_findings_from_meta(
    project_root: Path,
    filepaths: list[Path],
    *,
    threshold: float,
) -> list[MutationFinding]:
    findings: list[MutationFinding] = []
    for filepath in filepaths:
        relative = filepath.relative_to(project_root)
        meta_path = project_root / "mutants" / f"{relative.as_posix()}.meta"
        if not meta_path.is_file():
            findings.append(
                MutationFinding(
                    filepath=str(relative).replace("\\", "/"),
                    score=0.0,
                    killed=0,
                    total=0,
                    above_threshold=True,
                ),
            )
            continue

        killed, total = parse_mutmut_meta(meta_path)
        score = compute_mutation_score(killed, total)
        findings.append(
            MutationFinding(
                filepath=str(relative).replace("\\", "/"),
                score=score,
                killed=killed,
                total=total,
                above_threshold=score < threshold,
            ),
        )
    return findings


def build_mutation_report(
    *,
    threshold: float,
    findings: list[MutationFinding],
    skipped_unchanged: list[str],
    selected_count: int,
) -> MutationReport:
    return cast(
        MutationReport,
        build_threshold_report(
            tool="mutation",
            report_cls=cast(Any, MutationReport),
            threshold=threshold,
            findings=cast(Sequence[ThresholdFinding], findings),
            skipped_unchanged=skipped_unchanged,
            selected_count=selected_count,
            labels=_MUTATION_LABELS,
        ),
    )
