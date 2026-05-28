"""Unit tests for pilot_app — used by mutmut via pytest."""

from pilot_app.calculator import add, subtract


def test_add() -> None:
    assert add(1, 2) == 3
    assert add(2, 3) == 5


def test_subtract() -> None:
    assert subtract(5, 3) == 2
