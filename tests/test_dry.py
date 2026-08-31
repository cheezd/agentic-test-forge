"""Tests for advisory DRY duplication detection."""

from __future__ import annotations

import ast
import time
from pathlib import Path

import pytest

from agentic_test_forge.analysis.dry import (
    DEFAULT_DRY_MIN_LINES,
    DEFAULT_DRY_MIN_NODES,
    DEFAULT_DRY_THRESHOLD,
    FunctionUnit,
    SimilarPair,
    _collect_fingerprints,
    _find_similar_pairs,
    _function_unit,
    _jaccard,
    _normalize_body,
    analyze_dry,
)

# Shared structure with one extra normalized node on the right (Jaccard ~0.89).
_PARTIAL_OVERLAP_LEFT = """
def prepare(raw):
    cleaned = raw.strip()
    parsed = int(cleaned)
    scaled = parsed * 2
    bounded = min(scaled, 100)
    labeled = str(bounded)
    return labeled
""".strip()

_PARTIAL_OVERLAP_RIGHT = """
def prepare_copy(text):
    cleaned = text.strip()
    parsed = int(cleaned)
    scaled = parsed * 2
    bounded = min(scaled, 100)
    labeled = str(bounded)
    extra = labeled.lower()
    return labeled
""".strip()

_TINY_CLONE = "def tiny():\n    return 1\n"
_SHORT_CLONE = """
def padded(value):
    alias = value
    copy = alias
    return copy
""".strip() + "\n"


def _function_from_source(source: str) -> ast.FunctionDef:
    module = ast.parse(source)
    node = module.body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def _unit_from_source(source: str, *, name: str, filepath: str = "sample.py") -> FunctionUnit:
    return _function_unit(
        _function_from_source(source),
        qualified_name=name,
        filepath=Path(filepath),
    )


def _write_src_files(tmp_path: Path, files: dict[str, str]) -> Path:
    package = tmp_path / "src"
    package.mkdir()
    for relative, source in files.items():
        target = package / relative
        target.write_text(source, encoding="utf-8")
    return package


def test_normalize_renamed_locals_produce_identical_fingerprint_sets() -> None:
    left = _function_from_source("def alpha(x):\n    return x + 1")
    right = _function_from_source("def beta(item):\n    return item + 1")

    left_fps = _collect_fingerprints(_normalize_body(left))
    right_fps = _collect_fingerprints(_normalize_body(right))

    assert left_fps == right_fps


def test_normalize_constant_type_tags_differ_for_str_vs_int() -> None:
    int_body = _function_from_source("def check(n):\n    return n > 80")
    str_body = _function_from_source('def check(label):\n    return label > "80"')

    int_fps = _collect_fingerprints(_normalize_body(int_body))
    str_fps = _collect_fingerprints(_normalize_body(str_body))

    assert int_fps != str_fps


def test_normalize_attribute_attr_without_receiver_collapse() -> None:
    left = _function_from_source("def load(raw):\n    return raw.get('dry')")
    right = _function_from_source("def load(data):\n    return data.fetch('dry')")

    left_fps = _collect_fingerprints(_normalize_body(left))
    right_fps = _collect_fingerprints(_normalize_body(right))

    assert left_fps == right_fps


def test_normalize_preserves_chained_attribute_shape() -> None:
    shallow = _function_from_source("def read(obj):\n    return obj.name")
    nested = _function_from_source("def read(cfg):\n    return cfg.gates.dry")

    shallow_fps = _collect_fingerprints(_normalize_body(shallow))
    nested_fps = _collect_fingerprints(_normalize_body(nested))

    assert shallow_fps != nested_fps


def test_jaccard_identical_sets_score_one() -> None:
    left = {"a", "b", "c"}
    assert _jaccard(left, set(left)) == 1.0


def test_jaccard_disjoint_sets_score_zero() -> None:
    assert _jaccard({"a"}, {"b"}) == 0.0


def test_jaccard_empty_sets_score_one() -> None:
    assert _jaccard(set(), set()) == 1.0


def test_jaccard_partial_overlap() -> None:
    score = _jaccard({"a", "b", "c"}, {"b", "c", "d"})
    assert score == pytest.approx(0.5)


def test_similar_pair_normalized_is_symmetric() -> None:
    forward = SimilarPair("alpha", "a.py", "beta", "b.py")
    reverse = forward.reverse

    assert forward.normalized() == reverse.normalized()


def test_find_similar_pairs_respects_threshold() -> None:
    left = _unit_from_source("def alpha(x):\n    return x + 1", name="alpha", filepath="a.py")
    right = _unit_from_source("def beta(item):\n    return item + 1", name="beta", filepath="b.py")
    different = _unit_from_source(
        "def gamma(x):\n    return x * 2\n    return x + 1",
        name="gamma",
        filepath="c.py",
    )

    findings = _find_similar_pairs(
        [left, right, different],
        threshold=0.82,
        min_lines=1,
        min_nodes=1,
    )

    assert len(findings) == 1
    assert findings[0].similarity_score == 1.0
    assert {findings[0].qualified_name, findings[0].duplicate_of} == {"alpha", "beta"}


def test_find_similar_pairs_excludes_small_functions() -> None:
    tiny = _unit_from_source("def tiny():\n    return 1", name="tiny", filepath="tiny.py")
    findings = _find_similar_pairs([tiny], threshold=0.5, min_lines=4, min_nodes=20)
    assert findings == []


def test_find_similar_pairs_dedupes_reverse_direction() -> None:
    left = _unit_from_source("def alpha(x):\n    return x + 1", name="alpha", filepath="a.py")
    right = _unit_from_source("def beta(x):\n    return x + 1", name="beta", filepath="b.py")

    findings = _find_similar_pairs([left, right], threshold=0.82, min_lines=1, min_nodes=1)

    assert len(findings) == 1


def test_find_similar_pairs_sorts_by_score_descending() -> None:
    high_left = FunctionUnit("a", "1.py", frozenset({"x", "y", "z"}), 1, 3, 10, 4)
    high_right = FunctionUnit("b", "2.py", frozenset({"x", "y", "z"}), 1, 3, 10, 4)
    low_left = FunctionUnit("c", "3.py", frozenset({"x"}), 1, 3, 10, 4)
    low_right = FunctionUnit("d", "4.py", frozenset({"y"}), 1, 3, 10, 4)

    findings = _find_similar_pairs(
        [high_left, high_right, low_left, low_right],
        threshold=0.01,
        min_lines=1,
        min_nodes=1,
    )

    assert len(findings) >= 2
    assert findings[0].similarity_score == 1.0
    assert findings[0].similarity_score >= findings[-1].similarity_score


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

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)

    assert report.status == "pass"
    assert report.advisory is True
    assert len(report.findings) == 1
    assert report.findings[0].similarity_score == 1.0
    assert report.findings[0].duplicate_of in {"duplicate", "also_duplicate"}


def test_analyze_dry_detects_renamed_local_near_duplicates(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "a.py").write_text(
        """
def alpha(value):
    return value + 1
""".strip(),
        encoding="utf-8",
    )
    (package / "b.py").write_text(
        """
def beta(item):
    return item + 1
""".strip(),
        encoding="utf-8",
    )

    report = analyze_dry(["src"], search_root=tmp_path, threshold=0.82, min_lines=1, min_nodes=1)

    assert len(report.findings) == 1
    assert report.findings[0].similarity_score >= 0.82


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

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)

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

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)

    assert len(report.findings) == 1
    assert report.findings[0].qualified_name.startswith("Widget.")


def test_analyze_dry_records_skipped_parse_files(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    bad_file = package / "broken.py"
    bad_file.write_text("def oops(:\n", encoding="utf-8")

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)

    assert str(bad_file) in report.skipped_parse_files


def test_analyze_dry_finding_includes_line_ranges_and_node_count(tmp_path: Path) -> None:
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

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)
    finding = report.findings[0]

    assert finding.start_line >= 1
    assert finding.end_line >= finding.start_line
    assert finding.node_count > 0


def test_analyze_dry_json_includes_similarity_score(tmp_path: Path) -> None:
    package = tmp_path / "src"
    package.mkdir()
    (package / "a.py").write_text("def a(x):\n    return x + 1\n", encoding="utf-8")
    (package / "b.py").write_text("def b(x):\n    return x + 1\n", encoding="utf-8")

    report = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)

    assert '"similarity_score"' in report.to_json()


def test_analyze_dry_reports_partial_overlap_in_threshold_band(tmp_path: Path) -> None:
    _write_src_files(
        tmp_path,
        {"left.py": _PARTIAL_OVERLAP_LEFT, "right.py": _PARTIAL_OVERLAP_RIGHT},
    )

    report = analyze_dry(["src"], search_root=tmp_path)

    assert len(report.findings) == 1
    score = report.findings[0].similarity_score
    assert DEFAULT_DRY_THRESHOLD <= score < 1.0
    assert {report.findings[0].qualified_name, report.findings[0].duplicate_of} == {
        "prepare",
        "prepare_copy",
    }


def test_analyze_dry_partial_overlap_excluded_above_default_threshold(tmp_path: Path) -> None:
    _write_src_files(
        tmp_path,
        {"left.py": _PARTIAL_OVERLAP_LEFT, "right.py": _PARTIAL_OVERLAP_RIGHT},
    )

    report = analyze_dry(["src"], search_root=tmp_path, threshold=0.99)

    assert report.findings == ()


def test_analyze_dry_default_min_lines_excludes_tiny_clones(tmp_path: Path) -> None:
    _write_src_files(tmp_path, {"a.py": _TINY_CLONE, "b.py": _TINY_CLONE.replace("tiny", "also")})

    unfiltered = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)
    filtered = analyze_dry(["src"], search_root=tmp_path)

    assert len(unfiltered.findings) == 1
    assert unfiltered.findings[0].similarity_score == 1.0
    assert filtered.findings == ()
    assert DEFAULT_DRY_MIN_LINES == 4


def test_analyze_dry_default_min_nodes_excludes_short_clones(tmp_path: Path) -> None:
    other = _SHORT_CLONE.replace("padded", "also_padded")
    _write_src_files(tmp_path, {"a.py": _SHORT_CLONE, "b.py": other})

    unfiltered = analyze_dry(["src"], search_root=tmp_path, min_lines=1, min_nodes=1)
    filtered = analyze_dry(["src"], search_root=tmp_path)

    assert len(unfiltered.findings) == 1
    assert unfiltered.findings[0].node_count < DEFAULT_DRY_MIN_NODES
    assert filtered.findings == ()


@pytest.mark.slow
def test_analyze_dry_completes_on_repo_src_within_five_seconds() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if not src.is_dir():
        pytest.skip("src/ not present")

    start = time.perf_counter()
    report = analyze_dry(["src"], search_root=repo_root)
    elapsed = time.perf_counter() - start

    assert report.status == "pass"
    assert report.advisory is True
    assert elapsed < 5.0
    for finding in report.findings:
        assert DEFAULT_DRY_THRESHOLD <= finding.similarity_score <= 1.0
        assert finding.start_line >= 1
        assert finding.end_line >= finding.start_line
        assert finding.node_count >= DEFAULT_DRY_MIN_NODES
        assert finding.qualified_name
        assert finding.filepath
