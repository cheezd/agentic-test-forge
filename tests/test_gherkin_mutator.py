"""Tests for safe Gherkin feature file editing and scenario mutation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agentic_test_forge.mutation.gherkin.feature_editor import FeatureFileEditor
from agentic_test_forge.mutation.gherkin.mutator import ScenarioMutator
from agentic_test_forge.mutation.gherkin.parser import parse_feature_file
from agentic_test_forge.mutation.gherkin.scoring import DRY_RUN_MUTATION_EXIT_CODE


def test_feature_file_editor_does_not_mutate_source(tmp_path: Path) -> None:
    feature = tmp_path / "sample.feature"
    original = (
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n"
    )
    feature.write_text(original, encoding="utf-8")

    with FeatureFileEditor(feature) as editor:
        editor.write_lines(["mutated"])

    assert feature.read_text(encoding="utf-8") == original


def test_scenario_mutator_dry_run_uses_documented_exit_code(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    mutator = ScenarioMutator(
        project_root=tmp_path,
        test_cmd="behave",
        runner="behave",
        run_tests=False,
    )

    with patch(
        "agentic_test_forge.mutation.gherkin.mutator.run_acceptance_tests",
        side_effect=AssertionError("dry-run must not invoke subprocess"),
    ):
        finding = mutator.apply_and_test(scenario, threshold=80)

    assert DRY_RUN_MUTATION_EXIT_CODE != 0
    assert finding.killed == finding.total
