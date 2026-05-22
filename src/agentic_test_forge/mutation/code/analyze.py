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
    MutationReport,
    build_findings_from_meta,
    build_mutation_report,
)
from agentic_test_forge.mutation.code.runner import (
    MutationUnavailableError,
    MutmutRunError,
    run_mutmut,
    temporary_mutmut_paths,
)
from agentic_test_forge.mutation.code.scope import GitScopeError, resolve_mutation_scope


def analyze_mutation(
    paths: list[str | Path],
    *,
    threshold: float,
    base_ref: str = "main",
    manifest_dir: str = ".forge",
    search_root: Path | None = None,
    full_run: bool = False,
    run_mutmut_tool: bool = True,
) -> MutationReport:
    """Run differential mutation analysis and return a structured report."""
    root = (search_root or Path.cwd()).resolve()
    scope = resolve_mutation_scope(
        paths,
        base_ref=base_ref,
        search_root=root,
        manifest_dir=manifest_dir,
        full_run=full_run,
    )

    skipped = tuple(
        str(path.relative_to(root)).replace("\\", "/")
        for path in scope.skipped_unchanged
    )

    if not scope.selected:
        return build_mutation_report(
            threshold=threshold,
            findings=[],
            skipped_unchanged=list(skipped),
            selected_count=0,
        )

    relative_paths = [
        str(path.relative_to(root)).replace("\\", "/") for path in scope.selected
    ]

    if run_mutmut_tool:
        try:
            with temporary_mutmut_paths(root, relative_paths):
                run_mutmut(root)
        except (MutationUnavailableError, MutmutRunError, GitScopeError):
            raise

    findings = build_findings_from_meta(
        root,
        list(scope.selected),
        threshold=threshold,
    )
    report = build_mutation_report(
        threshold=threshold,
        findings=findings,
        skipped_unchanged=list(skipped),
        selected_count=len(scope.selected),
    )

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

    return report
