"""Tests for forge check orchestration."""

from __future__ import annotations

from unittest.mock import patch

from agentic_test_forge.analysis.crap import CoverageDataMissingError, CrapReport
from agentic_test_forge.config.models import ForgeConfig, GateConfig
from agentic_test_forge.mutation.code import MutationUnavailableError
from agentic_test_forge.mutation.code.report import MutationReport
from agentic_test_forge.orchestration.check import run_quality_check


def test_run_quality_check_with_no_gates_enabled() -> None:
    config = ForgeConfig(gates=GateConfig(crap=False, mutation=False, gherkin=False))
    report = run_quality_check(config)
    assert report.status == "pass"
    assert report.gates_run == ()


def test_run_quality_check_runs_enabled_crap_gate() -> None:
    config = ForgeConfig(gates=GateConfig(crap=True, mutation=False, gherkin=False))
    crap = CrapReport(
        tool="crap",
        status="pass",
        threshold=30,
        formula="standard",
        findings=(),
        summary="ok",
    )
    with patch("agentic_test_forge.orchestration.check.analyze_crap", return_value=crap):
        report = run_quality_check(config, paths=["src"])

    assert report.crap == crap
    assert report.gates_run == ("crap",)


def test_run_quality_check_records_crap_tool_error() -> None:
    config = ForgeConfig(gates=GateConfig(crap=True, mutation=False, gherkin=False))
    with patch(
        "agentic_test_forge.orchestration.check.analyze_crap",
        side_effect=CoverageDataMissingError("missing coverage"),
    ):
        report = run_quality_check(config, paths=["src"])

    assert report.errors == ("crap: missing coverage",)
    assert report.crap is None


def test_run_quality_check_fails_when_mutation_gate_fails() -> None:
    config = ForgeConfig(gates=GateConfig(crap=False, mutation=True, gherkin=False))
    mutation = MutationReport(
        tool="mutation",
        status="fail",
        threshold=80,
        findings=(),
        summary="low score",
    )
    with patch(
        "agentic_test_forge.orchestration.check.analyze_mutation",
        return_value=mutation,
    ):
        report = run_quality_check(config, paths=["src"])

    assert report.status == "fail"


def test_run_quality_check_records_mutation_unavailable() -> None:
    config = ForgeConfig(gates=GateConfig(crap=False, mutation=True, gherkin=False))
    with patch(
        "agentic_test_forge.orchestration.check.analyze_mutation",
        side_effect=MutationUnavailableError("mutmut unavailable"),
    ):
        report = run_quality_check(config, paths=["src"])

    assert "mutation: mutmut unavailable" in report.errors
