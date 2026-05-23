"""Tests for Gherkin feature parsing."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.mutation.gherkin.parser import parse_feature_file, scenario_content_hash


def _write_feature(tmp_path: Path, relative: str, content: str) -> Path:
    feature = tmp_path / relative
    feature.parent.mkdir(parents=True, exist_ok=True)
    feature.write_text(content, encoding="utf-8")
    return feature


def test_parse_feature_file_extracts_scenario_outline(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "features/sample.feature",
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
    )

    scenarios = parse_feature_file(feature, project_root=tmp_path)
    assert len(scenarios) == 1
    scenario = scenarios[0]
    assert scenario.name == "Add numbers"
    assert scenario.filepath == "features/sample.feature"
    assert scenario.start_line == 3
    assert scenario.end_line == 9
    assert scenario.examples is not None
    assert scenario.examples.header == ("a", "b", "result")
    assert scenario.examples.header_line_index == 7
    assert len(scenario.examples.rows) == 1
    assert scenario.examples.rows[0].line_index == 8
    assert scenario.examples.rows[0].cells == ("1", "2", "3")
    assert scenario.block_text == "\n".join(
        [
            "  Scenario Outline: Add numbers",
            "    Given values <a> and <b>",
            "    Then result is <result>",
            "",
            "    Examples:",
            "      | a | b | result |",
            "      | 1 | 2 | 3      |",
        ],
    )


def test_parse_feature_file_extracts_multiple_scenarios(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "features/multi.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: First",
                "    Examples:",
                "      | x |",
                "      | 1 |",
                "",
                "  Scenario: Second",
                "    Examples:",
                "      | y |",
                "      | 2 |",
            ],
        )
        + "\n",
    )

    scenarios = parse_feature_file(feature, project_root=tmp_path)
    assert [scenario.name for scenario in scenarios] == ["First", "Second"]
    assert scenarios[0].start_line == 3
    assert scenarios[0].end_line == 7
    assert scenarios[1].start_line == 8
    assert scenarios[1].end_line == 11
    assert scenarios[0].examples is not None
    assert scenarios[1].examples is not None
    assert scenarios[0].examples.rows[0].cells == ("1",)
    assert scenarios[1].examples.rows[0].cells == ("2",)


def test_parse_feature_file_skips_blank_lines_before_examples_header(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Demo",
                "    Examples:",
                "",
                "      | x |",
                "      | 1 |",
            ],
        )
        + "\n",
    )

    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario.examples is not None
    assert scenario.examples.header_line_index == 5
    assert scenario.examples.rows[0].line_index == 6


def test_parse_feature_file_returns_none_examples_for_malformed_table(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Demo",
                "    Examples:",
                "      not a table row",
            ],
        )
        + "\n",
    )

    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario.examples is None


def test_parse_feature_file_returns_none_examples_for_header_only_table(
    tmp_path: Path,
) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Demo",
                "    Examples:",
                "      | x |",
            ],
        )
        + "\n",
    )

    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario.examples is None


def test_parse_feature_file_uses_last_examples_block(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Demo",
                "    Examples:",
                "      | x |",
                "      | 1 |",
                "    Examples:",
                "      | y |",
                "      | 2 |",
            ],
        )
        + "\n",
    )

    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario.examples is not None
    assert scenario.examples.header == ("y",)
    assert scenario.examples.rows[0].cells == ("2",)


def test_parse_feature_file_parses_scenario_without_examples(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "Feature: Demo\n\n  Scenario Outline: Empty\n    Given nothing happens\n",
    )

    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario.name == "Empty"
    assert scenario.examples is None
    assert "Given nothing happens" in scenario.block_text


def test_scenario_content_hash_is_stable(tmp_path: Path) -> None:
    feature = _write_feature(
        tmp_path,
        "sample.feature",
        "Feature: Demo\n\n  Scenario Outline: Demo\n    Examples:\n      | x |\n      | 1 |\n",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    assert scenario_content_hash(scenario.block_text) == scenario_content_hash(scenario.block_text)
