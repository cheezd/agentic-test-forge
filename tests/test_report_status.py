"""Tests for shared report status and gate policy enums."""

from __future__ import annotations

from agentic_test_forge.config.models import GateConfig
from agentic_test_forge.reporting.status import GatePolicy, ReportStatus


def test_report_status_str_enum_values() -> None:
    assert ReportStatus.PASS == "pass"
    assert ReportStatus.FAIL == "fail"
    assert ReportStatus.ERROR == "error"


def test_gate_config_policy_for_dry_is_advisory() -> None:
    assert GateConfig.policy_for("dry") == GatePolicy.ADVISORY


def test_gate_config_policy_for_blocking_gates() -> None:
    assert GateConfig.policy_for("crap") == GatePolicy.BLOCKING
    assert GateConfig.policy_for("mutation") == GatePolicy.BLOCKING
    assert GateConfig.policy_for("gherkin") == GatePolicy.BLOCKING
