"""Shared report status and gate policy enums."""

from __future__ import annotations

from enum import StrEnum


class ReportStatus(StrEnum):
    """Outcome status for forge reports."""

    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


class GatePolicy(StrEnum):
    """Whether a quality gate can fail ``forge check``."""

    BLOCKING = "blocking"
    ADVISORY = "advisory"
