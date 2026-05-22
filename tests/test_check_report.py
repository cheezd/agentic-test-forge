"""Tests for combined check report building."""

from __future__ import annotations

from agentic_test_forge.analysis.crap import CrapReport
from agentic_test_forge.analysis.dry import DryReport
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.orchestration.report import build_check_report


def test_build_check_report_when_no_gates_enabled() -> None:
    report = build_check_report(
        gates_run=[],
        crap=None,
        mutation=None,
        gherkin=None,
        dry=None,
        errors=[],
    )
    assert report.status == "pass"
    assert "No quality gates enabled" in report.summary


def test_build_check_report_fails_when_sub_gate_fails() -> None:
    crap = CrapReport(
        tool="crap",
        status="fail",
        threshold=30,
        formula="standard",
        findings=(),
        summary="bad",
    )
    report = build_check_report(
        gates_run=["crap"],
        crap=crap,
        mutation=None,
        gherkin=None,
        dry=None,
        errors=[],
    )
    assert report.status == "fail"
    assert "crap" in report.summary


def test_build_check_report_json_includes_dry_report() -> None:
    dry = DryReport(
        tool="dry",
        status="pass",
        findings=(),
        summary="ok",
    )
    report = build_check_report(
        gates_run=["dry"],
        crap=None,
        mutation=None,
        gherkin=None,
        dry=dry,
        errors=[],
    )
    payload = report.to_dict()
    assert payload["reports"]["dry"]["tool"] == "dry"


def test_build_check_report_json_includes_sub_reports() -> None:
    mutation = MutationReport(
        tool="mutation",
        status="pass",
        threshold=80,
        findings=(),
        summary="ok",
    )
    report = build_check_report(
        gates_run=["mutation"],
        crap=None,
        mutation=mutation,
        gherkin=None,
        dry=None,
        errors=[],
    )
    payload = report.to_dict()
    assert payload["reports"]["mutation"]["tool"] == "mutation"
