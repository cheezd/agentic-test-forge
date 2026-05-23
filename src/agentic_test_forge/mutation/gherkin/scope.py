"""Resolve which Gherkin scenarios should be mutation-tested."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_test_forge.manifest.partition import partition_by_manifest_hash
from agentic_test_forge.manifest.store import (
    gherkin_manifest_path,
    load_manifest,
)
from agentic_test_forge.mutation.gherkin.parser import (
    GherkinScenario,
    parse_feature_file,
    scenario_content_hash,
)
from agentic_test_forge.scope import (
    filter_git_changed_files,
    iter_files_by_suffix,
    normalize_paths,
    resolve_search_root,
    run_git_diff_names,
)


@dataclass(frozen=True)
class GherkinScopeResult:
    """Scenarios selected for mutation and scenarios skipped by the manifest."""

    selected: tuple[GherkinScenario, ...]
    skipped_unchanged: tuple[GherkinScenario, ...]
    base_ref: str


def _scenarios_with_examples(feature_path: Path, project_root: Path) -> list[GherkinScenario]:
    return [
        scenario
        for scenario in parse_feature_file(feature_path, project_root=project_root)
        if scenario.examples is not None
    ]


def resolve_gherkin_scope(
    paths: list[str | Path],
    *,
    base_ref: str,
    search_root: Path | None = None,
    manifest_dir: str = ".forge",
    full_run: bool = False,
) -> GherkinScopeResult:
    """Return scenarios to mutate, applying git diff and manifest filters."""
    root = resolve_search_root(search_root)
    path_roots = normalize_paths([str(p) for p in paths], root)

    if full_run:
        candidate_files = iter_files_by_suffix(path_roots, ".feature")
    else:
        changed = run_git_diff_names(
            base_ref,
            root,
            context="differential gherkin scope",
        )
        candidate_files = filter_git_changed_files(
            changed,
            suffix=".feature",
            search_root=root,
            path_roots=path_roots,
        )

    manifest = load_manifest(gherkin_manifest_path(manifest_dir))
    candidates: list[GherkinScenario] = []
    for feature_path in candidate_files:
        candidates.extend(_scenarios_with_examples(feature_path, root))

    selected, skipped = partition_by_manifest_hash(
        candidates,
        key_fn=lambda scenario: scenario.scenario_id,
        hash_fn=lambda scenario: scenario_content_hash(scenario.block_text),
        manifest=manifest,
        full_run=full_run,
    )

    return GherkinScopeResult(
        selected=tuple(selected),
        skipped_unchanged=tuple(skipped),
        base_ref=base_ref,
    )
