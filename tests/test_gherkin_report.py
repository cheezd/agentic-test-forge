"""Tests for Gherkin mutation report building."""

from __future__ import annotations

from agentic_test_forge.mutation.gherkin.report import (
    GherkinFinding,
    build_gherkin_mutation_report,
)


def test_build_gherkin_mutation_report_passes_when_no_scenarios_selected() -> None:
    report = build_gherkin_mutation_report(
        threshold=80.0,
        findings=[],
        skipped_unchanged=[],
        selected_count=0,
    )
    assert report.status == "pass"


def test_build_gherkin_mutation_report_fails_when_findings_below_threshold() -> None:
    findings = [
        GherkinFinding(
            scenario_id="features/sample.feature::Add",
            score=50.0,
            killed=1,
            total=2,
            above_threshold=True,
        ),
    ]
    report = build_gherkin_mutation_report(
        threshold=80.0,
        findings=findings,
        skipped_unchanged=["features/old.feature::Old"],
        selected_count=1,
    )
    assert report.status == "fail"
    assert report.skipped_unchanged == ("features/old.feature::Old",)
