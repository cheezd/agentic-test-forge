"""Typer CLI for agentic-test-forge."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="forge",
    help="Quality workflow tools for Python (CRAP, mutation, Gherkin gates).",
    no_args_is_help=True,
)
console = Console(stderr=True)

NOT_IMPLEMENTED_EXIT = 2


def _not_implemented(feature: str, phase: str) -> None:
    console.print(
        f"[yellow]{feature}[/yellow] is not implemented yet (planned: {phase}).",
    )
    raise typer.Exit(code=NOT_IMPLEMENTED_EXIT)


@app.command()
def crap(
    _threshold: float | None = typer.Option(
        None,
        "--threshold",
        help="CRAP score threshold (overrides config).",
    ),
    _path: str = typer.Option("src/", "--path", help="Path to analyze."),
) -> None:
    """Analyze cyclomatic complexity and coverage (CRAP scores)."""
    _not_implemented("CRAP analyzer", "Phase 2")


@app.command("check")
def check_cmd(
    _json_output: str | None = typer.Option(
        None,
        "--json",
        help="Write structured JSON report to this file.",
    ),
) -> None:
    """Run the full quality gate (coverage -> CRAP -> mutation)."""
    _not_implemented("Quality gate orchestrator", "Phase 5")


@app.command("mutate-gherkin")
def mutate_gherkin(
    _features: str = typer.Argument("features/", help="Path to .feature files."),
) -> None:
    """Mutate Gherkin Examples and run acceptance tests."""
    _not_implemented("Gherkin mutation", "Phase 4")


def run() -> None:
    """Console script entrypoint."""
    app()


if __name__ == "__main__":
    run()
