"""Shared forge error types."""


class ForgeError(Exception):
    """Base class for forge domain errors."""


class ForgeToolError(ForgeError):
    """Analysis could not run; maps to CLI exit code TOOL_ERROR."""


class ConfigError(ForgeError):
    """Invalid forge configuration."""
