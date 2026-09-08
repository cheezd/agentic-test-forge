"""Shared helpers for Gherkin lint, inventory, and step validation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agentic_test_forge.mutation.gherkin.parser import (
    EXAMPLES_PATTERN,
    GherkinScenario,
    parse_feature_file,
)
from agentic_test_forge.scope import (
    filter_git_changed_files,
    iter_files_by_suffix,
    normalize_paths,
    resolve_search_root,
    run_git_diff_names,
)

TAG_LINE_PATTERN = re.compile(r"^\s*(?:@\S+)(?:\s+@\S+)*\s*$")
TAG_TOKEN_PATTERN = re.compile(r"@\S+")
STEP_LINE_PATTERN = re.compile(
    r"^\s*(Given|When|Then|And|But)\s+(.+?)\s*$",
    re.IGNORECASE,
)
FEATURE_LINE_PATTERN = re.compile(r"^\s*Feature:\s*", re.IGNORECASE)
OUTLINE_LINE_PATTERN = re.compile(r"^\s*Scenario Outline:", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedScenario:
    """Parser scenario plus tags, kind, and Examples-keyword presence."""

    scenario: GherkinScenario
    tags: tuple[str, ...]
    kind: str
    has_examples_keyword: bool
    steps: tuple[str, ...]

    @property
    def has_examples(self) -> bool:
        return self.scenario.examples is not None


def collect_feature_files(
    paths: Sequence[str | Path],
    *,
    search_root: Path | None = None,
    base_ref: str | None = None,
) -> list[Path]:
    """Return ``.feature`` files under ``paths``, optionally git-filtered."""
    root = resolve_search_root(search_root)
    path_roots = normalize_paths([str(p) for p in paths], root)
    if base_ref is None:
        return iter_files_by_suffix(path_roots, ".feature")

    changed = run_git_diff_names(
        base_ref,
        root,
        context="gherkin inventory scope",
    )
    return filter_git_changed_files(
        changed,
        suffix=".feature",
        search_root=root,
        path_roots=path_roots,
    )


def collect_parsed_scenarios(
    paths: Sequence[str | Path],
    *,
    search_root: Path | None = None,
    base_ref: str | None = None,
) -> list[ParsedScenario]:
    """Parse all scenarios under ``paths`` with preflight metadata."""
    root = resolve_search_root(search_root)
    path_roots = normalize_paths([str(p) for p in paths], root)
    parsed: list[ParsedScenario] = []
    for feature_path in collect_feature_files(
        paths,
        search_root=root,
        base_ref=base_ref,
    ):
        parse_root = _project_root_for(feature_path, root, path_roots)
        file_tags = _feature_level_tags(feature_path)
        for scenario in parse_feature_file(feature_path, project_root=parse_root):
            parsed.append(_enrich_scenario(feature_path, scenario, file_tags))
    return parsed


def _project_root_for(
    feature_path: Path,
    search_root: Path,
    path_roots: Sequence[Path],
) -> Path:
    """Return a root that ``feature_path`` can be made relative to."""
    resolved = feature_path.resolve()
    try:
        resolved.relative_to(search_root)
        return search_root
    except ValueError:
        pass
    for candidate in path_roots:
        try:
            resolved.relative_to(candidate.resolve())
            return candidate.resolve()
        except ValueError:
            continue
    return resolved.parent


def _feature_level_tags(feature_path: Path) -> tuple[str, ...]:
    lines = feature_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if FEATURE_LINE_PATTERN.match(line) is None:
            continue
        return _tags_immediately_above(lines, index)
    return ()


def _enrich_scenario(
    feature_path: Path,
    scenario: GherkinScenario,
    feature_tags: tuple[str, ...],
) -> ParsedScenario:
    lines = feature_path.read_text(encoding="utf-8").splitlines()
    start_index = scenario.start_line - 1
    scenario_tags = _tags_immediately_above(lines, start_index)
    tags = tuple(dict.fromkeys((*feature_tags, *scenario_tags)))
    kind = "outline" if OUTLINE_LINE_PATTERN.search(scenario.block_text) else "scenario"
    has_examples_keyword = any(
        EXAMPLES_PATTERN.match(line) for line in scenario.block_text.splitlines()
    )
    steps = tuple(_iter_step_texts(scenario.block_text))
    return ParsedScenario(
        scenario=scenario,
        tags=tags,
        kind=kind,
        has_examples_keyword=has_examples_keyword,
        steps=steps,
    )


def _tags_immediately_above(lines: list[str], start_index: int) -> tuple[str, ...]:
    tags: list[str] = []
    index = start_index - 1
    while index >= 0:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index -= 1
            continue
        if TAG_LINE_PATTERN.match(line) is None:
            break
        tags = [*TAG_TOKEN_PATTERN.findall(line), *tags]
        index -= 1
    return tuple(tags)


def _iter_step_texts(block_text: str) -> list[str]:
    steps: list[str] = []
    for line in block_text.splitlines():
        if EXAMPLES_PATTERN.match(line):
            break
        match = STEP_LINE_PATTERN.match(line)
        if match is not None:
            steps.append(match.group(2).strip())
    return steps
