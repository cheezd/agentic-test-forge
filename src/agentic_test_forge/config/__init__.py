"""Configuration loading for consumer projects."""

from agentic_test_forge.config.loader import load_config
from agentic_test_forge.config.models import ForgeConfig, GateConfig

__all__ = ["ForgeConfig", "GateConfig", "load_config"]
