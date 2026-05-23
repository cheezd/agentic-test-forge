"""Tests for analyze_gherkin_mutation orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agentic_test_forge.mutation.gherkin.analyze import analyze_gherkin_mutation
from agentic_test_forge.mutation.gherkin.parser import parse_feature_file
from agentic_test_forge.mutation.gherkin.report import GherkinFinding
from agentic_test_forge.mutation.gherkin.scope import GherkinScopeResult


def test_analyze_gherkin_mutation_without_selected_scenarios(tmp_path: Path) -> None:
    scope = GherkinScopeResult(selected=(), skipped_unchanged=(), base_ref="main")
    with patch(
        "agentic_test_forge.mutation.gherkin.analyze.resolve_gherkin_scope",
        return_value=scope,
    ):
        report = analyze_gherkin_mutation(["features"], threshold=80, search_root=tmp_path)

    assert report.status == "pass"


def test_analyze_gherkin_mutation_evaluates_scenarios_and_updates_manifest(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    scope = GherkinScopeResult(selected=(scenario,), skipped_unchanged=(), base_ref="main")
    finding = GherkinFinding(
        scenario_id=scenario.scenario_id,
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )

    with (
        patch(
            "agentic_test_forge.mutation.gherkin.analyze.resolve_gherkin_scope",
            return_value=scope,
        ),
        patch(
            "agentic_test_forge.mutation.gherkin.analyze.evaluate_scenario",
            return_value=finding,
        ),
    ):
        report = analyze_gherkin_mutation(
            ["features"],
            threshold=80,
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
            run_tests=False,
        )

    assert report.status == "pass"
    manifest_file = tmp_path / ".forge" / "gherkin-manifest.json"
    assert manifest_file.is_file()


def test_evaluate_scenario_runs_mutations_and_scores(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )

    with patch(
        "agentic_test_forge.mutation.gherkin.mutator.run_acceptance_tests",
        return_value=1,
    ):
        report = analyze_gherkin_mutation(
            ["features"],
            threshold=80,
            search_root=tmp_path,
            full_run=True,
            run_tests=True,
        )

    assert report.status == "pass"
    assert report.findings[0].killed == report.findings[0].total
