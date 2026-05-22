"""Parse mutmut output into forge mutation reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ReportStatus = Literal["pass", "fail"]

KILLED_EXIT_CODES = {1, 3, -24}


@dataclass(frozen=True)
class MutationFinding:
    """Mutation score for one source file."""

    filepath: str
    score: float
    killed: int
    total: int
    above_threshold: bool


@dataclass(frozen=True)
class MutationReport:
    """Aggregate mutation testing report."""

    tool: str
    status: ReportStatus
    threshold: float
    findings: tuple[MutationFinding, ...]
    summary: str
    skipped_unchanged: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [asdict(finding) for finding in self.findings]
        return payload

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def compute_mutation_score(killed: int, total: int) -> float:
    if total == 0:
        return 100.0
    return (killed / total) * 100.0


def _status_for_exit_code(exit_code: int | None) -> str:
    if exit_code is None:
        return "not_checked"
    if exit_code in KILLED_EXIT_CODES:
        return "killed"
    if exit_code == 0:
        return "survived"
    if exit_code in {33, 34}:
        return "skipped"
    if exit_code in {36, 24, -24, 255, 152}:
        return "timeout"
    return "other"


def parse_mutmut_meta(meta_path: Path) -> tuple[int, int]:
    """Return killed and total mutant counts from a mutmut meta file."""
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    exit_codes = payload.get("exit_code_by_key", {})
    if not isinstance(exit_codes, dict):
        return 0, 0

    killed = 0
    total = 0
    for raw_code in exit_codes.values():
        if raw_code is None:
            continue
        total += 1
        if _status_for_exit_code(int(raw_code)) == "killed":
            killed += 1
    return killed, total


def build_findings_from_meta(
    project_root: Path,
    filepaths: list[Path],
    *,
    threshold: float,
) -> list[MutationFinding]:
    findings: list[MutationFinding] = []
    for filepath in filepaths:
        relative = filepath.relative_to(project_root)
        meta_path = project_root / "mutants" / f"{relative.as_posix()}.meta"
        if not meta_path.is_file():
            findings.append(
                MutationFinding(
                    filepath=str(relative).replace("\\", "/"),
                    score=0.0,
                    killed=0,
                    total=0,
                    above_threshold=True,
                ),
            )
            continue

        killed, total = parse_mutmut_meta(meta_path)
        score = compute_mutation_score(killed, total)
        findings.append(
            MutationFinding(
                filepath=str(relative).replace("\\", "/"),
                score=score,
                killed=killed,
                total=total,
                above_threshold=score < threshold,
            ),
        )
    return findings


def build_mutation_report(
    *,
    threshold: float,
    findings: list[MutationFinding],
    skipped_unchanged: list[str],
    selected_count: int,
) -> MutationReport:
    if selected_count == 0:
        summary = "No changed Python files require mutation testing."
        return MutationReport(
            tool="mutation",
            status="pass",
            threshold=threshold,
            findings=tuple(findings),
            summary=summary,
            skipped_unchanged=tuple(skipped_unchanged),
        )

    if not findings:
        summary = f"Mutation testing completed for {selected_count} file(s)."
        return MutationReport(
            tool="mutation",
            status="pass",
            threshold=threshold,
            findings=(),
            summary=summary,
            skipped_unchanged=tuple(skipped_unchanged),
        )

    violations = [finding for finding in findings if finding.above_threshold]
    aggregate_killed = sum(finding.killed for finding in findings)
    aggregate_total = sum(finding.total for finding in findings)
    aggregate_score = compute_mutation_score(aggregate_killed, aggregate_total)
    status: ReportStatus = "fail" if violations or aggregate_score < threshold else "pass"

    if violations:
        summary = (
            f"{len(violations)} file(s) below mutation threshold {threshold}% "
            f"(aggregate score {aggregate_score:.1f}%)."
        )
    else:
        summary = (
            f"All {len(findings)} mutated file(s) meet mutation threshold "
            f"{threshold}% (aggregate score {aggregate_score:.1f}%)."
        )

    return MutationReport(
        tool="mutation",
        status=status,
        threshold=threshold,
        findings=tuple(findings),
        summary=summary,
        skipped_unchanged=tuple(skipped_unchanged),
    )
