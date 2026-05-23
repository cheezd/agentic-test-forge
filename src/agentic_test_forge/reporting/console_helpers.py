"""Shared Rich console helpers for forge reports."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from rich.console import Console
from rich.table import Table

from agentic_test_forge.reporting.status import ReportStatus

ColumnJustify = Literal["default", "left", "center", "right", "full"]


def print_status_header(
    console: Console,
    *,
    title: str,
    status: ReportStatus,
    label: str | None = None,
) -> None:
    """Print a bold report title with colored status."""
    if status == ReportStatus.PASS:
        status_style = "green"
        status_label = label or status.upper()
    elif status == ReportStatus.ERROR:
        status_style = "red"
        status_label = label or "ERROR"
    else:
        status_style = "red"
        status_label = label or status.upper()

    console.print(
        f"[bold]{title}[/bold] — [{status_style}]{status_label}[/{status_style}]",
    )


def print_advisory_header(console: Console, *, title: str) -> None:
    """Print a report title marked advisory (non-blocking)."""
    console.print(f"[bold]{title}[/bold] — [yellow]ADVISORY[/yellow]")


def print_skipped_unchanged(
    console: Console,
    *,
    count: int,
    entity_label: str,
) -> None:
    """Print manifest skip count when entities were unchanged."""
    if count <= 0:
        return
    console.print(
        f"[dim]{count} {entity_label} skipped (unchanged manifest hash).[/dim]",
    )


def print_findings_table(
    console: Console,
    *,
    title: str,
    columns: Sequence[tuple[str, ColumnJustify | None]],
    rows: Sequence[Sequence[str]],
) -> None:
    """Render a findings table when rows are present."""
    if not rows:
        return

    table = Table(title=title)
    for header, justify in columns:
        table.add_column(header, justify=justify or "left")

    for row in rows:
        table.add_row(*row)

    console.print(table)


def threshold_flag_cell(above_threshold: bool) -> str:
    """Return Rich markup for a pass/fail threshold flag."""
    if above_threshold:
        return "[red]FAIL[/red]"
    return "[green]ok[/green]"
