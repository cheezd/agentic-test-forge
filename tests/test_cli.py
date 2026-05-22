"""Tests for the forge CLI."""

from typer.testing import CliRunner

from agentic_test_forge.cli.main import NOT_IMPLEMENTED_EXIT, app

runner = CliRunner()


def test_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "crap" in result.stdout
    assert "check" in result.stdout
    assert "mutate-gherkin" in result.stdout


def test_crap_stub_exits_not_implemented() -> None:
    result = runner.invoke(app, ["crap"])
    assert result.exit_code == NOT_IMPLEMENTED_EXIT
    assert "not implemented" in result.output.lower()


def test_check_stub_exits_not_implemented() -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == NOT_IMPLEMENTED_EXIT


def test_mutate_gherkin_stub_exits_not_implemented() -> None:
    result = runner.invoke(app, ["mutate-gherkin"])
    assert result.exit_code == NOT_IMPLEMENTED_EXIT
