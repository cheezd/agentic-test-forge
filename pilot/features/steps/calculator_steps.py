"""Behave step definitions for the Gherkin mutation pilot."""

from __future__ import annotations

from behave import given, then, when
from pilot_app.calculator import add


@given("values {a:d} and {b:d}")
def step_given_values(context: object, a: int, b: int) -> None:
    context.a = a  # type: ignore[attr-defined]
    context.b = b  # type: ignore[attr-defined]


@when("they are added")
def step_when_added(context: object) -> None:
    context.result = add(context.a, context.b)  # type: ignore[attr-defined]


@then("the result is {expected:d}")
def step_then_result(context: object, expected: int) -> None:
    assert context.result == expected  # type: ignore[attr-defined]


@given("nothing special")
def step_given_nothing(_context: object) -> None:
    return None


@when("nothing happens")
def step_when_nothing(_context: object) -> None:
    return None


@then("nothing fails")
def step_then_nothing(_context: object) -> None:
    assert True
