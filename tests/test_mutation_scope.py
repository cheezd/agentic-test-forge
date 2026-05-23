"""Tests for git-scoped mutation file selection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    MutationManifest,
    file_content_hash,
    manifest_path,
    save_manifest,
)
from agentic_test_forge.mutation.code.scope import resolve_mutation_scope
from agentic_test_forge.scope import GitScopeError


def test_resolve_scope_uses_git_diff(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    changed = src / "changed.py"
    changed.write_text("x = 1\n", encoding="utf-8")
    (src / "ignored.py").write_text("y = 2\n", encoding="utf-8")

    with patch(
        "agentic_test_forge.mutation.code.scope.run_git_diff_names",
        return_value=["src/changed.py"],
    ):
        scope = resolve_mutation_scope(["src"], base_ref="main", search_root=tmp_path)

    assert scope.selected == (changed.resolve(),)
    assert scope.skipped_unchanged == ()


def test_resolve_scope_skips_unchanged_manifest_entries(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    module = src / "module.py"
    module.write_text("value = 1\n", encoding="utf-8")

    save_manifest(
        manifest_path(tmp_path / ".forge"),
        MutationManifest(
            files={
                "src/module.py": FileManifestEntry(
                    content_hash=file_content_hash(module),
                    score=100.0,
                    last_run="2026-05-22T12:00:00+00:00",
                ),
            },
        ),
    )

    with patch(
        "agentic_test_forge.mutation.code.scope.run_git_diff_names",
        return_value=["src/module.py"],
    ):
        scope = resolve_mutation_scope(
            ["src"],
            base_ref="main",
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
        )

    assert scope.selected == ()
    assert scope.skipped_unchanged == (module.resolve(),)


def test_resolve_scope_full_run_ignores_git(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    module = src / "module.py"
    module.write_text("value = 1\n", encoding="utf-8")

    with patch(
        "agentic_test_forge.mutation.code.scope.run_git_diff_names",
        side_effect=AssertionError("git should not run"),
    ):
        scope = resolve_mutation_scope(
            ["src"],
            base_ref="main",
            search_root=tmp_path,
            full_run=True,
        )

    assert scope.selected == (module.resolve(),)


def test_resolve_scope_raises_when_git_missing(tmp_path: Path) -> None:
    with (
        patch(
            "agentic_test_forge.mutation.code.scope.run_git_diff_names",
            side_effect=GitScopeError("git diff failed"),
        ),
        pytest.raises(GitScopeError),
    ):
        resolve_mutation_scope(["src"], base_ref="main", search_root=tmp_path)
