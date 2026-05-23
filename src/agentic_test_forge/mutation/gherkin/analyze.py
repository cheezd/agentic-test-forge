"""Gherkin mutation analysis orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from agentic_test_forge.config.models import GherkinRunner
from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    ForgeManifest,
    gherkin_manifest_path,
    load_manifest,
    prune_stale_manifest_entries,
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
from agentic_test_forge.mutation.gherkin.scope import (
    GherkinScopeResult,
    collect_mutable_scenario_ids,
    resolve_gherkin_scope,
)
from agentic_test_forge.scope import resolve_search_root


def _skipped_scenario_ids(scope: GherkinScopeResult) -> list[str]:
    return [scenario.scenario_id for scenario in scope.skipped_unchanged]


def _create_scenario_mutator(
    *,
    project_root: Path,
    test_cmd: str,
    runner: GherkinRunner,
    run_tests: bool,
) -> ScenarioMutator:
    return ScenarioMutator(
        project_root=project_root,
        test_cmd=test_cmd,
        runner=runner,
        run_tests=run_tests,
    )


def _finding_for_scenario(
    mutator: ScenarioMutator,
    scenario: GherkinScenario,
    *,
    threshold: float,
) -> GherkinFinding:
    return mutator.apply_and_test(scenario, threshold=threshold)


def _findings_for_scenarios(
    mutator: ScenarioMutator,
    scenarios: Sequence[GherkinScenario],
    *,
    threshold: float,
) -> list[GherkinFinding]:
    return [
        _finding_for_scenario(mutator, scenario, threshold=threshold)
        for scenario in scenarios
    ]


def _manifest_entry_for_scenario(
    scenario: GherkinScenario,
    finding: GherkinFinding,
    *,
    timestamp: str,
) -> FileManifestEntry:
    return FileManifestEntry(
        content_hash=scenario_content_hash(scenario.block_text),
        score=finding.score,
        last_run=timestamp,
    )


def _updated_gherkin_manifest_files(
    manifest: ForgeManifest,
    scenarios: Sequence[GherkinScenario],
    findings: Sequence[GherkinFinding],
    *,
    timestamp: str,
) -> dict[str, FileManifestEntry]:
    updated_files = dict(manifest.files)
    for scenario, finding in zip(scenarios, findings, strict=True):
        updated_files[scenario.scenario_id] = _manifest_entry_for_scenario(
            scenario,
            finding,
            timestamp=timestamp,
        )
    return updated_files


def _persist_gherkin_manifest(
    *,
    paths: list[str | Path],
    root: Path,
    scenarios: Sequence[GherkinScenario],
    findings: Sequence[GherkinFinding],
    manifest_dir: str,
) -> None:
    manifest = load_manifest(gherkin_manifest_path(manifest_dir))
    timestamp = utc_now_iso()
    updated_files = _updated_gherkin_manifest_files(
        manifest,
        scenarios,
        findings,
        timestamp=timestamp,
    )
    active_scenario_ids = collect_mutable_scenario_ids(paths, search_root=root)
    pruned_files = prune_stale_manifest_entries(
        updated_files,
        key_is_valid=lambda key: key in active_scenario_ids,
    )
    save_manifest(gherkin_manifest_path(manifest_dir), ForgeManifest(files=pruned_files))


def _empty_gherkin_mutation_report(
    *,
    threshold: float,
    skipped: list[str],
) -> GherkinMutationReport:
    return build_gherkin_mutation_report(
        threshold=threshold,
        findings=[],
        skipped_unchanged=skipped,
        selected_count=0,
    )


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
    mutator = _create_scenario_mutator(
        project_root=project_root,
        test_cmd=test_cmd,
        runner=runner,
        run_tests=run_tests,
    )
    return _finding_for_scenario(mutator, scenario, threshold=threshold)


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
    skipped = _skipped_scenario_ids(scope)

    if not scope.selected:
        return _empty_gherkin_mutation_report(threshold=threshold, skipped=skipped)

    mutator = _create_scenario_mutator(
        project_root=root,
        test_cmd=test_cmd,
        runner=runner,
        run_tests=run_tests,
    )
    findings = _findings_for_scenarios(
        mutator,
        scope.selected,
        threshold=threshold,
    )
    report = build_gherkin_mutation_report(
        threshold=threshold,
        findings=findings,
        skipped_unchanged=skipped,
        selected_count=len(scope.selected),
    )
    _persist_gherkin_manifest(
        paths=paths,
        root=root,
        scenarios=scope.selected,
        findings=findings,
        manifest_dir=manifest_dir,
    )
    return report
