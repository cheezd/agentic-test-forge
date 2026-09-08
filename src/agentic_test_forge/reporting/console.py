"""Rich formatters for forge reports."""

from __future__ import annotations

from rich.console import Console

from agentic_test_forge.analysis.crap import CrapReport
from agentic_test_forge.analysis.dry import DryReport
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.mutation.gherkin.inventory import GherkinInventoryReport
from agentic_test_forge.mutation.gherkin.lint import GherkinLintReport
from agentic_test_forge.mutation.gherkin.report import GherkinMutationReport
from agentic_test_forge.mutation.gherkin.validate_steps import GherkinValidateStepsReport
from agentic_test_forge.orchestration.report import CheckReport
from agentic_test_forge.reporting.console_helpers import (
    print_advisory_header,
    print_findings_table,
    print_skipped_unchanged,
    print_status_header,
    threshold_flag_cell,
)
from agentic_test_forge.reporting.status import ReportStatus


def print_crap_report(report: CrapReport, console: Console) -> None:
    """Render a human-readable CRAP report."""
    print_status_header(console, title="CRAP analysis", status=report.status)
    console.print(report.summary)

    print_findings_table(
        console,
        title="Function CRAP scores",
        columns=(
            ("Function", None),
            ("Complexity", "right"),
            ("Coverage", "right"),
            ("CRAP", "right"),
            ("Flag", "center"),
        ),
        rows=[
            (
                finding.qualified_name,
                f"{finding.complexity:.0f}",
                f"{finding.coverage:.0%}",
                f"{finding.crap_score:.2f}",
                threshold_flag_cell(finding.above_threshold),
            )
            for finding in report.findings
        ],
    )


def print_mutation_report(report: MutationReport, console: Console) -> None:
    """Render a human-readable mutation report."""
    print_status_header(console, title="Mutation analysis", status=report.status)
    console.print(report.summary)
    print_skipped_unchanged(
        console,
        count=len(report.skipped_unchanged),
        entity_label="file(s)",
    )

    print_findings_table(
        console,
        title="File mutation scores",
        columns=(
            ("File", None),
            ("Killed", "right"),
            ("Total", "right"),
            ("Score", "right"),
            ("Flag", "center"),
        ),
        rows=[
            (
                finding.filepath,
                str(finding.killed),
                str(finding.total),
                f"{finding.score:.1f}%",
                threshold_flag_cell(finding.above_threshold),
            )
            for finding in report.findings
        ],
    )


def print_dry_report(report: DryReport, console: Console) -> None:
    """Render an advisory DRY duplication report."""
    print_advisory_header(console, title="DRY analysis")
    console.print(report.summary)

    print_findings_table(
        console,
        title="Potential duplicate functions",
        rows=[
            (
                finding.qualified_name,
                finding.filepath,
                f"{finding.duplicate_of} ({finding.duplicate_filepath})",
                f"{finding.similarity_score:.2f}",
                f"{finding.start_line}-{finding.end_line}",
            )
            for finding in sorted(
                report.findings,
                key=lambda item: (-item.similarity_score, item.filepath, item.qualified_name),
            )
        ],
        columns=(
            ("Function", None),
            ("File", None),
            ("Duplicate of", None),
            ("Score", "right"),
            ("Lines", "right"),
        ),
    )


def print_check_report(report: CheckReport, console: Console) -> None:
    """Render a combined quality gate report."""
    if report.status == ReportStatus.PASS:
        label = "PASS"
    elif report.status == ReportStatus.ERROR:
        label = "ERROR"
    else:
        label = "FAIL"
    print_status_header(
        console,
        title="Quality gate",
        status=report.status,
        label=label,
    )
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


def print_gherkin_lint_report(report: GherkinLintReport, console: Console) -> None:
    """Render a human-readable Gherkin lint report."""
    print_status_header(console, title="Gherkin lint", status=report.status)
    console.print(report.summary)
    print_findings_table(
        console,
        title="Lint findings",
        columns=(
            ("Rule", None),
            ("Sev", None),
            ("File", None),
            ("Scenario", None),
            ("Line", "right"),
            ("Message", None),
        ),
        rows=[
            (
                finding.rule,
                finding.severity,
                finding.filepath,
                finding.scenario_name,
                str(finding.start_line),
                finding.message,
            )
            for finding in report.findings
        ],
    )


def print_gherkin_inventory_report(report: GherkinInventoryReport, console: Console) -> None:
    """Render a human-readable Gherkin inventory."""
    print_status_header(console, title="Gherkin inventory", status=report.status)
    console.print(report.summary)
    print_findings_table(
        console,
        title="Scenarios",
        columns=(
            ("File", None),
            ("Scenario", None),
            ("Kind", None),
            ("Examples", "center"),
            ("Tags", None),
            ("Lines", "right"),
        ),
        rows=[
            (
                item.filepath,
                item.name,
                item.kind,
                "yes" if item.has_examples else "no",
                " ".join(item.tags),
                f"{item.start_line}-{item.end_line}",
            )
            for item in report.scenarios
        ],
    )


def print_gherkin_validate_steps_report(
    report: GherkinValidateStepsReport,
    console: Console,
) -> None:
    """Render a human-readable undefined-step report."""
    print_status_header(console, title="Gherkin validate-steps", status=report.status)
    console.print(report.summary)
    print_findings_table(
        console,
        title="Undefined steps",
        columns=(
            ("File", None),
            ("Scenario", None),
            ("Line", "right"),
            ("Step", None),
        ),
        rows=[
            (
                finding.filepath,
                finding.scenario_name,
                str(finding.start_line),
                finding.step or finding.message,
            )
            for finding in report.findings
        ],
    )


def print_gherkin_mutation_report(report: GherkinMutationReport, console: Console) -> None:
    """Render a human-readable Gherkin mutation report."""
    print_status_header(console, title="Gherkin mutation", status=report.status)
    console.print(report.summary)
    print_skipped_unchanged(
        console,
        count=len(report.skipped_unchanged),
        entity_label="scenario(s)",
    )

    print_findings_table(
        console,
        title="Scenario mutation scores",
        columns=(
            ("Scenario", None),
            ("Killed", "right"),
            ("Total", "right"),
            ("Score", "right"),
            ("Flag", "center"),
        ),
        rows=[
            (
                finding.scenario_id,
                str(finding.killed),
                str(finding.total),
                f"{finding.score:.1f}%",
                threshold_flag_cell(finding.above_threshold),
            )
            for finding in report.findings
        ],
    )
