"""Tests for mutation report parsing."""

from __future__ import annotations

import json
from pathlib import Path

from agentic_test_forge.mutation.code.report import (
    build_findings_from_meta,
    build_mutation_report,
    compute_mutation_score,
    parse_mutmut_meta,
)


def test_compute_mutation_score() -> None:
    assert compute_mutation_score(8, 10) == 80.0
    assert compute_mutation_score(0, 0) == 100.0


def test_parse_mutmut_meta(tmp_path: Path) -> None:
    meta = tmp_path / "sample.meta"
    meta.write_text(
        json.dumps(
            {
                "exit_code_by_key": {
                    "module.fn1": 1,
                    "module.fn2": 0,
                    "module.fn3": None,
                },
                "durations_by_key": {},
                "estimated_durations_by_key": {},
                "type_check_error_by_key": {},
            },
        ),
        encoding="utf-8",
    )

    killed, total = parse_mutmut_meta(meta)
    assert killed == 1
    assert total == 2


def test_build_findings_from_meta(tmp_path: Path) -> None:
    relative = Path("src/sample.py")
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text("def sample():\n    return 1\n", encoding="utf-8")

    meta_dir = tmp_path / "mutants" / "src"
    meta_dir.mkdir(parents=True)
    meta = meta_dir / "sample.py.meta"
    meta.write_text(
        json.dumps(
            {
                "exit_code_by_key": {"sample.sample": 1, "sample.sample2": 0},
                "durations_by_key": {},
                "estimated_durations_by_key": {},
                "type_check_error_by_key": {},
            },
        ),
        encoding="utf-8",
    )

    findings = build_findings_from_meta(tmp_path, [source], threshold=80.0)
    assert findings[0].filepath == "src/sample.py"
    assert findings[0].score == 50.0
    assert findings[0].above_threshold is True


def test_build_mutation_report_passes_when_no_files_selected() -> None:
    report = build_mutation_report(
        threshold=80.0,
        findings=[],
        skipped_unchanged=[],
        selected_count=0,
    )
    assert report.status == "pass"
