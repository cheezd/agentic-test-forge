"""Tests for mutmut exit code classification."""

from __future__ import annotations

from agentic_test_forge.mutation.code.exit_codes import (
    MUTMUT_KILLED_EXIT_CODES,
    MUTMUT_TIMEOUT_EXIT_CODES,
    classify_mutmut_exit_code,
)


def test_classify_mutmut_exit_code_killed() -> None:
    for code in MUTMUT_KILLED_EXIT_CODES:
        assert classify_mutmut_exit_code(code) == "killed"


def test_classify_mutmut_exit_code_survived() -> None:
    assert classify_mutmut_exit_code(0) == "survived"


def test_killed_precedence_over_timeout_for_negative_twenty_four() -> None:
    assert -24 in MUTMUT_KILLED_EXIT_CODES
    assert -24 not in MUTMUT_TIMEOUT_EXIT_CODES
    assert classify_mutmut_exit_code(-24) == "killed"
