"""Rich formatters for forge reports."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from agentic_test_forge.analysis.crap import CrapReport


def print_crap_report(report: CrapReport, console: Console) -> None:
    """Render a human-readable CRAP report."""
    status_style = "green" if report.status == "pass" else "red"
    status = report.status.upper()
    console.print(f"[bold]CRAP analysis[/bold] — [{status_style}]{status}[/{status_style}]")
    console.print(report.summary)

    if not report.findings:
        return

    table = Table(title="Function CRAP scores")
    table.add_column("Function")
    table.add_column("Complexity", justify="right")
    table.add_column("Coverage", justify="right")
    table.add_column("CRAP", justify="right")
    table.add_column("Flag", justify="center")

    for finding in report.findings:
        flag = "[red]FAIL[/red]" if finding.above_threshold else "[green]ok[/green]"
        table.add_row(
            finding.qualified_name,
            f"{finding.complexity:.0f}",
            f"{finding.coverage:.0%}",
            f"{finding.crap_score:.2f}",
            flag,
        )

    console.print(table)
