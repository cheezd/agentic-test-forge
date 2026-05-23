"""Shared path resolution helpers for forge analyzers and scope."""

from __future__ import annotations

from pathlib import Path


def resolve_search_root(search_root: Path | None = None) -> Path:
    """Return the resolved project root used for relative path resolution."""
    return (search_root or Path.cwd()).resolve()


def normalize_paths(paths: list[str | Path], search_root: Path) -> list[Path]:
    """Resolve configured path roots against ``search_root``."""
    normalized: list[Path] = []
    for raw in paths:
        candidate = Path(raw)
        resolved = candidate if candidate.is_absolute() else (search_root / candidate)
        normalized.append(resolved.resolve())
    return normalized


def is_under_any(path: Path, roots: list[Path]) -> bool:
    """Return whether ``path`` is equal to or nested under any root."""
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def iter_files_by_suffix(roots: list[Path], suffix: str) -> list[Path]:
    """Collect files under ``roots`` matching ``suffix`` (e.g. ``.py``, ``.feature``)."""
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == suffix:
            files.append(root.resolve())
        elif root.is_dir():
            files.extend(sorted(p.resolve() for p in root.rglob(f"*{suffix}")))
    return files


def filter_git_changed_files(
    changed: list[str],
    *,
    suffix: str,
    search_root: Path,
    path_roots: list[Path],
) -> list[Path]:
    """Map git diff names to scoped, resolved files under ``path_roots``."""
    candidate_files: list[Path] = []
    for relative in changed:
        if not relative.endswith(suffix):
            continue
        candidate = (search_root / relative).resolve()
        if candidate.is_file() and is_under_any(candidate, path_roots):
            candidate_files.append(candidate)
    return candidate_files
