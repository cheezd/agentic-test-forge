"""Tests for forge configuration loading."""

from pathlib import Path

from agentic_test_forge.config import load_config


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.forge]
paths = ["lib"]
crap_threshold = 12
crap_formula = "simplified"
manifest_dir = ".forge-cache"

[tool.forge.gates]
crap = true
mutation = true
gherkin = false
""".strip(),
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.paths == ["lib"]
    assert config.crap_threshold == 12.0
    assert config.crap_formula == "simplified"
    assert config.manifest_dir == ".forge-cache"
    assert config.gates.crap is True
    assert config.gates.mutation is True
    assert config.gates.gherkin is False


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
    assert config.gates.crap is False
