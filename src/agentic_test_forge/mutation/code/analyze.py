"""Mutation analysis orchestration."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    MutationManifest,
    file_content_hash,
    load_manifest,
    manifest_path,
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


def _skipped_relative_paths(scope: ScopeResult, root: Path) -> list[str]:
    return [to_posix_relative(path, root) for path in scope.skipped_unchanged]


def _run_mutation_tool(
    *,
    root: Path,
    scope: ScopeResult,
    run_mutmut_tool: bool,
    test_cmd: str,
) -> None:
    if not run_mutmut_tool:
        return
    relative_paths = [to_posix_relative(path, root) for path in scope.selected]
    run_mutmut(root, relative_paths=relative_paths, test_cmd=test_cmd)


def _persist_mutation_manifest(
    *,
    root: Path,
    findings: list[MutationFinding],
    manifest_dir: str,
) -> None:
    manifest = load_manifest(manifest_path(manifest_dir))
    updated_files = dict(manifest.files)
    timestamp = utc_now_iso()
    for finding in findings:
        filepath = root / finding.filepath
        if not filepath.is_file():
            continue
        updated_files[finding.filepath] = FileManifestEntry(
            content_hash=file_content_hash(filepath),
            score=finding.score,
            last_run=timestamp,
        )
    save_manifest(manifest_path(manifest_dir), MutationManifest(files=updated_files))


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
        return build_mutation_report(
            threshold=threshold,
            findings=[],
            skipped_unchanged=skipped,
            selected_count=0,
        )

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
