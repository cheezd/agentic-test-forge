"""Tests for Gherkin mutation constants and cell mutation helpers."""

from __future__ import annotations

from agentic_test_forge.mutation.gherkin.constants import (
    NUMBER_DELTA,
    STRING_MUTATION_SUFFIX,
    ZERO_REPLACEMENT,
)
from agentic_test_forge.mutation.gherkin.mutator import mutate_cell_value


def test_mutate_string_cell_uses_named_suffix() -> None:
    candidates = mutate_cell_value("foo")
    assert f"foo{STRING_MUTATION_SUFFIX}" in candidates


def test_mutate_number_cell_uses_named_delta_and_zero() -> None:
    candidates = mutate_cell_value("3")
    assert str(3 + NUMBER_DELTA) in candidates
    assert str(3 - NUMBER_DELTA) in candidates
    assert ZERO_REPLACEMENT in candidates


def test_mutate_invalid_number_falls_back_to_string_mutations() -> None:
    candidates = mutate_cell_value("1.2.3")
    assert f"1.2.3{STRING_MUTATION_SUFFIX}" in candidates
