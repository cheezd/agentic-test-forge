"""Subprocess wrapper for mutmut."""

from __future__ import annotations

import os
import platform
import shutil
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


def _mutmut_name_patterns_for_paths(relative_paths: list[str]) -> list[str]:
    """Build mutmut CLI mutant-name globs from scoped relative file paths."""
    patterns: list[str] = []
    for raw_path in relative_paths:
        posix = raw_path.replace("\\", "/")
        for prefix in ("src/", "lib/"):
            if posix.startswith(prefix):
                posix = posix[len(prefix) :]
                break
        if posix.endswith(".py"):
            posix = posix[:-3]
        module = posix.replace("/", ".")
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        patterns.append(f"{module}.*")
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


def _mutmut_argv(*args: str) -> list[str]:
    """Build mutmut CLI argv.

    Prefer the ``mutmut`` console script over ``python -m mutmut`` so
    ``mutmut.__main__`` stays cached in ``sys.modules`` during pytest runs
    (see mutmut GH-466).
    """
    mutmut_exe = shutil.which("mutmut")
    if mutmut_exe is not None:
        return [mutmut_exe, *args]
    return [sys.executable, "-m", "mutmut", *args]


def run_mutmut(
    project_root: Path,
    *,
    relative_paths: list[str],
    test_cmd: str | None = None,
) -> None:
    """Run mutmut for scoped paths without mutating the consumer pyproject.toml."""
    ensure_mutmut_available()
    write_mutmut_run_config(project_root, relative_paths, test_cmd=test_cmd)
    wildcards = _mutmut_name_patterns_for_paths(relative_paths)
    run_argv = _mutmut_argv("run", *wildcards) if wildcards else _mutmut_argv("run")
    env = os.environ.copy()
    completed = subprocess.run(
        run_argv,
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
        _mutmut_argv("export-cicd-stats"),
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
