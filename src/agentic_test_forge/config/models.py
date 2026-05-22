"""Configuration models for [tool.forge]."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

CrapFormula = Literal["standard", "simplified"]
GherkinRunner = Literal["behave", "pytest"]


@dataclass(frozen=True)
class GateConfig:
    """Which quality gates are enabled in forge check."""

    crap: bool = False
    mutation: bool = False
    gherkin: bool = False
    dry: bool = False


@dataclass(frozen=True)
class ForgeConfig:
    """Resolved forge configuration for a consumer project."""

    paths: list[str] = field(default_factory=lambda: ["src"])
    crap_threshold: float = 30.0
    crap_formula: CrapFormula = "standard"
    manifest_dir: str = ".forge"
    mutation_threshold: float = 80.0
    mutation_base_ref: str = "main"
    mutation_test_cmd: str = "pytest"
    gherkin_threshold: float = 80.0
    gherkin_base_ref: str = "main"
    gherkin_test_cmd: str = "behave"
    gherkin_runner: GherkinRunner = "behave"
    gherkin_paths: list[str] = field(default_factory=lambda: ["features"])
    gates: GateConfig = field(default_factory=GateConfig)
