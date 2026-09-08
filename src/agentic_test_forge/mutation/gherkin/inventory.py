"""Machine-readable inventory of Gherkin scenarios."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_test_forge.mutation.gherkin.preflight import collect_parsed_scenarios
from agentic_test_forge.reporting.serialize import report_to_json, serialize_findings_report
from agentic_test_forge.reporting.status import ReportStatus

INVENTORY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class InventoryScenario:
    """One scenario row in a sign-off inventory."""

    filepath: str
    name: str
    scenario_id: str
    tags: tuple[str, ...]
    has_examples: bool
    start_line: int
    end_line: int
    kind: str


@dataclass(frozen=True)
class GherkinInventoryReport:
    """Listing report. Always passes; used as a machine packet."""

    tool: str
    status: ReportStatus
    summary: str
    schema_version: int
    scenarios: tuple[InventoryScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        return serialize_findings_report(self, findings_field="scenarios")

    def to_json(self, indent: int = 2) -> str:
        return report_to_json(self, indent=indent, findings_field="scenarios")


def analyze_gherkin_inventory(
    paths: Sequence[str | Path],
    *,
    search_root: Path | None = None,
    base_ref: str | None = None,
) -> GherkinInventoryReport:
    """List scenarios under ``paths``, optionally limited to git-changed files."""
    parsed = collect_parsed_scenarios(paths, search_root=search_root, base_ref=base_ref)
    scenarios = tuple(
        InventoryScenario(
            filepath=item.scenario.filepath,
            name=item.scenario.name,
            scenario_id=item.scenario.scenario_id,
            tags=item.tags,
            has_examples=item.has_examples,
            start_line=item.scenario.start_line,
            end_line=item.scenario.end_line,
            kind=item.kind,
        )
        for item in parsed
    )
    summary = (
        f"{len(scenarios)} scenario(s) inventoried"
        + (f" (changed vs {base_ref})." if base_ref else ".")
    )
    return GherkinInventoryReport(
        tool="gherkin-inventory",
        status=ReportStatus.PASS,
        summary=summary,
        schema_version=INVENTORY_SCHEMA_VERSION,
        scenarios=scenarios,
    )
