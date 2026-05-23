"""Parse Gherkin feature files and extract mutable Examples tables."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

SCENARIO_PATTERN = re.compile(r"^\s*(Scenario Outline|Scenario):\s*(.+?)\s*$")
EXAMPLES_PATTERN = re.compile(r"^\s*Examples:\s*(.*)$")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|(.+)\|\s*$")


@dataclass(frozen=True)
class ExamplesRow:
    """One row in an Examples table."""

    line_index: int
    cells: tuple[str, ...]


@dataclass(frozen=True)
class ExamplesTable:
    """Parsed Examples table attached to a scenario."""

    header_line_index: int
    header: tuple[str, ...]
    rows: tuple[ExamplesRow, ...]


@dataclass(frozen=True)
class GherkinScenario:
    """Scenario block with optional Examples table."""

    scenario_id: str
    name: str
    filepath: str
    start_line: int
    end_line: int
    block_text: str
    examples: ExamplesTable | None


@dataclass(frozen=True)
class _ScenarioBlock:
    """Intermediate parse result for one scenario block."""

    name: str
    start_line: int
    end_line: int
    start_index: int
    block_lines: tuple[str, ...]


def scenario_content_hash(block_text: str) -> str:
    digest = hashlib.sha256()
    digest.update(block_text.encode("utf-8"))
    return digest.hexdigest()


def _parse_table_row(line: str) -> tuple[str, ...] | None:
    match = TABLE_ROW_PATTERN.match(line)
    if match is None:
        return None
    return tuple(cell.strip() for cell in match.group(1).split("|"))


def _parse_examples_table(lines: list[str], start_index: int) -> ExamplesTable | None:
    index = start_index + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        return None

    header_line_index = index
    header = _parse_table_row(lines[index])
    if header is None:
        return None

    rows: list[ExamplesRow] = []
    index += 1
    while index < len(lines):
        line = lines[index]
        if SCENARIO_PATTERN.match(line):
            break
        if line.strip() and not line.lstrip().startswith("#"):
            cells = _parse_table_row(line)
            if cells is None:
                break
            rows.append(ExamplesRow(line_index=index, cells=cells))
        index += 1

    if not rows:
        return None

    return ExamplesTable(
        header_line_index=header_line_index,
        header=header,
        rows=tuple(rows),
    )


def _iter_scenario_blocks(lines: list[str]) -> Iterator[_ScenarioBlock]:
    """Yield scenario name, line range, and block lines from feature text."""
    index = 0
    while index < len(lines):
        match = SCENARIO_PATTERN.match(lines[index])
        if match is None:
            index += 1
            continue

        name = match.group(2).strip()
        start_line = index + 1
        start_index = index
        block_lines = [lines[index]]
        index += 1

        while index < len(lines):
            line = lines[index]
            if SCENARIO_PATTERN.match(line):
                break
            block_lines.append(line)
            index += 1

        end_line = start_line + len(block_lines) - 1
        yield _ScenarioBlock(
            name=name,
            start_line=start_line,
            end_line=end_line,
            start_index=start_index,
            block_lines=tuple(block_lines),
        )


def _find_examples_in_block(
    lines: list[str],
    block: _ScenarioBlock,
) -> ExamplesTable | None:
    """Locate and parse the Examples table within one scenario block."""
    examples: ExamplesTable | None = None
    for offset, line in enumerate(block.block_lines):
        if EXAMPLES_PATTERN.match(line) is not None:
            examples = _parse_examples_table(lines, block.start_index + offset)
    return examples


def parse_feature_file(path: Path, *, project_root: Path) -> list[GherkinScenario]:
    """Extract scenarios with Examples tables from a .feature file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    relative = str(path.relative_to(project_root)).replace("\\", "/")
    scenarios: list[GherkinScenario] = []

    for block in _iter_scenario_blocks(lines):
        examples = _find_examples_in_block(lines, block)
        block_text = "\n".join(block.block_lines)
        scenarios.append(
            GherkinScenario(
                scenario_id=f"{relative}::{block.name}",
                name=block.name,
                filepath=relative,
                start_line=block.start_line,
                end_line=block.end_line,
                block_text=block_text,
                examples=examples,
            ),
        )

    return scenarios


def parse_feature_paths(paths: list[Path], *, project_root: Path) -> list[GherkinScenario]:
    """Parse all .feature files under the given paths."""
    scenarios: list[GherkinScenario] = []
    for path in paths:
        if path.is_file() and path.suffix == ".feature":
            scenarios.extend(parse_feature_file(path, project_root=project_root))
        elif path.is_dir():
            for feature in sorted(path.rglob("*.feature")):
                scenarios.extend(parse_feature_file(feature, project_root=project_root))
    return scenarios
