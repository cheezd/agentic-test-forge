"""Tests for Gherkin feature parsing."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.mutation.gherkin.parser import parse_feature_file, scenario_content_hash


def test_parse_feature_file_extracts_scenario_outline(tmp_path: Path) -> None:
    feature = tmp_path / "features" / "sample.feature"
    feature.parent.mkdir(parents=True)
    feature.write_text(
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Add numbers",
                "    Given values <a> and <b>",
                "    Then result is <result>",
                "",
                "    Examples:",
                "      | a | b | result |",
                "      | 1 | 2 | 3      |",
            ],
        )
        + "\n",
        encoding="utf-8",
    )

    scenarios = parse_feature_file(feature, project_root=tmp_path)
    assert len(scenarios) == 1
    scenario = scenarios[0]
    assert scenario.name == "Add numbers"
    assert scenario.examples is not None
    assert scenario.examples.header == ("a", "b", "result")
    assert len(scenario.examples.rows) == 1
    assert scenario.examples.rows[0].cells == ("1", "2", "3")


def test_scenario_content_hash_is_stable(tmp_path: Path) -> None:
    feature = tmp_path / "sample.feature"
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Demo\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario_content_hash(scenario.block_text) == scenario_content_hash(scenario.block_text)
