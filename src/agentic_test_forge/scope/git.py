"""Git helpers for differential forge scope."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agentic_test_forge.errors import ForgeToolError


class GitScopeError(ForgeToolError):
    """Raised when git-based differential scope cannot be resolved."""


def run_git_diff_names(
    base_ref: str,
    search_root: Path,
    *,
    context: str = "differential scope",
) -> list[str]:
    """Return changed file paths from ``git diff --name-only {base_ref}...HEAD``."""
    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=search_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        msg = f"git executable not found; required for {context}."
        raise GitScopeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = f"git diff failed for base ref '{base_ref}': {exc.stderr.strip()}"
        raise GitScopeError(msg) from exc
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
