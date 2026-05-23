"""Tests for shared report serialization helpers."""

from __future__ import annotations

from agentic_test_forge.analysis.crap import CrapFinding, CrapReport
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus


def test_serialize_findings_report_matches_crap_to_dict() -> None:
    report = CrapReport(
        tool="crap",
        status=ReportStatus.PASS,
        threshold=30,
        formula="standard",
        findings=(
            CrapFinding(
                qualified_name="sample.fn",
                filepath="src/sample.py",
                complexity=5.0,
                coverage=0.9,
                crap_score=10.0,
                above_threshold=False,
            ),
        ),
        summary="ok",
    )

    payload = serialize_findings_report(report)

    assert payload["tool"] == "crap"
    assert payload["findings"][0]["qualified_name"] == "sample.fn"
    assert report_to_json(report).startswith("{\n")


def test_mutation_report_json_shape_unchanged() -> None:
    report = MutationReport(
        tool="mutation",
        status=ReportStatus.PASS,
        threshold=80.0,
        findings=(),
        summary="ok",
        skipped_unchanged=("src/unchanged.py",),
    )

    payload = report.to_dict()

    assert payload == {
        "tool": "mutation",
        "status": ReportStatus.PASS,
        "threshold": 80.0,
        "findings": [],
        "summary": "ok",
        "skipped_unchanged": ("src/unchanged.py",),
    }
