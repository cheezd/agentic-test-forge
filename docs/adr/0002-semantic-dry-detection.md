# ADR 0002: Semantic DRY detection (dry4* parity)

**Status:** Accepted  
**Date:** 2026-06-23  
**Epic:** [#122](https://github.com/cheezd/agentic-test-forge/issues/122)  
**Supersedes:** Informal v1 exact-match behavior documented only in code and [#34](https://github.com/cheezd/agentic-test-forge/issues/34)

## Context

Forge v1 DRY analysis (`analysis/dry.py`) fingerprints function bodies with raw `ast.dump()` and reports **exact equality only**. That catches literal copy-paste clones but misses structural near-duplicates — renamed locals, equivalent logic with different identifiers — that Uncle Bob's [dry4clj](https://github.com/unclebob/dry4clj), [dry4go](https://github.com/unclebob/dry4go), and [dry4java](https://github.com/unclebob/dry4java) tools detect via normalization and Jaccard similarity.

Epic [#122](https://github.com/cheezd/agentic-test-forge/issues/122) and discovery grill session (2026-06-23) approved upgrading to semantic DRY while keeping the gate **advisory** per [ADR 0001](0001-package-boundaries-and-refactor-conventions.md).

Alternatives considered:

| Option | Outcome |
|--------|---------|
| Keep exact `ast.dump` only | Rejected — misses primary user value |
| Add `libcst` normalizer | Rejected — new dependency; stdlib sufficient |
| Text/difflib similarity | Rejected — poor structural fidelity |
| dry4go-style full receiver collapse (`obj.foo` → `_._`) | Rejected — grill Option C: attr-only normalization |

## Decision

### Algorithm

1. **Comparison unit:** Python `FunctionDef` / `AsyncFunctionDef` **body** only (signature excluded). Class-qualified names preserved. Nested inner functions are separate units (unchanged collector behavior).

2. **Normalize** incidental tokens via `ast.NodeTransformer` before fingerprinting:
   - `Name.id` → `_`
   - `Constant` → type tag (`_str_`, `_int_`, `_bool_`, `_none_`, …) — literal **values** not distinguished
   - `Attribute.attr` → `_` including call targets (`.get` / `.fetch` → `._`); **do not** collapse receiver base to `_` (grill Option C)
   - Pattern/call incidental names (`MatchAs.name`, `keyword.arg`, etc.) → normalized

3. **Fingerprints:** Walk normalized body subtree; collect `set[str]` of `ast.dump(normalized_subtree)` for the whole body and each nested node.

4. **Similarity:** Jaccard index over fingerprint sets: `score = |A ∩ B| / |A ∪ B|`.

5. **Reporting threshold:** Report pairs with `score ≥ dry_threshold` (default **0.82**). Score **1.00** = identical normalized structure (includes v1 exact clones).

6. **Size filters:** Skip units below `dry_min_lines` (default **4**) or `dry_min_nodes` (default **20**) before pairwise comparison.

7. **Score serialization:** Round to **2 decimal places** in console and JSON.

### Gate and CLI policy

- DRY remains **`GatePolicy.ADVISORY`** — findings appear in output; `ReportStatus.PASS`; `forge check` exit **0** even when duplicates found ([ADR 0001](0001-package-boundaries-and-refactor-conventions.md)).
- Add standalone **`forge dry`** command (grill reversal of epic non-goal) with CLI overrides for threshold, min-lines, min-nodes, path, and JSON output.
- Config keys on `ForgeConfig`: `dry_threshold`, `dry_min_lines`, `dry_min_nodes`.

### Package placement

All algorithm code stays in `analysis/dry.py`. Config in `config/`. Display in `reporting/console.py`. CLI in `cli/main.py`. No new packages ([ADR 0001](0001-package-boundaries-and-refactor-conventions.md)).

### Explicit non-goals

- Multi-language DRY inside forge
- Module-level, class-body, or lambda duplication detection
- Making DRY a blocking gate
- O(n²) bucketing unless profiling proves necessary on large consumer repos

### JSON compatibility

Add fields to `DryFinding` (`similarity_score`, `start_line`, `end_line`, `node_count`) **additively**. Existing fields unchanged.

## Consequences

### Positive

- Near-duplicate detection aligned with dry4* family and Uncle Bob's DRY intent
- Ranked findings improve refactor triage
- `forge dry` enables local analysis without full check pipeline
- Durable normalization rules documented for contributors and agents

### Negative / trade-offs

- O(n²) pairwise comparison may slow very large codebases; mitigated by min-node/min-line filters
- Fuzzy matches require human review — false positives possible at default threshold
- Normalizer must evolve with new Python AST node types
- CONTEXT glossary **DRY violation** definition must be updated (Phase D)

## References

- [Domain language (`CONTEXT.md`)](../domain/CONTEXT.md)
- [Consumer CI guide](../consumer-ci.md)
- [ADR 0001 — package boundaries](0001-package-boundaries-and-refactor-conventions.md)
- Discovery: `workspace/GH-122/research.md` (local, gitignored)
- dry4*: [dry4clj](https://github.com/unclebob/dry4clj) · [dry4go](https://github.com/unclebob/dry4go) · [dry4java](https://github.com/unclebob/dry4java)
