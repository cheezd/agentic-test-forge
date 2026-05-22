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
from agentic_test_forge.mutation.code.report import compute_mutation_score
from agentic_test_forge.mutation.gherkin.mutator import (
    apply_mutation,
    generate_example_mutations,
)
from agentic_test_forge.mutation.gherkin.parser import GherkinScenario, scenario_content_hash
from agentic_test_forge.mutation.gherkin.report import (
    GherkinFinding,
    GherkinMutationReport,
    build_gherkin_mutation_report,
)
from agentic_test_forge.mutation.gherkin.runner import run_acceptance_tests
from agentic_test_forge.mutation.gherkin.scope import resolve_gherkin_scope


def _evaluate_scenario(
    scenario: GherkinScenario,
    *,
    project_root: Path,
    test_cmd: str,
    runner: GherkinRunner,
    threshold: float,
    run_tests: bool,
) -> GherkinFinding:
    mutations = generate_example_mutations(scenario)
    if not mutations:
        return GherkinFinding(
            scenario_id=scenario.scenario_id,
            score=100.0,
            killed=0,
            total=0,
            above_threshold=False,
        )

    feature_path = project_root / scenario.filepath
    original_lines = feature_path.read_text(encoding="utf-8").splitlines()
    killed = 0

    for mutation in mutations:
        mutated_lines = apply_mutation(original_lines, scenario, mutation)
        feature_path.write_text("\n".join(mutated_lines) + "\n", encoding="utf-8")
        try:
            if run_tests:
                exit_code = run_acceptance_tests(
                    test_cmd=test_cmd,
                    runner=runner,
                    scenario=scenario,
                    project_root=project_root,
                )
            else:
                exit_code = 1
        finally:
            feature_path.write_text("\n".join(original_lines) + "\n", encoding="utf-8")

        if exit_code != 0:
            killed += 1

    total = len(mutations)
    score = compute_mutation_score(killed, total)
    return GherkinFinding(
        scenario_id=scenario.scenario_id,
        score=score,
        killed=killed,
        total=total,
        above_threshold=score < threshold,
    )


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
    root = (search_root or Path.cwd()).resolve()
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

    findings: list[GherkinFinding] = []
    for scenario in scope.selected:
        findings.append(
            _evaluate_scenario(
                scenario,
                project_root=root,
                test_cmd=test_cmd,
                runner=runner,
                threshold=threshold,
                run_tests=run_tests,
            ),
        )

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
