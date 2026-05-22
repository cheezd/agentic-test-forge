"""Quality gate orchestration for ``forge check``."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.analysis.crap import CoverageDataMissingError, analyze_crap
from agentic_test_forge.config.models import ForgeConfig
from agentic_test_forge.mutation.code import (
    GitScopeError,
    MutationUnavailableError,
    MutmutRunError,
    analyze_mutation,
)
from agentic_test_forge.mutation.gherkin import GherkinRunError, analyze_gherkin_mutation
from agentic_test_forge.orchestration.report import CheckReport, build_check_report


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

    if config.gates.crap:
        gates_run.append("crap")
        try:
            crap_report = analyze_crap(
                source_paths,
                threshold=config.crap_threshold,
                formula=config.crap_formula,
                coverage_file=coverage_file,
                search_root=root,
            )
        except CoverageDataMissingError as exc:
            errors.append(f"crap: {exc}")

    if config.gates.mutation:
        gates_run.append("mutation")
        try:
            mutation_report = analyze_mutation(
                source_paths,
                threshold=config.mutation_threshold,
                base_ref=effective_base,
                manifest_dir=config.manifest_dir,
                search_root=root,
                full_run=full_run,
            )
        except (GitScopeError, MutationUnavailableError, MutmutRunError) as exc:
            errors.append(f"mutation: {exc}")

    if config.gates.gherkin:
        gates_run.append("gherkin")
        gherkin_base = base_ref if base_ref is not None else config.gherkin_base_ref
        try:
            gherkin_report = analyze_gherkin_mutation(
                feature_paths,
                threshold=config.gherkin_threshold,
                base_ref=gherkin_base,
                manifest_dir=config.manifest_dir,
                search_root=root,
                full_run=full_run,
                test_cmd=config.gherkin_test_cmd,
                runner=config.gherkin_runner,
            )
        except (GitScopeError, GherkinRunError) as exc:
            errors.append(f"gherkin: {exc}")

    return build_check_report(
        gates_run=gates_run,
        crap=crap_report,
        mutation=mutation_report,
        gherkin=gherkin_report,
        errors=errors,
    )
