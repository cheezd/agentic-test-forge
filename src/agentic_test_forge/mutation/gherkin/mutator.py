"""Generate and apply mutations to Gherkin Examples cells."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_test_forge.mutation.gherkin.parser import GherkinScenario


@dataclass(frozen=True)
class ExampleMutation:
    """One mutation applied to a single Examples cell."""

    row_index: int
    column_index: int
    original: str
    mutated: str
    line_index: int


def _mutate_string(value: str) -> list[str]:
    mutations: list[str] = []
    if value:
        mutations.append("")
        mutations.append(f"{value}_mutated")
    else:
        mutations.append("mutated")
    lowered = value.lower()
    if lowered in {"true", "false"}:
        mutations.append("false" if lowered == "true" else "true")
    return mutations


def _mutate_number(value: str) -> list[str]:
    mutations: list[str] = []
    try:
        if "." in value:
            number = float(value)
            mutations.extend([str(number + 1), str(number - 1), "0"])
        else:
            number = int(value)
            mutations.extend([str(number + 1), str(number - 1), "0"])
    except ValueError:
        return _mutate_string(value)
    return mutations


def mutate_cell_value(value: str) -> list[str]:
    """Return candidate replacement values for one Examples cell."""
    stripped = value.strip()
    if not stripped:
        return [""] if value == "" else _mutate_string(value)

    if stripped.isdigit() or (
        stripped.replace(".", "", 1).isdigit() and stripped.count(".") <= 1
    ):
        candidates = _mutate_number(stripped)
    else:
        candidates = _mutate_string(stripped)

    unique: list[str] = []
    for candidate in candidates:
        if candidate != stripped and candidate not in unique:
            unique.append(candidate)
    return unique


def generate_example_mutations(scenario: GherkinScenario) -> list[ExampleMutation]:
    """Build mutations for every cell in a scenario's Examples table."""
    if scenario.examples is None:
        return []

    mutations: list[ExampleMutation] = []
    for row_index, row in enumerate(scenario.examples.rows):
        for column_index, cell in enumerate(row.cells):
            for mutated in mutate_cell_value(cell):
                mutations.append(
                    ExampleMutation(
                        row_index=row_index,
                        column_index=column_index,
                        original=cell,
                        mutated=mutated,
                        line_index=row.line_index,
                    ),
                )
    return mutations


def apply_mutation(
    lines: list[str],
    scenario: GherkinScenario,
    mutation: ExampleMutation,
) -> list[str]:
    """Return file lines with one Examples cell replaced."""
    if scenario.examples is None:
        return list(lines)

    updated = list(lines)
    row = scenario.examples.rows[mutation.row_index]
    cells = list(row.cells)
    cells[mutation.column_index] = mutation.mutated
    original_line = lines[row.line_index]
    indent = original_line[: len(original_line) - len(original_line.lstrip())]
    updated[row.line_index] = f"{indent}| " + " | ".join(cells) + " |"
    return updated
