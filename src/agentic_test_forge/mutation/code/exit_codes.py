"""mutmut process exit codes used when scoring mutation results.

Reference: mutmut records pytest/behave exit codes in ``*.meta`` files under
``mutants/``. Forge maps those codes to killed/survived/skipped/timeout when
building mutation scores.

See mutmut result handling:
https://github.com/boxed/mutmut/blob/main/src/mutmut/result.py
"""

from __future__ import annotations

# Tests failed while running the mutant — counts as killed.
MUTMUT_KILLED_EXIT_CODES: frozenset[int] = frozenset({1, 3, -24})

# Mutant compiled but tests passed — counts as survived.
MUTMUT_SURVIVED_EXIT_CODE = 0

# Mutmut skipped the mutant (unsupported syntax, etc.).
MUTMUT_SKIPPED_EXIT_CODES: frozenset[int] = frozenset({33, 34})

# Test run timed out or was terminated without a clean killed/survived result.
# Note: ``-24`` is classified as killed (see ``MUTMUT_KILLED_EXIT_CODES``) and
# is intentionally excluded here so killed takes precedence.
MUTMUT_TIMEOUT_EXIT_CODES: frozenset[int] = frozenset({36, 24, 255, 152})


def classify_mutmut_exit_code(exit_code: int | None) -> str:
    """Map a mutmut meta exit code to a coarse result label."""
    if exit_code is None:
        return "not_checked"
    if exit_code in MUTMUT_KILLED_EXIT_CODES:
        return "killed"
    if exit_code == MUTMUT_SURVIVED_EXIT_CODE:
        return "survived"
    if exit_code in MUTMUT_SKIPPED_EXIT_CODES:
        return "skipped"
    if exit_code in MUTMUT_TIMEOUT_EXIT_CODES:
        return "timeout"
    return "other"
