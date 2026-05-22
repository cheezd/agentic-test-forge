"""Tests for Gherkin Examples mutators."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.mutation.gherkin.mutator import (
    apply_mutation,
    generate_example_mutations,
    mutate_cell_value,
)
from agentic_test_forge.mutation.gherkin.parser import parse_feature_file


def test_mutate_cell_value_changes_numbers() -> None:
    mutations = mutate_cell_value("42")
    assert "43" in mutations
    assert "41" in mutations


def test_generate_and_apply_example_mutation(tmp_path: Path) -> None:
    feature = tmp_path / "sample.feature"
    feature.write_text(
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Add numbers",
                "    Examples:",
                "      | a | result |",
                "      | 1 | 3      |",
            ],
        )
        + "\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    mutations = generate_example_mutations(scenario)
    assert mutations

    original_lines = feature.read_text(encoding="utf-8").splitlines()
    mutated_lines = apply_mutation(original_lines, scenario, mutations[0])
    assert mutated_lines != original_lines
    assert mutations[0].mutated in mutated_lines[mutations[0].line_index]
