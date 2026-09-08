"""Typer CLI for agentic-test-forge."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console

from agentic_test_forge.analysis.crap import analyze_crap
from agentic_test_forge.analysis.dry import analyze_dry
from agentic_test_forge.cli.helpers import (
    cli_path_list,
    effective_override,
    optional_cli_paths,
    run_check_command,
    run_report_command,
)
from agentic_test_forge.config import load_config
from agentic_test_forge.mutation.code import analyze_mutation
from agentic_test_forge.mutation.gherkin import analyze_gherkin_mutation
from agentic_test_forge.mutation.gherkin.inventory import analyze_gherkin_inventory
from agentic_test_forge.mutation.gherkin.lint import analyze_gherkin_lint
from agentic_test_forge.mutation.gherkin.validate_steps import analyze_gherkin_validate_steps
from agentic_test_forge.orchestration import run_quality_check
from agentic_test_forge.reporting.console import (
    print_crap_report,
    print_dry_report,
    print_gherkin_inventory_report,
    print_gherkin_lint_report,
    print_gherkin_mutation_report,
    print_gherkin_validate_steps_report,
    print_mutation_report,
)

app = typer.Typer(
    name="forge",
    help="Quality workflow tools for Python (CRAP, mutation, Gherkin gates).",
    no_args_is_help=True,
)
gherkin_app = typer.Typer(
    help="Static Gherkin preflight: lint, inventory, validate-steps.",
    no_args_is_help=True,
)
app.add_typer(gherkin_app, name="gherkin")
console = Console(stderr=True)


@app.command()
def crap(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="CRAP score threshold (overrides config).",
    ),
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Path to analyze. Repeat for multiple. Defaults to [tool.forge].paths.",
        ),
    ] = None,
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
    run_report_command(
        analyze=lambda: analyze_crap(
            cli_path_list(path, config.paths),
            threshold=effective_override(threshold, config.crap_threshold),
            formula=config.crap_formula,
            coverage_file=coverage_file,
        ),
        print_report=print_crap_report,
        console=console,
        json_output=json_output,
    )


@app.command()
def dry(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="Jaccard similarity threshold (overrides config).",
    ),
    min_lines: int | None = typer.Option(
        None,
        "--min-lines",
        help="Minimum source lines per function (overrides config).",
    ),
    min_nodes: int | None = typer.Option(
        None,
        "--min-nodes",
        help="Minimum normalized AST nodes per function (overrides config).",
    ),
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Path to analyze. Repeat for multiple. Defaults to [tool.forge].paths.",
        ),
    ] = None,
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
) -> None:
    """Analyze structural duplicate function candidates (advisory)."""
    config = load_config()
    run_report_command(
        analyze=lambda: analyze_dry(
            cli_path_list(path, config.paths),
            threshold=effective_override(threshold, config.dry_threshold),
            min_lines=effective_override(min_lines, config.dry_min_lines),
            min_nodes=effective_override(min_nodes, config.dry_min_nodes),
        ),
        print_report=print_dry_report,
        console=console,
        json_output=json_output,
    )


@app.command()
def mutate(
    threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="Mutation score threshold percentage (overrides config).",
    ),
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Path roots to analyze. Repeat for multiple. Defaults to [tool.forge].paths.",
        ),
    ] = None,
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
    run_report_command(
        analyze=lambda: analyze_mutation(
            cli_path_list(path, config.paths),
            threshold=effective_override(threshold, config.mutation_threshold),
            base_ref=effective_override(base, config.mutation_base_ref),
            manifest_dir=config.manifest_dir,
            full_run=full,
            test_cmd=config.mutation_test_cmd,
        ),
        print_report=print_mutation_report,
        console=console,
        json_output=json_output,
    )


@app.command("check")
def check(
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Path roots for CRAP and mutation. Repeat for multiple. Defaults to config paths.",
        ),
    ] = None,
    features_path: Annotated[
        list[str] | None,
        typer.Option(
            "--features-path",
            help="Feature paths. Repeat for multiple. Defaults to [tool.forge].gherkin_paths.",
        ),
    ] = None,
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
    run_check_command(
        analyze=lambda: run_quality_check(
            config,
            paths=optional_cli_paths(path),
            gherkin_paths=optional_cli_paths(features_path),
            coverage_file=coverage_file,
            base_ref=base,
            full_run=full,
        ),
        console=console,
        json_output=json_output,
    )


@app.command("mutate-gherkin")
def mutate_gherkin(
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Feature paths. Repeat for multiple. Defaults to [tool.forge].gherkin_paths.",
        ),
    ] = None,
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
    run_report_command(
        analyze=lambda: analyze_gherkin_mutation(
            cli_path_list(path, config.gherkin_paths),
            threshold=effective_override(threshold, config.gherkin_threshold),
            base_ref=effective_override(base, config.gherkin_base_ref),
            manifest_dir=config.manifest_dir,
            full_run=full,
            test_cmd=config.gherkin_test_cmd,
            runner=config.gherkin_runner,
        ),
        print_report=print_gherkin_mutation_report,
        console=console,
        json_output=json_output,
    )


@gherkin_app.command("lint")
def gherkin_lint(
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Feature paths. Repeat for multiple. Defaults to [tool.forge].gherkin_paths.",
        ),
    ] = None,
    require_tags: bool = typer.Option(
        False,
        "--require-tags",
        help="Fail scenarios that have no tags.",
    ),
    flag_implementation_leakage: bool = typer.Option(
        False,
        "--flag-implementation-leakage",
        help="Warn when steps look like class or module names.",
    ),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
) -> None:
    """Lint feature files for mutation-unready or inconsistent specs."""
    config = load_config()
    run_report_command(
        analyze=lambda: analyze_gherkin_lint(
            cli_path_list(path, config.gherkin_paths),
            require_tags=require_tags,
            flag_implementation_leakage=flag_implementation_leakage,
        ),
        print_report=print_gherkin_lint_report,
        console=console,
        json_output=json_output,
    )


@gherkin_app.command("inventory")
def gherkin_inventory(
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Feature paths. Repeat for multiple. Defaults to [tool.forge].gherkin_paths.",
        ),
    ] = None,
    base: str | None = typer.Option(
        None,
        "--base",
        help="Git ref; list scenarios only in files changed vs this ref.",
    ),
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON inventory to this file.",
    ),
) -> None:
    """List scenarios for sign-off packets (human table or --json)."""
    config = load_config()
    run_report_command(
        analyze=lambda: analyze_gherkin_inventory(
            cli_path_list(path, config.gherkin_paths),
            base_ref=base,
        ),
        print_report=print_gherkin_inventory_report,
        console=console,
        json_output=json_output,
    )


@gherkin_app.command("validate-steps")
def gherkin_validate_steps(
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Feature paths. Repeat for multiple. Defaults to [tool.forge].gherkin_paths.",
        ),
    ] = None,
    steps_path: Annotated[
        list[str] | None,
        typer.Option(
            "--steps-path",
            help="Step-definition paths. Repeat for multiple. Defaults to <features>/steps/.",
        ),
    ] = None,
    json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
) -> None:
    """Report feature steps that have no matching step-definition pattern."""
    config = load_config()
    run_report_command(
        analyze=lambda: analyze_gherkin_validate_steps(
            cli_path_list(path, config.gherkin_paths),
            steps_paths=optional_cli_paths(steps_path),
        ),
        print_report=print_gherkin_validate_steps_report,
        console=console,
        json_output=json_output,
    )


def run() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    run()
