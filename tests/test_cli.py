"""Tests for the forge CLI."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from agentic_test_forge.analysis.crap import CoverageDataMissingError, CrapFinding, CrapReport
from agentic_test_forge.cli.main import NOT_IMPLEMENTED_EXIT, app
from agentic_test_forge.mutation.code import (
    MutationFinding,
    MutationReport,
    MutationUnavailableError,
)

runner = CliRunner()


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "crap" in result.stdout
    assert "mutate" in result.stdout
    assert "check" in result.stdout
    assert "mutate-gherkin" in result.stdout


def test_crap_reports_failure_when_threshold_exceeded() -> None:
    report = CrapReport(
        tool="crap",
        status="fail",
        threshold=6,
        formula="standard",
        findings=(
            CrapFinding(
                qualified_name="complex_uncovered",
                filepath="sample.py",
                complexity=5.0,
                coverage=0.0,
                crap_score=30.0,
                above_threshold=True,
            ),
        ),
        summary="1 function(s) exceed CRAP threshold 6.",
    )
    with patch("agentic_test_forge.cli.main.analyze_crap", return_value=report):
        result = runner.invoke(app, ["crap", "--path", "src", "--threshold", "6"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_crap_missing_coverage_exits_with_error() -> None:
    with patch(
        "agentic_test_forge.cli.main.analyze_crap",
        side_effect=CoverageDataMissingError("missing"),
    ):
        result = runner.invoke(app, ["crap"])
    assert result.exit_code == 1
    assert "missing" in result.output


def test_crap_json_output(tmp_path: Path) -> None:
    report = CrapReport(
        tool="crap",
        status="pass",
        threshold=30,
        formula="standard",
        findings=(),
        summary="All clear.",
    )
    json_path = tmp_path / "report.json"
    with patch("agentic_test_forge.cli.main.analyze_crap", return_value=report):
        result = runner.invoke(app, ["crap", "--json", str(json_path)])
    assert result.exit_code == 0
    assert json_path.is_file()
    assert '"tool": "crap"' in json_path.read_text(encoding="utf-8")


def test_check_stub_exits_not_implemented() -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == NOT_IMPLEMENTED_EXIT


def test_mutate_gherkin_stub_exits_not_implemented() -> None:
    result = runner.invoke(app, ["mutate-gherkin"])
    assert result.exit_code == NOT_IMPLEMENTED_EXIT


def test_mutate_reports_failure_when_threshold_not_met() -> None:
    report = MutationReport(
        tool="mutation",
        status="fail",
        threshold=80.0,
        findings=(
            MutationFinding(
                filepath="src/sample.py",
                score=50.0,
                killed=1,
                total=2,
                above_threshold=True,
            ),
        ),
        summary="1 file(s) below mutation threshold 80.0%.",
    )
    with patch("agentic_test_forge.cli.main.analyze_mutation", return_value=report):
        result = runner.invoke(app, ["mutate", "--path", "src", "--threshold", "80"])
    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_mutate_unavailable_exits_with_error() -> None:
    with patch(
        "agentic_test_forge.cli.main.analyze_mutation",
        side_effect=MutationUnavailableError("mutmut unavailable"),
    ):
        result = runner.invoke(app, ["mutate"])
    assert result.exit_code == 2
    assert "mutmut unavailable" in result.output


def test_mutate_json_output(tmp_path: Path) -> None:
    report = MutationReport(
        tool="mutation",
        status="pass",
        threshold=80.0,
        findings=(),
        summary="All clear.",
    )
    json_path = tmp_path / "mutation.json"
    with patch("agentic_test_forge.cli.main.analyze_mutation", return_value=report):
        result = runner.invoke(app, ["mutate", "--json", str(json_path)])
    assert result.exit_code == 0
    assert json_path.is_file()
    assert '"tool": "mutation"' in json_path.read_text(encoding="utf-8")
