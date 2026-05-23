"""Score Gherkin scenario mutation results."""

from __future__ import annotations

from agentic_test_forge.mutation.code.report import compute_mutation_score
from agentic_test_forge.mutation.gherkin.report import GherkinFinding

# Dry-run skips subprocess execution. Non-zero exit codes count as "killed" mutations,
# matching prior behavior when run_tests=False assumed exit code 1.
DRY_RUN_MUTATION_EXIT_CODE = 1


def score_mutations(
    *,
    scenario_id: str,
    killed: int,
    total: int,
    threshold: float,
) -> GherkinFinding:
    """Build a finding from killed/total mutation counts."""
    score = compute_mutation_score(killed, total)
    return GherkinFinding(
        scenario_id=scenario_id,
        score=score,
        killed=killed,
        total=total,
        above_threshold=score < threshold,
    )
