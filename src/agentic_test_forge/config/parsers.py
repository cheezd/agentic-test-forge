"""Focused parsers for [tool.forge] configuration values."""

from __future__ import annotations

from typing import Any, TypeVar

from agentic_test_forge.config.models import CrapFormula, ForgeConfig, GateConfig, GherkinRunner
from agentic_test_forge.errors import ConfigError

T = TypeVar("T")


def parse_string_list(raw: dict[str, Any], key: str, default: list[str]) -> list[str]:
    """Parse a string or list of strings into a normalized path list."""
    value = raw.get(key, default)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return list(default)


def parse_enum(raw: dict[str, Any], key: str, default: T, allowed: set[str], label: str) -> T:
    """Parse an enum-like string, raising ``ConfigError`` on unknown values."""
    raw_value = raw.get(key, default)
    value = str(raw_value)
    if value not in allowed:
        allowed_display = ", ".join(sorted(allowed))
        raise ConfigError(
            f"Invalid {label} {value!r}; expected one of: {allowed_display}",
        )
    return value  # type: ignore[return-value]


def parse_float(
    raw: dict[str, Any],
    key: str,
    default: float,
    *,
    label: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    """Parse a float threshold, raising ``ConfigError`` on invalid input."""
    raw_value = raw.get(key, default)
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid {label}: {raw_value!r} is not a number") from exc

    if min_value is not None and value < min_value:
        raise ConfigError(f"Invalid {label}: {value} must be >= {min_value}")
    if max_value is not None and value > max_value:
        raise ConfigError(f"Invalid {label}: {value} must be <= {max_value}")
    return value


def parse_gates(raw: dict[str, Any], defaults: GateConfig) -> GateConfig:
    """Parse gate toggles from raw forge config."""
    gates_raw = raw.get("gates", {})
    if not isinstance(gates_raw, dict):
        return defaults
    return GateConfig(
        crap=bool(gates_raw.get("crap", defaults.crap)),
        mutation=bool(gates_raw.get("mutation", defaults.mutation)),
        gherkin=bool(gates_raw.get("gherkin", defaults.gherkin)),
        dry=bool(gates_raw.get("dry", defaults.dry)),
    )


def parse_paths(raw: dict[str, Any], defaults: ForgeConfig) -> list[str]:
    """Parse source path globs."""
    return parse_string_list(raw, "paths", list(defaults.paths))


def parse_crap_settings(raw: dict[str, Any], defaults: ForgeConfig) -> tuple[float, CrapFormula]:
    """Parse CRAP threshold and formula."""
    threshold = parse_float(
        raw,
        "crap_threshold",
        defaults.crap_threshold,
        label="crap_threshold",
        min_value=0.0,
    )
    formula = parse_enum(
        raw,
        "crap_formula",
        defaults.crap_formula,
        {"standard", "simplified"},
        "crap_formula",
    )
    return threshold, formula


def parse_mutation_settings(
    raw: dict[str, Any],
    defaults: ForgeConfig,
) -> tuple[float, str, str]:
    """Parse code mutation threshold and git/test settings."""
    threshold = parse_float(
        raw,
        "mutation_threshold",
        defaults.mutation_threshold,
        label="mutation_threshold",
        min_value=0.0,
        max_value=100.0,
    )
    base_ref = str(raw.get("mutation_base_ref", defaults.mutation_base_ref))
    test_cmd = str(raw.get("mutation_test_cmd", defaults.mutation_test_cmd))
    return threshold, base_ref, test_cmd


def parse_gherkin_settings(
    raw: dict[str, Any],
    defaults: ForgeConfig,
) -> tuple[float, str, str, GherkinRunner, list[str]]:
    """Parse Gherkin mutation threshold, runner, and path settings."""
    threshold = parse_float(
        raw,
        "gherkin_threshold",
        defaults.gherkin_threshold,
        label="gherkin_threshold",
        min_value=0.0,
        max_value=100.0,
    )
    base_ref = str(raw.get("gherkin_base_ref", defaults.gherkin_base_ref))
    test_cmd = str(raw.get("gherkin_test_cmd", defaults.gherkin_test_cmd))
    runner = parse_enum(
        raw,
        "gherkin_runner",
        defaults.gherkin_runner,
        {"behave", "pytest"},
        "gherkin_runner",
    )
    paths = parse_string_list(raw, "gherkin_paths", list(defaults.gherkin_paths))
    return threshold, base_ref, test_cmd, runner, paths
