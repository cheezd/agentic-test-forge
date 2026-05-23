"""Tests for advisory DRY duplication detection."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.analysis.dry import analyze_dry


def test_analyze_dry_detects_duplicate_function_bodies(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "a.py").write_text(
        """
def duplicate(x):
    return x + 1
""".strip(),
        encoding="utf-8",
    )
    (package / "b.py").write_text(
        """
def also_duplicate(x):
    return x + 1
""".strip(),
        encoding="utf-8",
    )

    report = analyze_dry(["src"], search_root=tmp_path)

    assert report.status == "pass"
    assert report.advisory is True
    assert len(report.findings) == 1
    assert report.findings[0].duplicate_of in {"duplicate", "also_duplicate"}


def test_analyze_dry_reports_clean_when_no_duplicates(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "only.py").write_text(
        """
def unique(value):
    return value * 2
""".strip(),
        encoding="utf-8",
    )

    report = analyze_dry(["src"], search_root=tmp_path)

    assert report.findings == ()
    assert "No duplicate" in report.summary
