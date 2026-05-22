"""Tests for acceptance test runner wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_test_forge.mutation.gherkin.parser import GherkinScenario
from agentic_test_forge.mutation.gherkin.runner import (
    GherkinRunError,
    build_test_command,
    run_acceptance_tests,
)


def test_build_test_command_for_behave(tmp_path: Path) -> None:
    scenario = GherkinScenario(
        scenario_id="features/sample.feature::Add numbers",
        name="Add numbers",
        filepath="features/sample.feature",
        start_line=3,
        end_line=10,
        block_text="block",
        examples=None,
    )
    command = build_test_command(
        test_cmd="behave",
        runner="behave",
        scenario=scenario,
        project_root=tmp_path,
    )
    assert command[0] == "behave"
    assert "--name" in command
    assert "Add numbers" in command


def test_run_acceptance_tests_returns_exit_code(tmp_path: Path) -> None:
    scenario = GherkinScenario(
        scenario_id="features/sample.feature::Add numbers",
        name="Add numbers",
        filepath="features/sample.feature",
        start_line=3,
        end_line=10,
        block_text="block",
        examples=None,
    )
    ok = type("Result", (), {"returncode": 1})()
    with patch(
        "agentic_test_forge.mutation.gherkin.runner.subprocess.run",
        return_value=ok,
    ):
        exit_code = run_acceptance_tests(
            test_cmd="behave",
            runner="behave",
            scenario=scenario,
            project_root=tmp_path,
        )
    assert exit_code == 1


def test_run_acceptance_tests_raises_when_command_missing(tmp_path: Path) -> None:
    scenario = GherkinScenario(
        scenario_id="features/sample.feature::Add numbers",
        name="Add numbers",
        filepath="features/sample.feature",
        start_line=3,
        end_line=10,
        block_text="block",
        examples=None,
    )
    with (
        patch(
            "agentic_test_forge.mutation.gherkin.runner.subprocess.run",
            side_effect=FileNotFoundError("missing"),
        ),
        pytest.raises(GherkinRunError, match="not found"),
    ):
        run_acceptance_tests(
            test_cmd="missing-runner",
            runner="behave",
            scenario=scenario,
            project_root=tmp_path,
        )
