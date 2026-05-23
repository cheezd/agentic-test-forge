"""Mutation analysis orchestration."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    ForgeManifest,
    file_content_hash,
    load_manifest,
    manifest_path,
    prune_stale_manifest_entries,
    save_manifest,
    utc_now_iso,
)
from agentic_test_forge.mutation.code.report import (
    MutationFinding,
    MutationReport,
    build_findings_from_meta,
    build_mutation_report,
)
from agentic_test_forge.mutation.code.runner import run_mutmut
from agentic_test_forge.mutation.code.scope import ScopeResult, resolve_mutation_scope
from agentic_test_forge.scope import resolve_search_root, to_posix_relative


def _relative_paths(paths: Sequence[Path], root: Path) -> list[str]:
    return [to_posix_relative(path, root) for path in paths]


def _skipped_relative_paths(scope: ScopeResult, root: Path) -> list[str]:
    return _relative_paths(scope.skipped_unchanged, root)


def _selected_relative_paths(scope: ScopeResult, root: Path) -> list[str]:
    return _relative_paths(scope.selected, root)


def _run_mutation_tool(
    *,
    root: Path,
    scope: ScopeResult,
    run_mutmut_tool: bool,
    test_cmd: str,
) -> None:
    if not run_mutmut_tool:
        return
    run_mutmut(
        root,
        relative_paths=_selected_relative_paths(scope, root),
        test_cmd=test_cmd,
    )


def _manifest_entry_for_finding(
    root: Path,
    finding: MutationFinding,
    *,
    timestamp: str,
) -> FileManifestEntry | None:
    filepath = root / finding.filepath
    if not filepath.is_file():
        return None
    return FileManifestEntry(
        content_hash=file_content_hash(filepath),
        score=finding.score,
        last_run=timestamp,
    )


def _updated_manifest_files(
    manifest: ForgeManifest,
    findings: list[MutationFinding],
    *,
    root: Path,
    timestamp: str,
) -> dict[str, FileManifestEntry]:
    updated_files = dict(manifest.files)
    for finding in findings:
        entry = _manifest_entry_for_finding(root, finding, timestamp=timestamp)
        if entry is None:
            continue
        updated_files[finding.filepath] = entry
    return updated_files


def _persist_mutation_manifest(
    *,
    root: Path,
    findings: list[MutationFinding],
    manifest_dir: str,
) -> None:
    manifest = load_manifest(manifest_path(manifest_dir))
    timestamp = utc_now_iso()
    updated_files = _updated_manifest_files(
        manifest,
        findings,
        root=root,
        timestamp=timestamp,
    )
    pruned_files = prune_stale_manifest_entries(
        updated_files,
        key_is_valid=lambda key: (root / key).is_file(),
    )
    save_manifest(manifest_path(manifest_dir), ForgeManifest(files=pruned_files))


def _empty_mutation_report(
    *,
    threshold: float,
    skipped: list[str],
) -> MutationReport:
    return build_mutation_report(
        threshold=threshold,
        findings=[],
        skipped_unchanged=skipped,
        selected_count=0,
    )


def analyze_mutation(
    paths: list[str | Path],
    *,
    threshold: float,
    base_ref: str = "main",
    manifest_dir: str = ".forge",
    search_root: Path | None = None,
    full_run: bool = False,
    run_mutmut_tool: bool = True,
    test_cmd: str = "pytest",
) -> MutationReport:
    """Run differential mutation analysis and return a structured report."""
    root = resolve_search_root(search_root)
    scope = resolve_mutation_scope(
        paths,
        base_ref=base_ref,
        search_root=root,
        manifest_dir=manifest_dir,
        full_run=full_run,
    )
    skipped = _skipped_relative_paths(scope, root)

    if not scope.selected:
        return _empty_mutation_report(threshold=threshold, skipped=skipped)

    _run_mutation_tool(
        root=root,
        scope=scope,
        run_mutmut_tool=run_mutmut_tool,
        test_cmd=test_cmd,
    )
    findings = build_findings_from_meta(root, list(scope.selected), threshold=threshold)
    report = build_mutation_report(
        threshold=threshold,
        findings=findings,
        skipped_unchanged=skipped,
        selected_count=len(scope.selected),
    )
    _persist_mutation_manifest(root=root, findings=findings, manifest_dir=manifest_dir)
    return report
