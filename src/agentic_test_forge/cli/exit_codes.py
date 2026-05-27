"""CLI exit codes and helpers.

Contract (see docs/consumer-ci.md):
- SUCCESS (0): all blocking gates passed
- GATE_FAILURE (1): threshold failure in CRAP, mutation, or Gherkin gate
- TOOL_ERROR (2): tool or precondition error (missing coverage, git, mutmut, etc.)
"""

from __future__ import annotations

from enum import IntEnum
from typing import NoReturn

import typer
from rich.console import Console
from rich.markup import escape

from agentic_test_forge.errors import ForgeToolError
from agentic_test_forge.orchestration.report import CheckReport
from agentic_test_forge.reporting.status import ReportStatus


class ForgeExitCode(IntEnum):
    """Process exit codes for ``forge`` CLI commands."""

    SUCCESS = 0
    GATE_FAILURE = 1
    TOOL_ERROR = 2


def exit_for_tool_error(exc: ForgeToolError, console: Console) -> NoReturn:
    """Print a tool error and exit with TOOL_ERROR."""
    console.print(f"[red]Error:[/red] {escape(str(exc))}")
    raise typer.Exit(code=ForgeExitCode.TOOL_ERROR) from exc


def exit_for_report_status(status: ReportStatus) -> None:
    """Exit with GATE_FAILURE when a standalone gate report failed."""
    if status == ReportStatus.FAIL:
        raise typer.Exit(code=ForgeExitCode.GATE_FAILURE)


def exit_for_check_report(report: CheckReport, console: Console) -> None:
    """Exit based on combined check report errors and gate status."""
    if report.errors or report.status == ReportStatus.ERROR:
        for error in report.errors:
            console.print(f"[red]Error:[/red] {escape(error)}")
        raise typer.Exit(code=ForgeExitCode.TOOL_ERROR)
    exit_for_report_status(report.status)
