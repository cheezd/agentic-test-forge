"""Tests for CLI exit codes and forge error hierarchy."""

from __future__ import annotations

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from agentic_test_forge.analysis.crap import CoverageDataMissingError
from agentic_test_forge.cli.exit_codes import (
    ForgeExitCode,
    exit_for_check_report,
    exit_for_report_status,
    exit_for_tool_error,
)
from agentic_test_forge.cli.main import app
from agentic_test_forge.errors import ForgeError, ForgeToolError
from agentic_test_forge.mutation.code import GitScopeError, MutationUnavailableError, MutmutRunError
from agentic_test_forge.mutation.gherkin import GherkinRunError
from agentic_test_forge.orchestration.report import CheckReport
from agentic_test_forge.reporting.status import ReportStatus

runner = CliRunner()
console = Console()


def test_forge_exit_code_values_match_ci_contract() -> None:
    assert ForgeExitCode.SUCCESS == 0
    assert ForgeExitCode.GATE_FAILURE == 1
    assert ForgeExitCode.TOOL_ERROR == 2


@pytest.mark.parametrize(
    ("error_type",),
    [
        (CoverageDataMissingError,),
        (GitScopeError,),
        (MutationUnavailableError,),
        (MutmutRunError,),
        (GherkinRunError,),
    ],
)
def test_tool_errors_inherit_forge_tool_error(error_type: type[ForgeToolError]) -> None:
    assert issubclass(error_type, ForgeToolError)
    assert issubclass(error_type, ForgeError)


def test_exit_for_tool_error_uses_tool_error_code() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        exit_for_tool_error(CoverageDataMissingError("missing"), console)
    assert exc_info.value.exit_code == ForgeExitCode.TOOL_ERROR


def test_exit_for_report_status_raises_on_fail() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        exit_for_report_status(ReportStatus.FAIL)
    assert exc_info.value.exit_code == ForgeExitCode.GATE_FAILURE


def test_exit_for_check_report_tool_error_when_errors_present() -> None:
    report = CheckReport(
        tool="check",
        status=ReportStatus.ERROR,
        summary="errors",
        gates_run=("mutation",),
        errors=("mutation: unavailable",),
    )
    with pytest.raises(typer.Exit) as exc_info:
        exit_for_check_report(report, console)
    assert exc_info.value.exit_code == ForgeExitCode.TOOL_ERROR


def test_cli_crap_missing_coverage_uses_forge_exit_code() -> None:
    from unittest.mock import patch

    with patch(
        "agentic_test_forge.cli.main.analyze_crap",
        side_effect=CoverageDataMissingError("missing"),
    ):
        result = runner.invoke(app, ["crap"])
    assert result.exit_code == ForgeExitCode.TOOL_ERROR
