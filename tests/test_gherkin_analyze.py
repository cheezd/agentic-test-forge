"""Tests for analyze_gherkin_mutation orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    ForgeManifest,
    gherkin_manifest_path,
    load_manifest,
)
from agentic_test_forge.mutation.gherkin.analyze import (
    _manifest_entry_for_scenario,
    _persist_gherkin_manifest,
    _skipped_scenario_ids,
    _updated_gherkin_manifest_files,
    analyze_gherkin_mutation,
)
from agentic_test_forge.mutation.gherkin.parser import parse_feature_file
from agentic_test_forge.mutation.gherkin.report import GherkinFinding
from agentic_test_forge.mutation.gherkin.scope import GherkinScopeResult


def test_skipped_scenario_ids_collects_scope_skips(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    scope = GherkinScopeResult(selected=(), skipped_unchanged=(scenario,), base_ref="main")

    assert _skipped_scenario_ids(scope) == [scenario.scenario_id]


def test_manifest_entry_for_scenario_maps_fields(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    finding = GherkinFinding(
        scenario_id=scenario.scenario_id,
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )
    timestamp = "2026-05-23T00:00:00Z"

    entry = _manifest_entry_for_scenario(scenario, finding, timestamp=timestamp)

    assert entry.score == 100.0
    assert entry.last_run == timestamp
    assert entry.content_hash


def test_updated_gherkin_manifest_files_preserves_existing_entries(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    finding = GherkinFinding(
        scenario_id=scenario.scenario_id,
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )
    legacy = FileManifestEntry(content_hash="abc", score=1.0, last_run="old")
    manifest = ForgeManifest(files={"legacy.feature": legacy})
    timestamp = "2026-05-23T00:00:00Z"

    updated = _updated_gherkin_manifest_files(
        manifest,
        [scenario],
        [finding],
        timestamp=timestamp,
    )

    assert updated["legacy.feature"] == legacy
    assert updated[scenario.scenario_id].score == 100.0
    assert updated[scenario.scenario_id].last_run == timestamp


def test_persist_gherkin_manifest_writes_json(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    finding = GherkinFinding(
        scenario_id=scenario.scenario_id,
        score=100.0,
        killed=1,
        total=1,
        above_threshold=False,
    )
    manifest_dir = str(tmp_path / ".forge")

    _persist_gherkin_manifest(
        scenarios=[scenario],
        findings=[finding],
        manifest_dir=manifest_dir,
    )

    manifest = load_manifest(gherkin_manifest_path(manifest_dir))
    assert manifest.files[scenario.scenario_id].score == 100.0

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
            "agentic_test_forge.mutation.gherkin.analyze._findings_for_scenarios",
            return_value=[finding],
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
