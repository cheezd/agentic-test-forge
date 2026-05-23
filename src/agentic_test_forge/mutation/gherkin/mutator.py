"""Generate and apply mutations to Gherkin Examples cells."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentic_test_forge.config.models import GherkinRunner
from agentic_test_forge.mutation.gherkin.feature_editor import FeatureFileEditor
from agentic_test_forge.mutation.gherkin.parser import GherkinScenario
from agentic_test_forge.mutation.gherkin.report import GherkinFinding
from agentic_test_forge.mutation.gherkin.runner import run_acceptance_tests
from agentic_test_forge.mutation.gherkin.scoring import (
    DRY_RUN_MUTATION_EXIT_CODE,
    score_mutations,
)


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


@dataclass(frozen=True)
class ScenarioMutator:
    """Apply example mutations and run acceptance tests for one scenario."""

    project_root: Path
    test_cmd: str
    runner: GherkinRunner
    run_tests: bool

    def apply_and_test(
        self,
        scenario: GherkinScenario,
        *,
        threshold: float,
    ) -> GherkinFinding:
        """Mutate a scenario's Examples table and score surviving mutations."""
        mutations = generate_example_mutations(scenario)
        if not mutations:
            return score_mutations(
                scenario_id=scenario.scenario_id,
                killed=0,
                total=0,
                threshold=threshold,
            )

        source_path = self.project_root / scenario.filepath
        killed = 0

        with FeatureFileEditor(source_path) as editor:
            for mutation in mutations:
                mutated_lines = apply_mutation(
                    editor.original_lines,
                    scenario,
                    mutation,
                )
                editor.write_lines(mutated_lines)
                exit_code = self._mutation_exit_code(scenario, editor.work_path)
                if exit_code != 0:
                    killed += 1

        return score_mutations(
            scenario_id=scenario.scenario_id,
            killed=killed,
            total=len(mutations),
            threshold=threshold,
        )

    def _mutation_exit_code(self, scenario: GherkinScenario, feature_path: Path) -> int:
        if not self.run_tests:
            return DRY_RUN_MUTATION_EXIT_CODE
        return run_acceptance_tests(
            test_cmd=self.test_cmd,
            runner=self.runner,
            scenario=scenario,
            project_root=self.project_root,
            feature_path=feature_path,
        )
