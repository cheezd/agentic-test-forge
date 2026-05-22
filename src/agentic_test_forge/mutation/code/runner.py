"""Subprocess wrapper for mutmut."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import tomli_w


class MutationUnavailableError(RuntimeError):
    """Raised when mutmut cannot run in the current environment."""


class MutmutRunError(RuntimeError):
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


@contextmanager
def temporary_mutmut_paths(
    project_root: Path,
    relative_paths: list[str],
) -> Iterator[None]:
    """Temporarily set mutmut paths_to_mutate in pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    backup = project_root / ".forge" / "pyproject.mutmut.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)

    original_text = pyproject.read_text(encoding="utf-8") if pyproject.is_file() else None
    if original_text is not None:
        backup.write_text(original_text, encoding="utf-8")

    data: dict[str, object] = {}
    if pyproject.is_file():
        loaded = tomllib.loads(original_text or "")
        if isinstance(loaded, dict):
            data = loaded

    tool = data.setdefault("tool", {})
    if not isinstance(tool, dict):
        tool = {}
        data["tool"] = tool
    mutmut_section = tool.setdefault("mutmut", {})
    if not isinstance(mutmut_section, dict):
        mutmut_section = {}
        tool["mutmut"] = mutmut_section
    mutmut_section["paths_to_mutate"] = relative_paths

    pyproject.write_text(tomli_w.dumps(data), encoding="utf-8")
    try:
        yield
    finally:
        if original_text is None:
            pyproject.unlink(missing_ok=True)
        else:
            pyproject.write_text(original_text, encoding="utf-8")


def run_mutmut(project_root: Path) -> None:
    ensure_mutmut_available()
    env = os.environ.copy()
    completed = subprocess.run(
        [sys.executable, "-m", "mutmut", "run"],
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
