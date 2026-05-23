"""Quality gate orchestration for ``forge check``."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from agentic_test_forge.analysis.crap import analyze_crap
from agentic_test_forge.analysis.dry import analyze_dry
from agentic_test_forge.config.models import ForgeConfig
from agentic_test_forge.errors import ForgeToolError
from agentic_test_forge.mutation.code import analyze_mutation
from agentic_test_forge.mutation.gherkin import analyze_gherkin_mutation
from agentic_test_forge.orchestration.report import CheckReport, build_check_report

T = TypeVar("T")


def _run_blocking_gate(
    name: str,
    analyze_fn: Callable[[], T],
    *,
    gates_run: list[str],
    errors: list[str],
) -> T | None:
    """Run a gate that may raise ``ForgeToolError``; record failures in ``errors``."""
    gates_run.append(name)
    try:
        return analyze_fn()
    except ForgeToolError as exc:
        errors.append(f"{name}: {exc}")
        return None


def run_quality_check(
    config: ForgeConfig,
    *,
    paths: list[str | Path] | None = None,
    gherkin_paths: list[str | Path] | None = None,
    coverage_file: str = ".coverage",
    base_ref: str | None = None,
    full_run: bool = False,
    search_root: Path | None = None,
) -> CheckReport:
    """Run enabled quality gates and return a combined report."""
    root = (search_root or Path.cwd()).resolve()
    source_paths: list[str | Path] = list(paths if paths is not None else config.paths)
    feature_paths: list[str | Path] = list(
        gherkin_paths if gherkin_paths is not None else config.gherkin_paths
    )
    effective_base = base_ref if base_ref is not None else config.mutation_base_ref

    gates_run: list[str] = []
    errors: list[str] = []
    crap_report = None
    mutation_report = None
    gherkin_report = None
    dry_report = None

    if config.gates.dry:
        gates_run.append("dry")
        dry_report = analyze_dry(source_paths, search_root=root)

    if config.gates.crap:
        crap_report = _run_blocking_gate(
            "crap",
            lambda: analyze_crap(
                source_paths,
                threshold=config.crap_threshold,
                formula=config.crap_formula,
                coverage_file=coverage_file,
                search_root=root,
            ),
            gates_run=gates_run,
            errors=errors,
        )

    if config.gates.mutation:
        mutation_report = _run_blocking_gate(
            "mutation",
            lambda: analyze_mutation(
                source_paths,
                threshold=config.mutation_threshold,
                base_ref=effective_base,
                manifest_dir=config.manifest_dir,
                search_root=root,
                full_run=full_run,
                test_cmd=config.mutation_test_cmd,
            ),
            gates_run=gates_run,
            errors=errors,
        )

    if config.gates.gherkin:
        gherkin_base = base_ref if base_ref is not None else config.gherkin_base_ref
        gherkin_report = _run_blocking_gate(
            "gherkin",
            lambda: analyze_gherkin_mutation(
                feature_paths,
                threshold=config.gherkin_threshold,
                base_ref=gherkin_base,
                manifest_dir=config.manifest_dir,
                search_root=root,
                full_run=full_run,
                test_cmd=config.gherkin_test_cmd,
                runner=config.gherkin_runner,
            ),
            gates_run=gates_run,
            errors=errors,
        )

    return build_check_report(
        gates_run=gates_run,
        crap=crap_report,
        mutation=mutation_report,
        gherkin=gherkin_report,
        dry=dry_report,
        errors=errors,
    )
