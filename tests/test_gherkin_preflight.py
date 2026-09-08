"""Tests for Gherkin lint, inventory, and validate-steps."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agentic_test_forge.cli.exit_codes import ForgeExitCode
from agentic_test_forge.cli.main import app
from agentic_test_forge.mutation.gherkin.inventory import analyze_gherkin_inventory
from agentic_test_forge.mutation.gherkin.lint import analyze_gherkin_lint
from agentic_test_forge.mutation.gherkin.validate_steps import analyze_gherkin_validate_steps
from agentic_test_forge.reporting.status import ReportStatus

runner = CliRunner()

VALID_FEATURE = """\
@GH-153
Feature: Invoice creation

  @billing
  Scenario Outline: Create invoice with valid amount
    Given an authenticated user with billing access
    When they request an invoice for <amount>
    Then the response status is <status>

    Examples:
      | amount | status |
      | 10.00  | 201    |
"""


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_lint_fails_when_mutation_would_skip_plain_scenario(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(
        features / "skip.feature",
        "Feature: Demo\n\n  Scenario: No table\n    Given something\n",
    )

    report = analyze_gherkin_lint([features], search_root=tmp_path)

    assert report.status == ReportStatus.FAIL
    assert [item.rule for item in report.findings] == ["no_examples"]


def test_lint_fails_on_empty_examples_table(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(
        features / "empty.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Empty table",
                "    Given a value <x>",
                "",
                "    Examples:",
                "      | x |",
            ],
        )
        + "\n",
    )

    report = analyze_gherkin_lint([features], search_root=tmp_path)

    assert report.status == ReportStatus.FAIL
    assert [item.rule for item in report.findings] == ["empty_examples"]


def test_lint_fails_on_duplicate_scenario_names(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(
        features / "dup.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Same name",
                "    Examples:",
                "      | x |",
                "      | 1 |",
                "",
                "  Scenario Outline: Same name",
                "    Examples:",
                "      | y |",
                "      | 2 |",
            ],
        )
        + "\n",
    )

    report = analyze_gherkin_lint([features], search_root=tmp_path)

    assert report.status == ReportStatus.FAIL
    assert "duplicate_name" in {item.rule for item in report.findings}


def test_lint_require_tags_and_leakage_warning(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(
        features / "leak.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Uses a service class",
                "    Given InvoiceService is called",
                "    Examples:",
                "      | x |",
                "      | 1 |",
            ],
        )
        + "\n",
    )

    missing_tags = analyze_gherkin_lint([features], search_root=tmp_path, require_tags=True)
    leakage = analyze_gherkin_lint(
        [features],
        search_root=tmp_path,
        flag_implementation_leakage=True,
    )

    assert missing_tags.status == ReportStatus.FAIL
    assert any(item.rule == "missing_tags" for item in missing_tags.findings)
    assert leakage.status == ReportStatus.PASS
    assert any(item.rule == "implementation_leakage" for item in leakage.findings)


def test_inventory_json_schema_includes_tags_and_examples(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "invoice.feature", VALID_FEATURE)

    report = analyze_gherkin_inventory([features], search_root=tmp_path)
    payload = json.loads(report.to_json())

    assert report.status == ReportStatus.PASS
    assert payload["tool"] == "gherkin-inventory"
    assert payload["schema_version"] == 1
    assert len(payload["scenarios"]) == 1
    row = payload["scenarios"][0]
    assert row["filepath"] == "features/invoice.feature"
    assert row["name"] == "Create invoice with valid amount"
    assert row["has_examples"] is True
    assert row["kind"] == "outline"
    assert "@GH-153" in row["tags"]
    assert "@billing" in row["tags"]
    assert row["start_line"] < row["end_line"]


def test_validate_steps_detects_undefined_and_matches_decorators(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "invoice.feature", VALID_FEATURE)
    _write(
        features / "steps" / "billing_steps.py",
        "\n".join(
            [
                "from behave import given, then, when",
                "from behave import parse",
                "",
                "@given('an authenticated user with billing access')",
                "def step_auth(context):",
                "    pass",
                "",
                "@when(parse('they request an invoice for {amount}'))",
                "def step_request(context, amount):",
                "    pass",
            ],
        )
        + "\n",
    )

    report = analyze_gherkin_validate_steps([features], search_root=tmp_path)

    assert report.status == ReportStatus.FAIL
    assert report.step_file_count == 1
    steps = {item.step for item in report.findings}
    assert "the response status is <status>" in steps
    assert "an authenticated user with billing access" not in steps
    assert "they request an invoice for <amount>" not in steps


def test_validate_steps_matches_parsers_re(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(
        features / "re.feature",
        "\n".join(
            [
                "Feature: Demo",
                "",
                "  Scenario Outline: Regex step",
                "    Given order 42 is open",
                "    Examples:",
                "      | x |",
                "      | 1 |",
            ],
        )
        + "\n",
    )
    _write(
        features / "steps" / "re_steps.py",
        "\n".join(
            [
                "from pytest_bdd import given, parsers",
                "",
                "@given(parsers.re(r'order \\d+ is open'))",
                "def step_open():",
                "    pass",
            ],
        )
        + "\n",
    )

    report = analyze_gherkin_validate_steps([features], search_root=tmp_path)

    assert report.status == ReportStatus.PASS
    assert report.findings == ()


def test_validate_steps_passes_when_all_bound(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "invoice.feature", VALID_FEATURE)
    _write(
        features / "steps" / "billing_steps.py",
        "\n".join(
            [
                "from behave import given, then, when",
                "",
                "@given('an authenticated user with billing access')",
                "def step_auth(context):",
                "    pass",
                "",
                "@when('they request an invoice for {amount}')",
                "def step_request(context, amount):",
                "    pass",
                "",
                "@then('the response status is {status}')",
                "def step_status(context, status):",
                "    pass",
            ],
        )
        + "\n",
    )

    report = analyze_gherkin_validate_steps([features], search_root=tmp_path)

    assert report.status == ReportStatus.PASS
    assert report.findings == ()


def test_cli_lint_exits_gate_failure(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "skip.feature", "Feature: Demo\n\n  Scenario: Bare\n    Given x\n")

    result = runner.invoke(app, ["gherkin", "lint", "--path", str(features)])

    assert result.exit_code == ForgeExitCode.GATE_FAILURE
    assert "no_examples" in result.output


def test_cli_inventory_writes_json(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "invoice.feature", VALID_FEATURE)
    json_path = tmp_path / "inventory.json"

    result = runner.invoke(
        app,
        ["gherkin", "inventory", "--path", str(features), "--json", str(json_path)],
    )

    assert result.exit_code == ForgeExitCode.SUCCESS
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["scenarios"][0]["name"] == "Create invoice with valid amount"


def test_cli_validate_steps_exits_gate_failure_when_undefined(tmp_path: Path) -> None:
    features = tmp_path / "features"
    _write(features / "invoice.feature", VALID_FEATURE)

    result = runner.invoke(app, ["gherkin", "validate-steps", "--path", str(features)])

    assert result.exit_code == ForgeExitCode.GATE_FAILURE
    assert "undefined" in result.output.lower()
