"""Subprocess wrapper for mutmut."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

import tomli_w

from agentic_test_forge.errors import ForgeToolError


class MutationUnavailableError(ForgeToolError):
    """Raised when mutmut cannot run in the current environment."""


class MutmutRunError(ForgeToolError):
    """Raised when mutmut exits with an unexpected failure."""


def ensure_mutmut_available() -> None:
    if platform.system() == "Windows":
        msg = (
            "mutmut does not support native Windows. "
            "Run mutation testing in WSL or Linux CI."
        )
        raise MutationUnavailableError(msg)
    try:
        import mutmut  # noqa: F401
    except ImportError as exc:
        msg = "mutmut is not installed."
        raise MutationUnavailableError(msg) from exc


def _wildcard_patterns_for_paths(relative_paths: list[str]) -> list[str]:
    """Build mutmut CLI wildcard filters from scoped relative file paths."""
    patterns: list[str] = []
    for raw_path in relative_paths:
        posix = raw_path.replace("\\", "/")
        if posix.endswith(".py"):
            patterns.append(f"{posix[:-3]}*")
        else:
            patterns.append(f"{posix.rstrip('/')}*")
    return patterns


def write_mutmut_run_config(
    project_root: Path,
    relative_paths: list[str],
    *,
    test_cmd: str | None = None,
) -> Path:
    """Persist forge-owned mutmut run metadata under ``.forge/`` (audit only)."""
    config_path = project_root / ".forge" / "mutmut-run.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    mutmut_section: dict[str, object] = {"source_paths": relative_paths}
    if test_cmd is not None:
        mutmut_section["mutation_test_cmd"] = test_cmd
    payload = {"tool": {"mutmut": mutmut_section}}
    config_path.write_text(tomli_w.dumps(payload), encoding="utf-8")
    return config_path


def run_mutmut(
    project_root: Path,
    *,
    relative_paths: list[str],
    test_cmd: str | None = None,
) -> None:
    """Run mutmut for scoped paths without mutating the consumer pyproject.toml."""
    ensure_mutmut_available()
    write_mutmut_run_config(project_root, relative_paths, test_cmd=test_cmd)
    wildcards = _wildcard_patterns_for_paths(relative_paths)
    env = os.environ.copy()
    run_cmd = [sys.executable, "-m", "mutmut", "run", *wildcards]
    completed = subprocess.run(
        run_cmd,
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        msg = f"mutmut run failed: {detail}"
        raise MutmutRunError(msg)

    export = subprocess.run(
        [sys.executable, "-m", "mutmut", "export_cicd_stats"],
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if export.returncode != 0:
        detail = export.stderr.strip() or export.stdout.strip() or "unknown error"
        msg = f"mutmut export_cicd_stats failed: {detail}"
        raise MutmutRunError(msg)
