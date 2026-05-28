"""Integration tests for the forge-check pre-commit hook."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from agentic_test_forge.cli.exit_codes import ForgeExitCode

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
HOOKS_YAML = REPO_ROOT / ".pre-commit-hooks.yaml"


def _init_git_repo(fixture_dir: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=fixture_dir, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=fixture_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=fixture_dir,
        check=True,
        capture_output=True,
        env={
            **dict(__import__("os").environ),
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _write_pre_commit_config(target_dir: Path) -> None:
    config = """\
repos:
  - repo: local
    hooks:
      - id: forge-check
        name: forge check
        description: Run agentic-test-forge quality gates configured in [tool.forge.gates]
        entry: forge check
        language: python
        pass_filenames: false
        types: [python]
        additional_dependencies: [agentic-test-forge==1.0.0]
        args: [--path, src, --coverage-file, .coverage]
"""
    (target_dir / ".pre-commit-config.yaml").write_text(config, encoding="utf-8")


def _generate_coverage(fixture_dir: Path) -> None:
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(fixture_dir / "src")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "--cov=src",
            "--cov-report=",
            "-q",
            "--rootdir",
            str(fixture_dir),
        ],
        cwd=fixture_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def _run_pre_commit(fixture_dir: Path, *, cache_dir: Path) -> subprocess.CompletedProcess[str]:
    env = dict(__import__("os").environ)
    env["PRE_COMMIT_HOME"] = str(cache_dir)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pre_commit",
            "run",
            "forge-check",
            "--all-files",
            "--config",
            str(fixture_dir / ".pre-commit-config.yaml"),
        ],
        cwd=fixture_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def pre_commit_available() -> None:
    pytest.importorskip("pre_commit")


def test_pre_commit_hooks_yaml_exists_and_defines_forge_check() -> None:
    assert HOOKS_YAML.is_file()
    content = HOOKS_YAML.read_text(encoding="utf-8")
    assert "id: forge-check" in content
    assert "entry: forge check" in content
    assert "pass_filenames: false" in content
    assert "agentic-test-forge" in content


@pytest.mark.usefixtures("pre_commit_available")
def test_pre_commit_forge_check_passes_with_coverage(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "pass"
    shutil.copytree(FIXTURES / "pre_commit_pass", fixture_dir)
    _generate_coverage(fixture_dir)
    _init_git_repo(fixture_dir)
    _write_pre_commit_config(fixture_dir)

    result = _run_pre_commit(fixture_dir, cache_dir=tmp_path / "pre-commit-cache-pass")

    assert result.returncode == ForgeExitCode.SUCCESS, result.stdout + result.stderr


@pytest.mark.usefixtures("pre_commit_available")
def test_pre_commit_forge_check_fails_on_gate_threshold(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fail"
    shutil.copytree(FIXTURES / "pre_commit_fail", fixture_dir)
    _generate_coverage(fixture_dir)
    _init_git_repo(fixture_dir)
    _write_pre_commit_config(fixture_dir)

    result = _run_pre_commit(fixture_dir, cache_dir=tmp_path / "pre-commit-cache-fail")

    assert result.returncode == ForgeExitCode.GATE_FAILURE, result.stdout + result.stderr
    assert "FAIL" in result.stdout + result.stderr


@pytest.mark.usefixtures("pre_commit_available")
def test_pre_commit_forge_check_tool_error_without_coverage(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "no-coverage"
    shutil.copytree(FIXTURES / "pre_commit_no_coverage", fixture_dir)
    _init_git_repo(fixture_dir)
    _write_pre_commit_config(fixture_dir)

    result = _run_pre_commit(fixture_dir, cache_dir=tmp_path / "pre-commit-cache-no-cov")

    output = result.stdout + result.stderr
    # pre-commit returns 1 for any failed hook, even when forge exits TOOL_ERROR (2).
    assert result.returncode == ForgeExitCode.GATE_FAILURE, output
    assert "exit code: 2" in output
    assert "Coverage data not found" in output


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only mutation guard")
def test_forge_check_mutation_on_windows_exits_tool_error(tmp_path: Path) -> None:
    """Mutation gate enabled on Windows must exit 2, not crash (#76)."""
    fixture_dir = tmp_path / "windows-mutation"
    shutil.copytree(FIXTURES / "pre_commit_pass", fixture_dir)
    pyproject = fixture_dir / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace(
            "mutation = false",
            "mutation = true",
        ),
        encoding="utf-8",
    )
    _generate_coverage(fixture_dir)
    _init_git_repo(fixture_dir)

    result = subprocess.run(
        ["forge", "check", "--path", "src", "--full"],
        cwd=fixture_dir,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == ForgeExitCode.TOOL_ERROR
    assert "Windows" in result.stdout + result.stderr
