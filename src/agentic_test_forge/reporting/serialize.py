"""Shared JSON serialization for forge report dataclasses."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, cast


def serialize_findings_report(report: Any, *, findings_field: str = "findings") -> dict[str, Any]:
    """Serialize a report dataclass, expanding nested finding dataclasses."""
    if not is_dataclass(report):
        msg = f"Expected dataclass report, got {type(report)!r}"
        raise TypeError(msg)

    payload = asdict(cast(Any, report))
    findings = getattr(report, findings_field)
    payload[findings_field] = [asdict(finding) for finding in findings]
    return payload


def report_to_json(report: Any, *, indent: int = 2, findings_field: str = "findings") -> str:
    """Return JSON for a findings-based report."""
    return json.dumps(
        serialize_findings_report(report, findings_field=findings_field),
        indent=indent,
    )
