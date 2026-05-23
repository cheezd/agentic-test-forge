"""Tests for advisory DRY duplication detection."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.analysis.dry import (
    DuplicatePair,
    _find_duplicate_pairs,
    _finding_from_duplicate_pair,
    _pairs_from_fingerprint_entries,
    analyze_dry,
)


def test_duplicate_pair_normalized_is_symmetric() -> None:
    forward = DuplicatePair("alpha", "a.py", "beta", "b.py")
    reverse = forward.reverse

    assert forward.normalized() == reverse.normalized()


def test_pairs_from_fingerprint_entries_emits_combinations() -> None:
    entries = [("first", "one.py"), ("second", "two.py"), ("third", "three.py")]

    pairs = _pairs_from_fingerprint_entries(entries)

    assert len(pairs) == 3
    assert pairs[0] == DuplicatePair("first", "one.py", "second", "two.py")
    assert pairs[1] == DuplicatePair("first", "one.py", "third", "three.py")
    assert pairs[2] == DuplicatePair("second", "two.py", "third", "three.py")


def test_finding_from_duplicate_pair_maps_fields() -> None:
    pair = DuplicatePair("foo", "left.py", "bar", "right.py")

    finding = _finding_from_duplicate_pair(pair)

    assert finding.qualified_name == "foo"
    assert finding.filepath == "left.py"
    assert finding.duplicate_of == "bar"
    assert finding.duplicate_filepath == "right.py"


def test_find_duplicate_pairs_dedupes_reverse_direction() -> None:
    fingerprints = {
        "same-body": [
            ("alpha", "a.py"),
            ("beta", "b.py"),
        ],
    }

    findings = _find_duplicate_pairs(fingerprints)

    assert len(findings) == 1
    assert {findings[0].qualified_name, findings[0].duplicate_of} == {"alpha", "beta"}


def test_find_duplicate_pairs_reports_all_pairs_within_fingerprint() -> None:
    fingerprints = {
        "same-body": [
            ("one", "1.py"),
            ("two", "2.py"),
            ("three", "3.py"),
        ],
    }

    findings = _find_duplicate_pairs(fingerprints)

    assert len(findings) == 3


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


def test_analyze_dry_uses_class_qualified_names(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "models.py").write_text(
        """
class Widget:
    def duplicate(self, x):
        return x + 1

    def also_duplicate(self, x):
        return x + 1
""".strip(),
        encoding="utf-8",
    )

    report = analyze_dry(["src"], search_root=tmp_path)

    assert len(report.findings) == 1
    assert report.findings[0].qualified_name.startswith("Widget.")


def test_analyze_dry_records_skipped_parse_files(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    bad_file = package / "broken.py"
    bad_file.write_text("def oops(:\n", encoding="utf-8")

    report = analyze_dry(["src"], search_root=tmp_path)

    assert str(bad_file) in report.skipped_parse_files
