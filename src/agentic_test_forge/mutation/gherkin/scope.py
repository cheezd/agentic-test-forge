"""Resolve which Gherkin scenarios should be mutation-tested."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from agentic_test_forge.manifest.store import (
    gherkin_manifest_path,
    load_manifest,
)
from agentic_test_forge.mutation.code.scope import GitScopeError
from agentic_test_forge.mutation.gherkin.parser import (
    GherkinScenario,
    parse_feature_file,
    scenario_content_hash,
)


@dataclass(frozen=True)
class GherkinScopeResult:
    """Scenarios selected for mutation and scenarios skipped by the manifest."""

    selected: tuple[GherkinScenario, ...]
    skipped_unchanged: tuple[GherkinScenario, ...]
    base_ref: str


def _run_git_diff(base_ref: str, search_root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=search_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        msg = "git executable not found; required for differential gherkin scope."
        raise GitScopeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = f"git diff failed for base ref '{base_ref}': {exc.stderr.strip()}"
        raise GitScopeError(msg) from exc
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _normalize_paths(paths: list[str | Path], search_root: Path) -> list[Path]:
    normalized: list[Path] = []
    for raw in paths:
        candidate = Path(raw)
        resolved = candidate if candidate.is_absolute() else (search_root / candidate)
        normalized.append(resolved.resolve())
    return normalized


def _is_under_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _collect_feature_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".feature":
            files.append(root.resolve())
        elif root.is_dir():
            files.extend(sorted(p.resolve() for p in root.rglob("*.feature")))
    return files


def _scenarios_with_examples(feature_path: Path, project_root: Path) -> list[GherkinScenario]:
    return [
        scenario
        for scenario in parse_feature_file(feature_path, project_root=project_root)
        if scenario.examples is not None
    ]


def resolve_gherkin_scope(
    paths: list[str | Path],
    *,
    base_ref: str,
    search_root: Path | None = None,
    manifest_dir: str = ".forge",
    full_run: bool = False,
) -> GherkinScopeResult:
    """Return scenarios to mutate, applying git diff and manifest filters."""
    root = (search_root or Path.cwd()).resolve()
    path_roots = _normalize_paths([str(p) for p in paths], root)

    if full_run:
        candidate_files = _collect_feature_files(path_roots)
    else:
        changed = _run_git_diff(base_ref, root)
        candidate_files = []
        for relative in changed:
            if not relative.endswith(".feature"):
                continue
            candidate = (root / relative).resolve()
            if candidate.is_file() and _is_under_any(candidate, path_roots):
                candidate_files.append(candidate)

    manifest = load_manifest(gherkin_manifest_path(manifest_dir))
    selected: list[GherkinScenario] = []
    skipped: list[GherkinScenario] = []

    for feature_path in candidate_files:
        for scenario in _scenarios_with_examples(feature_path, root):
            current_hash = scenario_content_hash(scenario.block_text)
            previous = manifest.files.get(scenario.scenario_id)
            if (
                not full_run
                and previous is not None
                and previous.content_hash == current_hash
            ):
                skipped.append(scenario)
                continue
            selected.append(scenario)

    return GherkinScopeResult(
        selected=tuple(selected),
        skipped_unchanged=tuple(skipped),
        base_ref=base_ref,
    )
