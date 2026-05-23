"""Tests for shared path scope helpers."""

from __future__ import annotations

from pathlib import Path

from agentic_test_forge.scope import (
    filter_git_changed_files,
    is_under_any,
    iter_files_by_suffix,
    normalize_paths,
    resolve_search_root,
)


def test_resolve_search_root_defaults_to_cwd(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_search_root() == tmp_path.resolve()


def test_normalize_paths_resolves_relative_and_absolute(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    absolute = tmp_path / "lib"
    absolute.mkdir()
    resolved = normalize_paths(["src", str(absolute)], tmp_path)
    assert resolved == [src.resolve(), absolute.resolve()]


def test_is_under_any_matches_nested_paths(tmp_path: Path) -> None:
    root = tmp_path / "src"
    nested = root / "pkg" / "mod.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("x = 1\n", encoding="utf-8")
    assert is_under_any(nested.resolve(), [root.resolve()])


def test_iter_files_by_suffix_collects_python_files(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    module = src / "mod.py"
    module.write_text("x = 1\n", encoding="utf-8")
    (src / "readme.txt").write_text("nope", encoding="utf-8")
    files = iter_files_by_suffix([src], ".py")
    assert files == [module.resolve()]


def test_filter_git_changed_files_scopes_to_path_roots(tmp_path: Path) -> None:
    src = tmp_path / "src"
    other = tmp_path / "other"
    src.mkdir()
    other.mkdir()
    changed_file = src / "changed.py"
    changed_file.write_text("x = 1\n", encoding="utf-8")
    other_file = other / "other.py"
    other_file.write_text("y = 2\n", encoding="utf-8")

    filtered = filter_git_changed_files(
        ["src/changed.py", "other/other.py"],
        suffix=".py",
        search_root=tmp_path,
        path_roots=[src.resolve()],
    )
    assert filtered == [changed_file.resolve()]
