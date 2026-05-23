"""Rich formatters for forge reports."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from agentic_test_forge.analysis.crap import CrapReport
from agentic_test_forge.analysis.dry import DryReport
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.mutation.gherkin.report import GherkinMutationReport
from agentic_test_forge.orchestration.report import CheckReport
from agentic_test_forge.reporting.status import ReportStatus


def print_crap_report(report: CrapReport, console: Console) -> None:
    """Render a human-readable CRAP report."""
    status_style = "green" if report.status == ReportStatus.PASS else "red"
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


def print_mutation_report(report: MutationReport, console: Console) -> None:
    """Render a human-readable mutation report."""
    status_style = "green" if report.status == ReportStatus.PASS else "red"
    status = report.status.upper()
    console.print(
        f"[bold]Mutation analysis[/bold] — [{status_style}]{status}[/{status_style}]",
    )
    console.print(report.summary)

    if report.skipped_unchanged:
        skipped_count = len(report.skipped_unchanged)
        console.print(
            f"[dim]{skipped_count} file(s) skipped (unchanged manifest hash).[/dim]",
        )

    if not report.findings:
        return

    table = Table(title="File mutation scores")
    table.add_column("File")
    table.add_column("Killed", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Flag", justify="center")

    for finding in report.findings:
        flag = "[red]FAIL[/red]" if finding.above_threshold else "[green]ok[/green]"
        table.add_row(
            finding.filepath,
            str(finding.killed),
            str(finding.total),
            f"{finding.score:.1f}%",
            flag,
        )

    console.print(table)


def print_dry_report(report: DryReport, console: Console) -> None:
    """Render an advisory DRY duplication report."""
    console.print("[bold]DRY analysis[/bold] — [yellow]ADVISORY[/yellow]")
    console.print(report.summary)

    if not report.findings:
        return

    table = Table(title="Potential duplicate functions")
    table.add_column("Function")
    table.add_column("File")
    table.add_column("Duplicate of")

    for finding in report.findings:
        table.add_row(
            finding.qualified_name,
            finding.filepath,
            f"{finding.duplicate_of} ({finding.duplicate_filepath})",
        )

    console.print(table)


def print_check_report(report: CheckReport, console: Console) -> None:
    """Render a combined quality gate report."""
    if report.status == ReportStatus.PASS:
        status_style = "green"
        label = "PASS"
    elif report.status == ReportStatus.ERROR:
        status_style = "red"
        label = "ERROR"
    else:
        status_style = "red"
        label = "FAIL"
    console.print(f"[bold]Quality gate[/bold] — [{status_style}]{label}[/{status_style}]")
    console.print(report.summary)

    if report.dry is not None:
        console.print()
        print_dry_report(report.dry, console)
    if report.crap is not None:
        console.print()
        print_crap_report(report.crap, console)
    if report.mutation is not None:
        console.print()
        print_mutation_report(report.mutation, console)
    if report.gherkin is not None:
        console.print()
        print_gherkin_mutation_report(report.gherkin, console)


def print_gherkin_mutation_report(report: GherkinMutationReport, console: Console) -> None:
    """Render a human-readable Gherkin mutation report."""
    status_style = "green" if report.status == ReportStatus.PASS else "red"
    status = report.status.upper()
    console.print(
        f"[bold]Gherkin mutation[/bold] — [{status_style}]{status}[/{status_style}]",
    )
    console.print(report.summary)

    if report.skipped_unchanged:
        skipped_count = len(report.skipped_unchanged)
        console.print(
            f"[dim]{skipped_count} scenario(s) skipped (unchanged manifest hash).[/dim]",
        )

    if not report.findings:
        return

    table = Table(title="Scenario mutation scores")
    table.add_column("Scenario")
    table.add_column("Killed", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Flag", justify="center")

    for finding in report.findings:
        flag = "[red]FAIL[/red]" if finding.above_threshold else "[green]ok[/green]"
        table.add_row(
            finding.scenario_id,
            str(finding.killed),
            str(finding.total),
            f"{finding.score:.1f}%",
            flag,
        )

    console.print(table)
