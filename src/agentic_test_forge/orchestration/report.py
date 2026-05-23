"""Combined quality gate report envelope."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from agentic_test_forge.analysis.crap import CrapReport
from agentic_test_forge.analysis.dry import DryReport
from agentic_test_forge.config.models import GateConfig
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.mutation.gherkin.report import GherkinMutationReport
from agentic_test_forge.reporting.status import GatePolicy, ReportStatus


@dataclass(frozen=True)
class CheckReport:
    """Aggregate report from ``forge check``."""

    tool: str
    status: ReportStatus
    summary: str
    gates_run: tuple[str, ...]
    crap: CrapReport | None = None
    mutation: MutationReport | None = None
    gherkin: GherkinMutationReport | None = None
    dry: DryReport | None = None
    errors: tuple[str, ...] = ()
    gate_policies: tuple[tuple[str, GatePolicy], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "tool": self.tool,
            "status": self.status,
            "summary": self.summary,
            "gates_run": list(self.gates_run),
            "gate_policies": {
                name: policy.value for name, policy in self.gate_policies
            },
            "errors": list(self.errors),
            "reports": {},
        }
        if self.crap is not None:
            payload["reports"]["crap"] = self.crap.to_dict()
        if self.mutation is not None:
            payload["reports"]["mutation"] = self.mutation.to_dict()
        if self.gherkin is not None:
            payload["reports"]["gherkin"] = self.gherkin.to_dict()
        if self.dry is not None:
            payload["reports"]["dry"] = self.dry.to_dict()
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def build_check_report(
    *,
    gates_run: list[str],
    crap: CrapReport | None,
    mutation: MutationReport | None,
    gherkin: GherkinMutationReport | None,
    dry: DryReport | None,
    errors: list[str],
) -> CheckReport:
    if not gates_run and not errors:
        return CheckReport(
            tool="check",
            status=ReportStatus.PASS,
            summary="No quality gates enabled in [tool.forge.gates].",
            gates_run=(),
        )

    failed_gates: list[str] = []
    if crap is not None and crap.status == ReportStatus.FAIL:
        failed_gates.append("crap")
    if mutation is not None and mutation.status == ReportStatus.FAIL:
        failed_gates.append("mutation")
    if gherkin is not None and gherkin.status == ReportStatus.FAIL:
        failed_gates.append("gherkin")

    gate_policies = tuple(
        (gate, GateConfig.policy_for(gate)) for gate in gates_run
    )

    if failed_gates:
        summary = f"Quality gate failed: {', '.join(failed_gates)}."
        status = ReportStatus.FAIL
    elif errors:
        summary = f"Quality gate completed with tool error(s): {len(errors)}."
        status = ReportStatus.ERROR
    else:
        ran = ", ".join(gates_run) if gates_run else "none"
        summary = f"All enabled quality gates passed ({ran})."
        status = ReportStatus.PASS

    return CheckReport(
        tool="check",
        status=status,
        summary=summary,
        gates_run=tuple(gates_run),
        crap=crap,
        mutation=mutation,
        gherkin=gherkin,
        dry=dry,
        errors=tuple(errors),
        gate_policies=gate_policies,
    )
