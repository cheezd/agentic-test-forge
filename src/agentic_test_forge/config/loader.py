"""Load [tool.forge] from pyproject.toml and optional forge.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from agentic_test_forge.config.models import CrapFormula, ForgeConfig, GateConfig

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


def _parse_gates(raw: dict[str, Any]) -> GateConfig:
    gates_raw = raw.get("gates", {})
    if not isinstance(gates_raw, dict):
        return _DEFAULTS.gates
    return GateConfig(
        crap=bool(gates_raw.get("crap", _DEFAULTS.gates.crap)),
        mutation=bool(gates_raw.get("mutation", _DEFAULTS.gates.mutation)),
        gherkin=bool(gates_raw.get("gherkin", _DEFAULTS.gates.gherkin)),
    )


def _parse_forge_section(raw: dict[str, Any]) -> ForgeConfig:
    paths = raw.get("paths", _DEFAULTS.paths)
    if isinstance(paths, str):
        paths_list = [paths]
    elif isinstance(paths, list):
        paths_list = [str(p) for p in paths]
    else:
        paths_list = list(_DEFAULTS.paths)

    formula_raw = str(raw.get("crap_formula", _DEFAULTS.crap_formula))
    formula: CrapFormula = "simplified" if formula_raw == "simplified" else "standard"

    threshold_raw = raw.get("crap_threshold", _DEFAULTS.crap_threshold)
    threshold = float(threshold_raw)

    manifest_dir = str(raw.get("manifest_dir", _DEFAULTS.manifest_dir))

    mutation_threshold_raw = raw.get("mutation_threshold", _DEFAULTS.mutation_threshold)
    mutation_threshold = float(mutation_threshold_raw)
    mutation_base_ref = str(raw.get("mutation_base_ref", _DEFAULTS.mutation_base_ref))
    mutation_test_cmd = str(raw.get("mutation_test_cmd", _DEFAULTS.mutation_test_cmd))

    return ForgeConfig(
        paths=paths_list,
        crap_threshold=threshold,
        crap_formula=formula,
        manifest_dir=manifest_dir,
        mutation_threshold=mutation_threshold,
        mutation_base_ref=mutation_base_ref,
        mutation_test_cmd=mutation_test_cmd,
        gates=_parse_gates(raw),
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
