"""Tests for git-scoped Gherkin scenario selection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    MutationManifest,
    gherkin_manifest_path,
    save_manifest,
)
from agentic_test_forge.mutation.gherkin.parser import parse_feature_file, scenario_content_hash
from agentic_test_forge.mutation.gherkin.scope import resolve_gherkin_scope
from agentic_test_forge.scope import GitScopeError


def test_resolve_gherkin_scope_uses_git_diff(tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    feature = features / "sample.feature"
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )

    with patch(
        "agentic_test_forge.mutation.gherkin.scope.run_git_diff_names",
        return_value=["features/sample.feature"],
    ):
        scope = resolve_gherkin_scope(
            ["features"],
            base_ref="main",
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
        )

    assert len(scope.selected) == 1
    assert scope.skipped_unchanged == ()


def test_resolve_gherkin_scope_skips_unchanged_manifest_entries(tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    feature = features / "sample.feature"
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )
    scenario = parse_feature_file(feature, project_root=tmp_path)[0]
    save_manifest(
        gherkin_manifest_path(tmp_path / ".forge"),
        MutationManifest(
            files={
                scenario.scenario_id: FileManifestEntry(
                    content_hash=scenario_content_hash(scenario.block_text),
                    score=100.0,
                    last_run="2026-05-22T12:00:00+00:00",
                ),
            },
        ),
    )

    with patch(
        "agentic_test_forge.mutation.gherkin.scope.run_git_diff_names",
        return_value=["features/sample.feature"],
    ):
        scope = resolve_gherkin_scope(
            ["features"],
            base_ref="main",
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
        )

    assert scope.selected == ()
    assert len(scope.skipped_unchanged) == 1


def test_resolve_gherkin_scope_full_run_ignores_git(tmp_path: Path) -> None:
    features = tmp_path / "features"
    features.mkdir()
    feature = features / "sample.feature"
    feature.write_text(
        "Feature: Demo\n\n  Scenario Outline: Add\n    Examples:\n      | x |\n      | 1 |\n",
        encoding="utf-8",
    )

    with patch(
        "agentic_test_forge.mutation.gherkin.scope.run_git_diff_names",
        side_effect=AssertionError("git should not run"),
    ):
        scope = resolve_gherkin_scope(
            ["features"],
            base_ref="main",
            search_root=tmp_path,
            full_run=True,
            manifest_dir=str(tmp_path / ".forge"),
        )

    assert len(scope.selected) == 1


def test_resolve_gherkin_scope_raises_when_git_missing(tmp_path: Path) -> None:
    with (
        patch(
            "agentic_test_forge.mutation.gherkin.scope.run_git_diff_names",
            side_effect=GitScopeError("git diff failed"),
        ),
        pytest.raises(GitScopeError),
    ):
        resolve_gherkin_scope(
            ["features"],
            base_ref="main",
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
        )
