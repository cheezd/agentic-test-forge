"""Gherkin mutation analysis orchestration."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.config.models import GherkinRunner
from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    MutationManifest,
    gherkin_manifest_path,
    load_manifest,
    save_manifest,
    utc_now_iso,
)
from agentic_test_forge.mutation.gherkin.mutator import ScenarioMutator
from agentic_test_forge.mutation.gherkin.parser import GherkinScenario, scenario_content_hash
from agentic_test_forge.mutation.gherkin.report import (
    GherkinFinding,
    GherkinMutationReport,
    build_gherkin_mutation_report,
)
from agentic_test_forge.mutation.gherkin.scope import resolve_gherkin_scope
from agentic_test_forge.scope import resolve_search_root


def evaluate_scenario(
    scenario: GherkinScenario,
    *,
    project_root: Path,
    test_cmd: str,
    runner: GherkinRunner,
    threshold: float,
    run_tests: bool,
) -> GherkinFinding:
    """Evaluate one scenario by delegating to ``ScenarioMutator``."""
    mutator = ScenarioMutator(
        project_root=project_root,
        test_cmd=test_cmd,
        runner=runner,
        run_tests=run_tests,
    )
    return mutator.apply_and_test(scenario, threshold=threshold)


def analyze_gherkin_mutation(
    paths: list[str | Path],
    *,
    threshold: float,
    base_ref: str = "main",
    manifest_dir: str = ".forge",
    search_root: Path | None = None,
    full_run: bool = False,
    test_cmd: str = "behave",
    runner: GherkinRunner = "behave",
    run_tests: bool = True,
) -> GherkinMutationReport:
    """Run differential Gherkin mutation analysis and return a structured report."""
    root = resolve_search_root(search_root)
    scope = resolve_gherkin_scope(
        paths,
        base_ref=base_ref,
        search_root=root,
        manifest_dir=manifest_dir,
        full_run=full_run,
    )

    skipped = tuple(scenario.scenario_id for scenario in scope.skipped_unchanged)

    if not scope.selected:
        return build_gherkin_mutation_report(
            threshold=threshold,
            findings=[],
            skipped_unchanged=list(skipped),
            selected_count=0,
        )

    mutator = ScenarioMutator(
        project_root=root,
        test_cmd=test_cmd,
        runner=runner,
        run_tests=run_tests,
    )
    findings: list[GherkinFinding] = []
    for scenario in scope.selected:
        findings.append(mutator.apply_and_test(scenario, threshold=threshold))

    report = build_gherkin_mutation_report(
        threshold=threshold,
        findings=findings,
        skipped_unchanged=list(skipped),
        selected_count=len(scope.selected),
    )

    manifest = load_manifest(gherkin_manifest_path(manifest_dir))
    updated_files = dict(manifest.files)
    timestamp = utc_now_iso()
    for scenario, finding in zip(scope.selected, findings, strict=True):
        updated_files[scenario.scenario_id] = FileManifestEntry(
            content_hash=scenario_content_hash(scenario.block_text),
            score=finding.score,
            last_run=timestamp,
        )
    save_manifest(gherkin_manifest_path(manifest_dir), MutationManifest(files=updated_files))

    return report
