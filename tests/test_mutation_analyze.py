"""Tests for analyze_mutation orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from agentic_test_forge.mutation.code.analyze import analyze_mutation
from agentic_test_forge.mutation.code.report import MutationFinding, MutationReport
from agentic_test_forge.mutation.code.scope import ScopeResult


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
