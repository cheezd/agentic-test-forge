"""Tests for forge configuration loading."""

from pathlib import Path

import pytest

from agentic_test_forge.config import ConfigError, load_config


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.forge]
paths = ["lib"]
crap_threshold = 12
crap_formula = "simplified"
manifest_dir = ".forge-cache"
mutation_threshold = 90
mutation_base_ref = "develop"
mutation_test_cmd = "python -m pytest"
gherkin_threshold = 75
gherkin_base_ref = "develop"
gherkin_test_cmd = "behave --no-capture"
gherkin_runner = "pytest"

[tool.forge.gates]
crap = true
mutation = true
gherkin = false
dry = true
""".strip(),
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.paths == ["lib"]
    assert config.crap_threshold == 12.0
    assert config.crap_formula == "simplified"
    assert config.manifest_dir == ".forge-cache"
    assert config.mutation_threshold == 90.0
    assert config.mutation_base_ref == "develop"
    assert config.mutation_test_cmd == "python -m pytest"
    assert config.gherkin_threshold == 75.0
    assert config.gherkin_base_ref == "develop"
    assert config.gherkin_test_cmd == "behave --no-capture"
    assert config.gherkin_runner == "pytest"
    assert config.gates.crap is True
    assert config.gates.mutation is True
    assert config.gates.gherkin is False
    assert config.gates.dry is True


def test_forge_toml_overrides_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
crap_threshold = 30
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "forge.toml").write_text(
        """
crap_threshold = 6
""".strip(),
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.crap_threshold == 6.0


def test_load_config_defaults_when_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path)

    assert config.paths == ["src"]
    assert config.crap_threshold == 30.0
    assert config.crap_formula == "standard"
    assert config.mutation_threshold == 80.0
    assert config.mutation_base_ref == "main"
    assert config.mutation_test_cmd == "pytest"
    assert config.gherkin_threshold == 80.0
    assert config.gherkin_base_ref == "main"
    assert config.gherkin_test_cmd == "behave"
    assert config.gherkin_runner == "behave"
    assert config.gherkin_paths == ["features"]
    assert config.gates.crap is False
    assert config.gates.dry is False


def test_load_config_rejects_invalid_crap_formula(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
crap_formula = "unknown"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Invalid crap_formula"):
        load_config(tmp_path)


def test_load_config_rejects_invalid_gherkin_runner(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
gherkin_runner = "cucumber"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Invalid gherkin_runner"):
        load_config(tmp_path)


def test_load_config_rejects_non_numeric_threshold(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
mutation_threshold = "high"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="mutation_threshold"):
        load_config(tmp_path)


def test_load_config_rejects_out_of_range_mutation_threshold(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
mutation_threshold = 150
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="mutation_threshold"):
        load_config(tmp_path)


def test_load_config_rejects_out_of_range_gherkin_threshold(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.forge]
gherkin_threshold = -5
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="gherkin_threshold"):
        load_config(tmp_path)
