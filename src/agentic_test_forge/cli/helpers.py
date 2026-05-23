"""Shared CLI helpers for forge gate commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, TypeVar

from rich.console import Console

from agentic_test_forge.cli.exit_codes import (
    exit_for_check_report,
    exit_for_report_status,
    exit_for_tool_error,
)
from agentic_test_forge.errors import ForgeToolError
from agentic_test_forge.orchestration.report import CheckReport
from agentic_test_forge.reporting.console import print_check_report
from agentic_test_forge.reporting.status import ReportStatus


class StatusReport(Protocol):
    """Report with gate status used for CLI exit codes."""

    @property
    def status(self) -> ReportStatus: ...


class JsonReport(StatusReport, Protocol):
    """Report objects that can serialize to JSON."""

    def to_json(self, indent: int = 2) -> str: ...


ReportT = TypeVar("ReportT", bound=JsonReport)
OverrideT = TypeVar("OverrideT")


def effective_override(cli_value: OverrideT | None, config_value: OverrideT) -> OverrideT:
    """Return CLI override when provided, otherwise config default."""
    return config_value if cli_value is None else cli_value


def write_json_report(report: JsonReport, path: str, console: Console) -> None:
    """Write a structured JSON report and notify on the console."""
    Path(path).write_text(report.to_json(), encoding="utf-8")
    console.print(f"JSON report written to [bold]{path}[/bold]")


def run_report_command(
    *,
    analyze: Callable[[], ReportT],
    print_report: Callable[[ReportT, Console], None],
    console: Console,
    json_output: str | None = None,
) -> None:
    """Run analysis, print human output, optionally write JSON, then exit by status."""
    try:
        report = analyze()
    except ForgeToolError as exc:
        exit_for_tool_error(exc, console)

    print_report(report, console)

    if json_output:
        write_json_report(report, json_output, console)

    exit_for_report_status(report.status)


def run_check_command(
    *,
    analyze: Callable[[], CheckReport],
    console: Console,
    json_output: str | None = None,
) -> None:
    """Run quality check orchestration and exit using check report policy."""
    report = analyze()
    print_check_report(report, console)

    if json_output:
        write_json_report(report, json_output, console)

    exit_for_check_report(report, console)
