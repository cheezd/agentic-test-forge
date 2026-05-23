"""Run acceptance tests for mutated Gherkin scenarios."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from agentic_test_forge.config.models import GherkinRunner
from agentic_test_forge.errors import ForgeToolError
from agentic_test_forge.mutation.gherkin.parser import GherkinScenario


class GherkinRunError(ForgeToolError):
    """Raised when the configured acceptance test command fails to execute."""


def build_test_command(
    *,
    test_cmd: str,
    runner: GherkinRunner,
    scenario: GherkinScenario,
    project_root: Path,
) -> list[str]:
    """Build subprocess argv for one scenario mutation run."""
    base = shlex.split(test_cmd)
    feature_path = project_root / scenario.filepath
    if runner == "behave":
        return [*base, "--name", scenario.name, str(feature_path)]
    return [*base, str(feature_path)]


def run_acceptance_tests(
    *,
    test_cmd: str,
    runner: GherkinRunner,
    scenario: GherkinScenario,
    project_root: Path,
) -> int:
    """Run acceptance tests and return the process exit code."""
    command = build_test_command(
        test_cmd=test_cmd,
        runner=runner,
        scenario=scenario,
        project_root=project_root,
    )
    try:
        completed = subprocess.run(
            command,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        msg = f"Acceptance test command not found: {command[0]}"
        raise GherkinRunError(msg) from exc

    if completed.returncode < 0:
        msg = f"Acceptance test command terminated abnormally: {' '.join(command)}"
        raise GherkinRunError(msg)
    return completed.returncode
