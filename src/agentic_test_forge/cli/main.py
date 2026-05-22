"""Typer CLI for agentic-test-forge."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from agentic_test_forge.analysis.crap import CoverageDataMissingError, analyze_crap
from agentic_test_forge.config import load_config
from agentic_test_forge.mutation.code import (
    GitScopeError,
    MutationUnavailableError,
    MutmutRunError,
    analyze_mutation,
)
from agentic_test_forge.mutation.gherkin import (
    GherkinRunError,
    analyze_gherkin_mutation,
)
from agentic_test_forge.orchestration import run_quality_check
from agentic_test_forge.reporting.console import (
    print_check_report,
    print_crap_report,
    print_gherkin_mutation_report,
    print_mutation_report,
)

app = typer.Typer(
    name="forge",
    help="Quality workflow tools for Python (CRAP, mutation, Gherkin gates).",
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.command()
def crap(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="CRAP score threshold (overrides config).",
    ),
    path: str = typer.Option("src/", "--path", help="Path to analyze."),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
    coverage_file: str = typer.Option(
        ".coverage",
        "--coverage-file",
        help="Path to coverage.py data file.",
    ),
) -> None:
    """Analyze cyclomatic complexity and coverage (CRAP scores)."""
    config = load_config()
    effective_threshold = threshold if threshold is not None else config.crap_threshold

    try:
        report = analyze_crap(
            [path],
            threshold=effective_threshold,
            formula=config.crap_formula,
            coverage_file=coverage_file,
        )
    except CoverageDataMissingError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    print_crap_report(report, console)

    if json_output:
        Path(json_output).write_text(report.to_json(), encoding="utf-8")
        console.print(f"JSON report written to [bold]{json_output}[/bold]")

    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command()
def mutate(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="Mutation score threshold percentage (overrides config).",
    ),
    path: str = typer.Option("src/", "--path", help="Path roots to analyze."),
    base: str | None = typer.Option(
        None,
        "--base",
        help="Git ref for differential diff (overrides config).",
    ),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Ignore manifest skip logic and mutate all scoped Python files.",
    ),
) -> None:
    """Run differential code mutation testing (mutmut)."""
    config = load_config()
    effective_threshold = threshold if threshold is not None else config.mutation_threshold
    effective_base = base if base is not None else config.mutation_base_ref

    try:
        report = analyze_mutation(
            [path],
            threshold=effective_threshold,
            base_ref=effective_base,
            manifest_dir=config.manifest_dir,
            full_run=full,
            test_cmd=config.mutation_test_cmd,
        )
    except (GitScopeError, MutationUnavailableError, MutmutRunError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    print_mutation_report(report, console)

    if json_output:
        Path(json_output).write_text(report.to_json(), encoding="utf-8")
        console.print(f"JSON report written to [bold]{json_output}[/bold]")

    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("check")
def check_cmd(
    path: str = typer.Option("src/", "--path", help="Path roots for CRAP and code mutation."),
    features_path: str = typer.Option(
        "features/",
        "--features-path",
        help="Path to .feature files for Gherkin mutation gate.",
    ),
    coverage_file: str = typer.Option(
        ".coverage",
        "--coverage-file",
        help="Path to coverage.py data file for CRAP gate.",
    ),
    base: str | None = typer.Option(
        None,
        "--base",
        help="Git ref for differential mutation scope (overrides config).",
    ),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Ignore manifest skip logic for mutation gates.",
    ),
) -> None:
    """Run the full quality gate (CRAP -> mutation -> Gherkin)."""
    config = load_config()
    report = run_quality_check(
        config,
        paths=[path],
        gherkin_paths=[features_path],
        coverage_file=coverage_file,
        base_ref=base,
        full_run=full,
    )

    print_check_report(report, console)

    if json_output:
        Path(json_output).write_text(report.to_json(), encoding="utf-8")
        console.print(f"JSON report written to [bold]{json_output}[/bold]")

    if report.errors:
        for error in report.errors:
            console.print(f"[red]Error:[/red] {error}")
        raise typer.Exit(code=2)

    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("mutate-gherkin")
def mutate_gherkin(
    path: str = typer.Option("features/", "--path", help="Path to .feature files."),
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="Mutation score threshold percentage (overrides config).",
    ),
    base: str | None = typer.Option(
        None,
        "--base",
        help="Git ref for differential diff (overrides config).",
    ),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Ignore manifest skip logic and mutate all scoped scenarios.",
    ),
) -> None:
    """Mutate Gherkin Examples and run acceptance tests."""
    config = load_config()
    effective_threshold = threshold if threshold is not None else config.gherkin_threshold
    effective_base = base if base is not None else config.gherkin_base_ref

    try:
        report = analyze_gherkin_mutation(
            [path],
            threshold=effective_threshold,
            base_ref=effective_base,
            manifest_dir=config.manifest_dir,
            full_run=full,
            test_cmd=config.gherkin_test_cmd,
            runner=config.gherkin_runner,
        )
    except (GitScopeError, GherkinRunError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    print_gherkin_mutation_report(report, console)

    if json_output:
        Path(json_output).write_text(report.to_json(), encoding="utf-8")
        console.print(f"JSON report written to [bold]{json_output}[/bold]")

    if report.status == "fail":
        raise typer.Exit(code=1)


def run() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    run()
