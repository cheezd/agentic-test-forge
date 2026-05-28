"""Tests for mutmut subprocess wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from agentic_test_forge.mutation.code.runner import (
    MutationUnavailableError,
    MutmutRunError,
    _mutmut_name_patterns_for_paths,
    ensure_mutmut_available,
    run_mutmut,
    write_mutmut_run_config,
)


def test_ensure_mutmut_available_raises_on_windows() -> None:
    with (
        patch("agentic_test_forge.mutation.code.runner.platform.system", return_value="Windows"),
        pytest.raises(MutationUnavailableError, match="Windows"),
    ):
        ensure_mutmut_available()


def test_mutmut_name_patterns_for_paths() -> None:
    assert _mutmut_name_patterns_for_paths(["src/example.py"]) == ["example.*"]
    assert _mutmut_name_patterns_for_paths(["src\\pkg\\mod.py"]) == ["pkg.mod.*"]
    assert _mutmut_name_patterns_for_paths(["src/pilot_app/calculator.py"]) == [
        "pilot_app.calculator.*"
    ]


def test_write_mutmut_run_config_creates_forge_owned_file(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    original = pyproject.read_text(encoding="utf-8")

    config_path = write_mutmut_run_config(
        tmp_path,
        ["src/example.py"],
        test_cmd="pytest",
    )

    assert config_path == tmp_path / ".forge" / "mutmut-run.toml"
    assert config_path.is_file()
    assert "source_paths" in config_path.read_text(encoding="utf-8")
    assert pyproject.read_text(encoding="utf-8") == original


def test_run_mutmut_passes_wildcards_without_touching_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = \"demo\"\n", encoding="utf-8")
    original = pyproject.read_text(encoding="utf-8")
    ok = type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    with (
        patch(
            "agentic_test_forge.mutation.code.runner.ensure_mutmut_available",
        ),
        patch(
            "agentic_test_forge.mutation.code.runner._mutmut_argv",
            side_effect=lambda *args: ["mutmut", *args],
        ),
        patch(
            "agentic_test_forge.mutation.code.runner.subprocess.run",
            return_value=ok,
        ) as run_mock,
    ):
        run_mutmut(tmp_path, relative_paths=["src/example.py"], test_cmd="pytest")

    assert run_mock.call_count == 2
    run_args = run_mock.call_args_list[0].args[0]
    assert run_args[0] == "mutmut"
    assert run_args[1] == "run"
    assert "example.*" in run_args
    assert pyproject.read_text(encoding="utf-8") == original
    assert (tmp_path / ".forge" / "mutmut-run.toml").is_file()


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
        run_mutmut(tmp_path, relative_paths=["src/example.py"])
