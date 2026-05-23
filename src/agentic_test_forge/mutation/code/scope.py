"""Resolve which Python files should be mutation-tested."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_test_forge.manifest.store import (
    file_content_hash,
    load_manifest,
    manifest_path,
)
from agentic_test_forge.scope import (
    filter_git_changed_files,
    iter_files_by_suffix,
    normalize_paths,
    resolve_search_root,
    run_git_diff_names,
)


@dataclass(frozen=True)
class ScopeResult:
    """Files selected for mutation and files skipped by the manifest."""

    selected: tuple[Path, ...]
    skipped_unchanged: tuple[Path, ...]
    base_ref: str


def resolve_mutation_scope(
    paths: list[str | Path],
    *,
    base_ref: str,
    search_root: Path | None = None,
    manifest_dir: str = ".forge",
    full_run: bool = False,
) -> ScopeResult:
    """Return Python files to mutate, applying git diff and manifest filters."""
    root = resolve_search_root(search_root)
    path_roots = normalize_paths([str(p) for p in paths], root)

    if full_run:
        candidate_files = iter_files_by_suffix(path_roots, ".py")
    else:
        changed = run_git_diff_names(
            base_ref,
            root,
            context="differential mutation scope",
        )
        candidate_files = filter_git_changed_files(
            changed,
            suffix=".py",
            search_root=root,
            path_roots=path_roots,
        )

    manifest = load_manifest(manifest_path(manifest_dir))
    selected: list[Path] = []
    skipped: list[Path] = []

    for filepath in candidate_files:
        current_hash = file_content_hash(filepath)
        key = str(filepath.relative_to(root)).replace("\\", "/")
        previous = manifest.files.get(key)
        if (
            not full_run
            and previous is not None
            and previous.content_hash == current_hash
        ):
            skipped.append(filepath)
            continue
        selected.append(filepath)

    return ScopeResult(
        selected=tuple(selected),
        skipped_unchanged=tuple(skipped),
        base_ref=base_ref,
    )
