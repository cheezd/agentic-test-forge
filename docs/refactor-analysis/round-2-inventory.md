# Round 2 — inner-function SLA inventory

**Epic:** [#106](https://github.com/cheezd/agentic-test-forge/issues/106) — Refactor Round 2: inner-function SLA and readability  
**Issue:** [#111](https://github.com/cheezd/agentic-test-forge/issues/111)  
**Date:** 2026-05-23

Local working copy of the broader refactor research lives at `workspace/refactor-analysis/research.md` (gitignored). This file is the **committed** Round 2 inventory for agents and reviewers.

**Principle:** Orchestration calls named steps only; leaves do one thing; named types over opaque tuple keys.

## Sub-issues and PRs

| Issue | Module | PR | Status |
|-------|--------|-----|--------|
| [#107](https://github.com/cheezd/agentic-test-forge/issues/107) | `analysis/crap.py` | [#112](https://github.com/cheezd/agentic-test-forge/pull/112) | Merged |
| [#108](https://github.com/cheezd/agentic-test-forge/issues/108) | `analysis/dry.py` | [#113](https://github.com/cheezd/agentic-test-forge/pull/113) | Merged |
| [#109](https://github.com/cheezd/agentic-test-forge/issues/109) | `mutation/code/analyze.py` | [#114](https://github.com/cheezd/agentic-test-forge/pull/114) | Merged |
| [#110](https://github.com/cheezd/agentic-test-forge/issues/110) | `mutation/gherkin/analyze.py` | [#115](https://github.com/cheezd/agentic-test-forge/pull/115) | Merged |
| [#111](https://github.com/cheezd/agentic-test-forge/issues/111) | This document | [#116](https://github.com/cheezd/agentic-test-forge/pull/116) | In progress |

## `analysis/crap.py` (#107)

**Before:** `_collect_crap_findings` mixed file read, coverage path match, radon `cc_visit`, per-function coverage math, CRAP scoring, `CrapFinding` construction, and sort in one loop.

**After (orchestration + leaves):**

```python
_coverage_lines_for_file(data, filepath) -> set[int]
_function_blocks_from_source(source) -> list[Function]
_finding_from_radon_block(block, filepath, line_set, *, threshold, formula) -> CrapFinding
_findings_for_file(filepath, data, *, threshold, formula) -> list[CrapFinding]  # file-level orchestration
_collect_crap_findings(python_files, data, *, threshold, formula) -> list[CrapFinding]  # orchestration only
```

Public `analyze_crap` unchanged in shape; calls `_collect_crap_findings` → `_build_crap_report`.

## `analysis/dry.py` (#108)

**Before:** `_find_duplicate_pairs` used opaque 4-tuple `(name, file, other_name, other_file)` dedupe keys; `_index_function_fingerprints` mixed parse + index in one loop.

**After:**

```python
@dataclass DuplicatePair  # normalized() / reverse for A↔B dedupe

_parse_python_file(filepath) -> ast.AST | None
_register_file_fingerprints(fingerprints, tree, filepath) -> None
_index_function_fingerprints(python_files) -> tuple[dict, tuple[str, ...]]
_pairs_from_fingerprint_entries(entries) -> list[DuplicatePair]
_finding_from_duplicate_pair(pair) -> DryFinding
_find_duplicate_pairs(fingerprints) -> list[DryFinding]  # orchestration only
```

## `mutation/code/analyze.py` (#109)

**Before:** `_run_mutation_tool` inlined path conversion; `_persist_mutation_manifest` mixed load, hash, entry build, and save in one loop; empty-scope report built inline in `analyze_mutation`.

**After:**

```python
_relative_paths(paths, root) -> list[str]
_skipped_relative_paths(scope, root) -> list[str]
_selected_relative_paths(scope, root) -> list[str]
_run_mutation_tool(*, root, scope, run_mutmut_tool, test_cmd) -> None
_manifest_entry_for_finding(root, finding, *, timestamp) -> FileManifestEntry | None
_updated_manifest_files(manifest, findings, *, root, timestamp) -> dict[str, FileManifestEntry]
_persist_mutation_manifest(*, root, findings, manifest_dir) -> None
_empty_mutation_report(*, threshold, skipped) -> MutationReport
analyze_mutation(...) -> MutationReport  # orchestration only
```

## `mutation/gherkin/analyze.py` (#110)

**Before:** `analyze_gherkin_mutation` inlined mutator loop and manifest merge; `evaluate_scenario` duplicated mutator construction.

**After:**

```python
_skipped_scenario_ids(scope) -> list[str]
_create_scenario_mutator(*, project_root, test_cmd, runner, run_tests) -> ScenarioMutator
_finding_for_scenario(mutator, scenario, *, threshold) -> GherkinFinding
_findings_for_scenarios(mutator, scenarios, *, threshold) -> list[GherkinFinding]
_manifest_entry_for_scenario(scenario, finding, *, timestamp) -> FileManifestEntry
_updated_gherkin_manifest_files(manifest, scenarios, findings, *, timestamp) -> dict[str, FileManifestEntry]
_persist_gherkin_manifest(*, scenarios, findings, manifest_dir) -> None
_empty_gherkin_mutation_report(*, threshold, skipped) -> GherkinMutationReport
evaluate_scenario(...) -> GherkinFinding  # reuses mutator + finding leaves
analyze_gherkin_mutation(...) -> GherkinMutationReport  # orchestration only
```

## Remaining mixed-level functions (deferred)

Round 2 scope stopped at private helpers inside the four modules above. These are **intentionally out of scope** — tracked elsewhere or low priority:

| Function | File | Why deferred |
|----------|------|--------------|
| `_findings_for_file` | `analysis/crap.py` | File-level orchestration; single inline `read_text` remains. Extract `_read_python_source` only if a third caller appears. |
| `build_findings_from_meta` | `mutation/code/report.py` | Meta JSON parse + score loop; not in Round 2 module list. |
| `ScenarioMutator.apply_and_test` | `mutation/gherkin/mutator.py` | Mutation generation, temp-file edit, subprocess, scoring — decomposed in Round 1 (#84) via `FeatureFileEditor`; further split is epic [#100](https://github.com/cheezd/agentic-test-forge/issues/100) territory. |
| `parse_feature_file` | `mutation/gherkin/parser.py` | [#103](https://github.com/cheezd/agentic-test-forge/issues/103) |
| `resolve_mutation_scope` / `resolve_gherkin_scope` | `mutation/*/scope.py` | Git diff + manifest skip; [#102](https://github.com/cheezd/agentic-test-forge/issues/102) |
| `run_quality_check` | `orchestration/check.py` | Repeated gate blocks; [#101](https://github.com/cheezd/agentic-test-forge/issues/101) |
| CLI commands | `cli/main.py` | Round 1 [#86](https://github.com/cheezd/agentic-test-forge/issues/86) extracted helpers; commands still compose config + analyze + print. |
| Console printers | `reporting/console.py` | Round 1 [#89](https://github.com/cheezd/agentic-test-forge/issues/89) |

**Stop here for Round 2.** Future agents should not re-split Round 1 public pipelines or redo the four refactored modules unless behavior changes require it.

Contributor-facing package boundaries and refactor rules: [ADR 0001](../adr/0001-package-boundaries-and-refactor-conventions.md).

## Related epics

- Round 1: [#82](https://github.com/cheezd/agentic-test-forge/issues/82) (PRs #94–#99)
- Round 2: [#106](https://github.com/cheezd/agentic-test-forge/issues/106) (this inventory)
- Follow-up orchestration/parser work: [#100](https://github.com/cheezd/agentic-test-forge/issues/100) (#101–#105)
