"""Tests for shared CLI helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from rich.console import Console

from agentic_test_forge.analysis.crap import CrapReport
from agentic_test_forge.cli.exit_codes import ForgeExitCode
from agentic_test_forge.cli.helpers import effective_override, run_report_command, write_json_report
from agentic_test_forge.reporting.status import ReportStatus


def test_effective_override_prefers_cli_value() -> None:
    assert effective_override(5.0, 30.0) == 5.0
    assert effective_override(None, 30.0) == 30.0


def test_write_json_report_writes_file(tmp_path: Path) -> None:
    report = CrapReport(
        tool="crap",
        status=ReportStatus.PASS,
        threshold=30,
        formula="standard",
        findings=(),
        summary="ok",
    )
    console = Console(record=True)
    target = tmp_path / "out.json"
    write_json_report(report, str(target), console)
    assert target.is_file()
    assert '"tool": "crap"' in target.read_text(encoding="utf-8")


def test_run_report_command_exits_on_gate_failure() -> None:
    report = CrapReport(
        tool="crap",
        status=ReportStatus.FAIL,
        threshold=30,
        formula="standard",
        findings=(),
        summary="bad",
    )
    console = Console()
    with pytest.raises(typer.Exit) as exc_info:
        run_report_command(
            analyze=lambda: report,
            print_report=MagicMock(),
            console=console,
        )
    assert exc_info.value.exit_code == ForgeExitCode.GATE_FAILURE
