"""Load [tool.forge] from pyproject.toml and optional forge.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from agentic_test_forge.config.models import ForgeConfig
from agentic_test_forge.config.parsers import (
    parse_crap_settings,
    parse_gates,
    parse_gherkin_settings,
    parse_mutation_settings,
    parse_paths,
)

_DEFAULTS = ForgeConfig()


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _find_pyproject(start: Path) -> Path | None:
    current = start.resolve()
    for directory in [current, *current.parents]:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def _parse_forge_section(raw: dict[str, Any]) -> ForgeConfig:
    """Compose forge config from focused section parsers."""
    paths = parse_paths(raw, _DEFAULTS)
    crap_threshold, crap_formula = parse_crap_settings(raw, _DEFAULTS)
    mutation_threshold, mutation_base_ref, mutation_test_cmd = parse_mutation_settings(
        raw,
        _DEFAULTS,
    )
    (
        gherkin_threshold,
        gherkin_base_ref,
        gherkin_test_cmd,
        gherkin_runner,
        gherkin_paths,
    ) = parse_gherkin_settings(raw, _DEFAULTS)

    manifest_dir = str(raw.get("manifest_dir", _DEFAULTS.manifest_dir))

    return ForgeConfig(
        paths=paths,
        crap_threshold=crap_threshold,
        crap_formula=crap_formula,
        manifest_dir=manifest_dir,
        mutation_threshold=mutation_threshold,
        mutation_base_ref=mutation_base_ref,
        mutation_test_cmd=mutation_test_cmd,
        gherkin_threshold=gherkin_threshold,
        gherkin_base_ref=gherkin_base_ref,
        gherkin_test_cmd=gherkin_test_cmd,
        gherkin_runner=gherkin_runner,
        gherkin_paths=gherkin_paths,
        gates=parse_gates(raw, _DEFAULTS.gates),
    )


def load_config(project_root: Path | None = None) -> ForgeConfig:
    """Load forge config from pyproject.toml with optional forge.toml override."""
    root = (project_root or Path.cwd()).resolve()
    pyproject_path = _find_pyproject(root)
    merged: dict[str, Any] = {}

    if pyproject_path is not None:
        pyproject_data = _read_toml(pyproject_path)
        tool_section = pyproject_data.get("tool", {})
        if isinstance(tool_section, dict):
            forge_section = tool_section.get("forge", {})
            if isinstance(forge_section, dict):
                merged = _deep_merge(merged, forge_section)

    forge_toml = root / "forge.toml"
    if forge_toml.is_file():
        forge_data = _read_toml(forge_toml)
        if isinstance(forge_data, dict):
            merged = _deep_merge(merged, forge_data)

    if not merged:
        return _DEFAULTS

    return _parse_forge_section(merged)
