"""Constants for Gherkin Examples cell mutation strategies."""

from __future__ import annotations

# String cell mutations
EMPTY_STRING_REPLACEMENT = ""
STRING_MUTATION_SUFFIX = "_mutated"
EMPTY_CELL_STRING_REPLACEMENT = "mutated"

# Numeric cell mutations
NUMBER_DELTA = 1
ZERO_REPLACEMENT = "0"

# Boolean toggles handled inline via lowercase comparison.
