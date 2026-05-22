"""Tests for mutmut subprocess wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_test_forge.mutation.code.runner import (
    MutationUnavailableError,
    MutmutRunError,
    ensure_mutmut_available,
    run_mutmut,
    temporary_mutmut_paths,
)


def test_ensure_mutmut_available_raises_on_windows() -> None:
    with (
        patch("agentic_test_forge.mutation.code.runner.platform.system", return_value="Windows"),
        pytest.raises(MutationUnavailableError, match="Windows"),
    ):
        ensure_mutmut_available()


def test_temporary_mutmut_paths_restores_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"demo\"\n", encoding="utf-8")

    with temporary_mutmut_paths(tmp_path, ["src/example.py"]):
        updated = pyproject.read_text(encoding="utf-8")
        assert "paths_to_mutate" in updated

    restored = pyproject.read_text(encoding="utf-8")
    assert restored == "[project]\nname = \"demo\"\n"


def test_run_mutmut_raises_when_command_fails(tmp_path: Path) -> None:
    with (
        patch(
            "agentic_test_forge.mutation.code.runner.ensure_mutmut_available",
        ),
        patch(
            "agentic_test_forge.mutation.code.runner.subprocess.run",
            return_value=type("Result", (), {"returncode": 1, "stdout": "", "stderr": "boom"})(),
        ),
        pytest.raises(MutmutRunError, match="mutmut run failed"),
    ):
        run_mutmut(tmp_path)


def test_run_mutmut_succeeds_when_commands_pass(tmp_path: Path) -> None:
    ok = type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    with (
        patch(
            "agentic_test_forge.mutation.code.runner.ensure_mutmut_available",
        ),
        patch(
            "agentic_test_forge.mutation.code.runner.subprocess.run",
            return_value=ok,
        ) as run_mock,
    ):
        run_mutmut(tmp_path)

    assert run_mock.call_count == 2
