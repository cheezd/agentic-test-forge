"""Tests for analyze_mutation orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agentic_test_forge.manifest.store import (
    FileManifestEntry,
    ForgeManifest,
    load_manifest,
    manifest_path,
)
from agentic_test_forge.mutation.code.analyze import (
    _manifest_entry_for_finding,
    _persist_mutation_manifest,
    _selected_relative_paths,
    _updated_manifest_files,
    analyze_mutation,
)
from agentic_test_forge.mutation.code.report import MutationFinding, MutationReport
from agentic_test_forge.mutation.code.scope import ScopeResult


def test_selected_relative_paths_uses_posix_paths(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")
    scope = ScopeResult(selected=(module.resolve(),), skipped_unchanged=(), base_ref="main")

    assert _selected_relative_paths(scope, tmp_path) == ["src/sample.py"]


def test_manifest_entry_for_finding_skips_missing_files(tmp_path: Path) -> None:
    finding = MutationFinding(
        filepath="src/missing.py",
        score=50.0,
        killed=1,
        total=2,
        above_threshold=True,
    )

    entry = _manifest_entry_for_finding(tmp_path, finding, timestamp="2026-05-23T00:00:00Z")

    assert entry is None


def test_manifest_entry_for_finding_builds_entry_from_file(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")
    finding = MutationFinding(
        filepath="src/sample.py",
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )
    timestamp = "2026-05-23T00:00:00Z"

    entry = _manifest_entry_for_finding(tmp_path, finding, timestamp=timestamp)

    assert entry is not None
    assert entry.score == 100.0
    assert entry.last_run == timestamp
    assert entry.content_hash


def test_updated_manifest_files_preserves_existing_entries(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")
    finding = MutationFinding(
        filepath="src/sample.py",
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )
    legacy = FileManifestEntry(content_hash="abc", score=1.0, last_run="old")
    manifest = ForgeManifest(files={"legacy.py": legacy})
    timestamp = "2026-05-23T00:00:00Z"

    updated = _updated_manifest_files(manifest, [finding], root=tmp_path, timestamp=timestamp)

    assert updated["legacy.py"] == legacy
    assert updated["src/sample.py"].score == 100.0
    assert updated["src/sample.py"].last_run == timestamp


def test_persist_mutation_manifest_writes_json(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")
    finding = MutationFinding(
        filepath="src/sample.py",
        score=100.0,
        killed=1,
        total=1,
        above_threshold=False,
    )
    manifest_dir = str(tmp_path / ".forge")

    _persist_mutation_manifest(root=tmp_path, findings=[finding], manifest_dir=manifest_dir)

    manifest = load_manifest(manifest_path(manifest_dir))
    assert manifest.files["src/sample.py"].score == 100.0


def test_analyze_mutation_without_selected_files(tmp_path: Path) -> None:
    scope = ScopeResult(selected=(), skipped_unchanged=(), base_ref="main")
    with patch(
        "agentic_test_forge.mutation.code.analyze.resolve_mutation_scope",
        return_value=scope,
    ):
        report = analyze_mutation(["src"], threshold=80, search_root=tmp_path)

    assert report.status == "pass"
    assert "No changed Python files" in report.summary


def test_analyze_mutation_skips_mutmut_when_disabled(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")

    scope = ScopeResult(selected=(module.resolve(),), skipped_unchanged=(), base_ref="main")
    finding = MutationFinding(
        filepath="src/sample.py",
        score=100.0,
        killed=2,
        total=2,
        above_threshold=False,
    )
    expected = MutationReport(
        tool="mutation",
        status="pass",
        threshold=80.0,
        findings=(finding,),
        summary="All 1 mutated file(s) meet mutation threshold 80.0% (aggregate score 100.0%).",
    )

    with (
        patch(
            "agentic_test_forge.mutation.code.analyze.resolve_mutation_scope",
            return_value=scope,
        ),
        patch(
            "agentic_test_forge.mutation.code.analyze.run_mutmut",
        ) as run_mock,
        patch(
            "agentic_test_forge.mutation.code.analyze.build_findings_from_meta",
            return_value=[finding],
        ),
        patch(
            "agentic_test_forge.mutation.code.analyze.build_mutation_report",
            return_value=expected,
        ),
    ):
        report = analyze_mutation(
            ["src"],
            threshold=80,
            search_root=tmp_path,
            run_mutmut_tool=False,
        )

    run_mock.assert_not_called()
    assert report.status == "pass"


def test_analyze_mutation_runs_mutmut_and_updates_manifest(tmp_path: Path) -> None:
    module = tmp_path / "src" / "sample.py"
    module.parent.mkdir(parents=True)
    module.write_text("def sample():\n    return 1\n", encoding="utf-8")

    scope = ScopeResult(selected=(module.resolve(),), skipped_unchanged=(), base_ref="main")
    finding = MutationFinding(
        filepath="src/sample.py",
        score=100.0,
        killed=1,
        total=1,
        above_threshold=False,
    )

    with (
        patch(
            "agentic_test_forge.mutation.code.analyze.resolve_mutation_scope",
            return_value=scope,
        ),
        patch(
            "agentic_test_forge.mutation.code.analyze.run_mutmut",
        ) as run_mock,
        patch(
            "agentic_test_forge.mutation.code.analyze.build_findings_from_meta",
            return_value=[finding],
        ),
    ):
        report = analyze_mutation(
            ["src"],
            threshold=80,
            search_root=tmp_path,
            manifest_dir=str(tmp_path / ".forge"),
        )

    run_mock.assert_called_once()
    assert run_mock.call_args.kwargs["relative_paths"] == ["src/sample.py"]
    assert report.status == "pass"
    manifest_file = tmp_path / ".forge" / "mutation-manifest.json"
    assert manifest_file.is_file()
