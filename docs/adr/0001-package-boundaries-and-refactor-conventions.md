# ADR 0001: Package boundaries and refactor conventions

**Status:** Accepted  
**Date:** 2026-05-23  
**Epic:** [#100](https://github.com/cheezd/agentic-test-forge/issues/100) · Issue [#105](https://github.com/cheezd/agentic-test-forge/issues/105)  
**Supersedes:** Informal layout notes in Round 1/2 refactor research (committed inventory: [`round-2-inventory.md`](../refactor-analysis/round-2-inventory.md))

## Context

Epic [#82](https://github.com/cheezd/agentic-test-forge/issues/82) (Round 1) and [#106](https://github.com/cheezd/agentic-test-forge/issues/106) (Round 2) refactored public pipelines and inner helpers without a single contributor-facing record of package responsibilities, dependency direction, or where new shared code belongs. Epic [#100](https://github.com/cheezd/agentic-test-forge/issues/100) completed follow-up orchestration, scope, parser, and manifest work (#101–#104).

This ADR documents the **post–Round 2 layout** so future changes stay consistent.

## Decision

### Package map and dependency direction

Dependencies flow **inward** toward leaf packages. Lower layers must not import `cli`, `orchestration`, `analysis`, or `mutation`.

```
cli/
  └─► orchestration/, analysis/, mutation/, config/, reporting/, cli/helpers, cli/exit_codes

orchestration/
  └─► analysis/, mutation/, config/, reporting/status, errors

analysis/          mutation/code/          mutation/gherkin/
  └─► scope/         └─► scope/                └─► scope/, parser/, mutator/, …
  └─► reporting/     └─► manifest/             └─► manifest/
  └─► errors         └─► reporting/            └─► reporting/, config/
                     └─► config (types)

scope/             manifest/               config/
  └─► errors         └─► (stdlib only)         └─► errors, reporting/status

reporting/         errors.py (root)
  └─► status/threshold/serialize are leaves
  └─► console* may import domain report dataclasses for display
```

| Package | Responsibility | Public entrypoints (examples) |
|---------|----------------|------------------------------|
| `cli/` | Typer commands, config overrides, exit-code mapping | `forge` via `cli/main.py`, `cli/helpers.py`, `cli/exit_codes.py` |
| `config/` | Load and validate `[tool.forge]` | `load_config`, `ForgeConfig`, `GateConfig`, `config/parsers.py` |
| `orchestration/` | Multi-gate pipeline for `forge check` | `run_quality_check`, `CheckReport` |
| `analysis/` | CRAP and DRY analyzers | `analyze_crap`, `analyze_dry` |
| `mutation/code/` | mutmut differential mutation | `analyze_mutation`, `resolve_mutation_scope` |
| `mutation/gherkin/` | Examples-table mutation | `analyze_gherkin_mutation`, `resolve_gherkin_scope`, `parser.py` |
| `scope/` | Shared git diff and path resolution | `run_git_diff_names`, `normalize_paths`, `iter_files_by_suffix` |
| `manifest/` | Differential state persistence | `load_manifest`, `save_manifest`, `partition_by_manifest_hash`, `prune_stale_manifest_entries` |
| `reporting/` | Status enums, thresholds, JSON/console output | `ReportStatus`, `GatePolicy`, `reporting/console.py` |
| `errors.py` | Shared exception types | `ForgeToolError`, `ConfigError` |

**Bounded contexts** (see [`CONTEXT.md`](../domain/CONTEXT.md)): analysis does not mutate code; mutation does not compute CRAP; orchestration coordinates but delegates execution.

### Where new shared helpers should live

| Need | Location | Notes |
|------|----------|-------|
| Git diff or path walking used by multiple gates | `scope/` | Introduced in Round 1 (#83). Domain scope modules compose these helpers. |
| Manifest load/save, hash skip partition, stale prune | `manifest/` | `partition_by_manifest_hash` (#102), `prune_stale_manifest_entries` (#104). |
| Gate-specific scope (Python files vs Gherkin scenarios) | `mutation/code/scope.py`, `mutation/gherkin/scope.py` | Compose `scope/` + `manifest/`; do not duplicate git/path loops. |
| Config value parsing | `config/parsers.py` | Keep `loader.py` as orchestration only. |
| Report status / threshold / JSON shape | `reporting/` | Domain reports (`CrapReport`, etc.) stay in their bounded context; use `reporting/status.py` for shared status. |
| Rich console formatting | `reporting/console.py`, `reporting/console_helpers.py` | No subprocess or analysis logic. |
| Process exit codes | `cli/exit_codes.py` | Map `ReportStatus` / `CheckReport` → `ForgeExitCode`; see [Consumer CI](../consumer-ci.md#exit-codes). |
| Gate orchestration loops | `orchestration/check.py` | Use small helpers (e.g. `_run_blocking_gate`, #101) instead of repeated try/except blocks. |

**Rule of thumb:** extract to the **lowest package** that has no upward dependency. If two mutation gates need it, prefer `scope/` or `manifest/` over `mutation/`.

### Refactor conventions

1. **Preserve public API shape** — `analyze_*`, `run_quality_check`, CLI flags, and report dataclass fields remain stable unless a ticket explicitly changes behavior.
2. **Orchestration vs leaves** — Top-level functions call named steps only; one level of abstraction per function (Round 2 SLA). See [`round-2-inventory.md`](../refactor-analysis/round-2-inventory.md).
3. **Characterization tests before behavior changes** — Especially parser line indices (#103) and manifest prune policy (#104).
4. **One issue per PR** — Close the tracking issue on merge.
5. **Do not re-split Round 2 modules** unless a new ticket requires behavior changes in `analysis/crap.py`, `analysis/dry.py`, `mutation/code/analyze.py`, or `mutation/gherkin/analyze.py`.

### Exit codes and report status

Two layers:

| Layer | Type | Values | Used by |
|-------|------|--------|---------|
| Report payload | `ReportStatus` (`reporting/status.py`) | `pass`, `fail`, `error` | Individual gate reports and `CheckReport.status` |
| Process exit | `ForgeExitCode` (`cli/exit_codes.py`) | `0` SUCCESS, `1` GATE_FAILURE, `2` TOOL_ERROR | CLI / CI |

Mapping policy:

- **`fail`** on a **blocking** gate (CRAP, mutation, Gherkin) → exit `1`.
- **`ForgeToolError`** or `CheckReport.errors` → report `error`, exit `2`.
- **DRY** uses `GatePolicy.ADVISORY` — findings appear in output but never fail `forge check`.
- Standalone commands (`forge crap`, etc.) use `exit_for_report_status`; `forge check` uses `exit_for_check_report`.

Authoritative CI table: [`docs/consumer-ci.md`](../consumer-ci.md#exit-codes).

### Manifest dual-use (`ForgeManifest`)

One envelope type serves both mutation gates:

| File | Path helper | Key format | Value |
|------|-------------|------------|-------|
| Code mutation | `manifest_path(manifest_dir)` → `mutation-manifest.json` | POSIX path relative to project root (e.g. `src/foo.py`) | `FileManifestEntry` |
| Gherkin mutation | `gherkin_manifest_path(manifest_dir)` → `gherkin-manifest.json` | `scenario_id` (`{feature}::{name}`) | `FileManifestEntry` |

Conventions:

- **`ForgeManifest.files`** is the sole map; `MutationManifest` is a backward-compatible alias.
- **Merge on save** — analyzers merge new findings into existing `files`, then prune stale keys, then `save_manifest`.
- **Prune on save (#104)** — drop entries whose keys no longer refer to live repo entities (deleted `.py` files or removed scenarios). Retain entries for existing files/scenarios even when outside the current git-diff scope. `--full` bypasses manifest *skip* during scope selection only; pruning still runs on save. Details in [`CONTEXT.md`](../domain/CONTEXT.md).
- **Differential skip** — `partition_by_manifest_hash` compares `content_hash` for scoped items; unchanged entries skip re-run.

## Consequences

### Positive

- Contributors and agents have a single reference for layout and extraction targets.
- Dependency direction reduces circular imports and keeps `scope/` / `manifest/` reusable.
- Exit and manifest policies are explicit for CI operators.

### Negative / trade-offs

- `reporting/console.py` imports domain report types for display (acceptable presentation-layer coupling).
- Prune-on-save may remove orphaned keys before an operator inspects them; acceptable for manifest size and clarity.

## References

- [Domain language (`CONTEXT.md`)](../domain/CONTEXT.md)
- [Consumer CI guide](../consumer-ci.md)
- [Round 2 refactor inventory](../refactor-analysis/round-2-inventory.md)
- Round 1 epic [#82](https://github.com/cheezd/agentic-test-forge/issues/82); Round 2 epic [#106](https://github.com/cheezd/agentic-test-forge/issues/106); follow-up epic [#100](https://github.com/cheezd/agentic-test-forge/issues/100)
