"""Tests for shared git scope helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agentic_test_forge.scope import GitScopeError, run_git_diff_names


def test_run_git_diff_names_returns_stripped_lines(tmp_path: Path) -> None:
    completed = MagicMock()
    completed.stdout = "src/a.py\n\nsrc/b.py\n"
    with patch("agentic_test_forge.scope.git.subprocess.run", return_value=completed):
        names = run_git_diff_names("main", tmp_path)
    assert names == ["src/a.py", "src/b.py"]


def test_run_git_diff_names_raises_when_git_missing(tmp_path: Path) -> None:
    with (
        patch(
            "agentic_test_forge.scope.git.subprocess.run",
            side_effect=FileNotFoundError("git"),
        ),
        pytest.raises(GitScopeError, match="git executable not found"),
    ):
        run_git_diff_names("main", tmp_path, context="differential mutation scope")


def test_run_git_diff_names_raises_on_git_failure(tmp_path: Path) -> None:
    import subprocess

    with (
        patch(
            "agentic_test_forge.scope.git.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", "diff"],
                stderr="fatal: bad revision",
            ),
        ),
        pytest.raises(GitScopeError, match="git diff failed"),
    ):
        run_git_diff_names("main", tmp_path)
