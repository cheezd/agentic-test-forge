# CONTEXT — agentic-test-forge

Canonical domain language for the `agentic_test_forge` library. Ticket research should cite sections here rather than duplicating definitions.

---

## Product purpose

`agentic-test-forge` is a Python library and CLI (`forge`) that enforces Uncle Bob Martin's quality practices for AI-generated and legacy Python codebases: measure complexity and coverage (CRAP), validate tests via mutation (source and Gherkin), and expose a single quality gate for agents and CI.

**Primary use case:** Install into **consumer projects** (other repos in active development) to help clean up, harden, and improve code quality over time. When mature, **`forge check` runs as a CI pipeline gate** — typically after unit tests and coverage collection — blocking merges on threshold failures.

The tool integrates with existing pytest/behave workflows rather than replacing them. Each consumer repo owns its own `[tool.forge]` thresholds and paths.

---

## Ubiquitous language

| Canonical term | Definition | Not to be confused with |
|----------------|------------|-------------------------|
| **Forge** | The CLI entrypoint and overall tool (`forge` command). | Generic "build" or "compile" |
| **Quality gate** | Orchestrated check (`forge check`) running coverage → CRAP → mutation with configurable thresholds; exits non-zero on failure. | A single linter or test run |
| **CRAP score** | Change Risk Anti-Patterns (CRAP) score per function: `complexity² × (1 - coverage)³ + complexity` (standard formula) or simplified variant `complexity + (1 - coverage)³` as configured. Coverage is a 0–1 fraction of executable lines in the function body. | Cyclomatic complexity alone |
| **CRAP threshold** | Maximum allowed CRAP score per function before flagging (default `30`). Fail when `crap_score > threshold`. | Coverage percentage threshold |
| **Mutation score** | Percentage of mutants killed by tests: `(killed / total) × 100`. Reported per file (code) or per scenario (Gherkin) and as an aggregate. | Code coverage percentage |
| **Mutation threshold** | Minimum required mutation score (default `80`, range 0–100). Fail when score **or** aggregate score is **below** threshold. | CRAP score ceiling |
| **Gherkin threshold** | Same semantics as mutation threshold, applied to Gherkin scenario mutations (default `80`). | CRAP score ceiling |
| **Mutation testing** | Introduce small code/scenario changes; tests should fail if they truly validate behavior. | Fuzz testing or property-based testing |
| **Differential mutation** | Run mutation only on changed functions (code) or scenarios (Gherkin), identified via git diff and/or content hashes. | Full-suite mutation every run |
| **Forge hash / manifest** | Stable content hash stored inline (`# forge-hash: abc123`) or in a manifest file to skip unchanged units in differential runs. On save, stale entries for deleted files or removed scenarios are pruned; existing but out-of-scope entries are retained. | Git commit SHA |
| **Code mutation** | mutmut-driven changes to Python source under test. | Gherkin mutation |
| **Gherkin mutation** | Mutations to `.feature` Examples tables (strings, numbers, edge cases); acceptance tests should fail. | Code mutation |
| **Agent report** | Structured JSON plus human-readable Rich summary for programmatic consumption. | Plain pytest output |
| **Consumer project** | A separate Python repository that installs `agentic-test-forge` and configures `[tool.forge]` for local dev and CI. | This library's own repo (dogfooding only) |
| **CI gate** | A CI job step that runs `forge check` (or staged subcommands) and fails the pipeline on non-zero exit. | Pre-commit hook or ad-hoc local run |
| **DRY violation** | Detected duplication signal (basic radon or simple AST checks); advisory, not blocking by default. | CRAP or mutation failure |

Aliases: `agentic-test-forge` (distribution name) → package `agentic_test_forge`.

---

## Score interpretation

Forge reports several related metrics. Threshold config keys (`crap_threshold`, `mutation_threshold`, `gherkin_threshold`) set CI gate cutoffs; the bands below help interpret raw values when triaging findings.

### Cyclomatic complexity (radon)

Shown in `forge crap` output as **Complexity** per function. Radon assigns one point per decision path (branches, loops, comprehensions, etc.).

| Complexity | Risk level | Interpretation & recommendations |
|------------|------------|----------------------------------|
| 1–10 | Low | Simple and straightforward. Easy to understand, test, and maintain. Ideal range. |
| 11–20 | Moderate | Becoming complex. Still manageable but should be monitored. Consider breaking down large functions. |
| 21–50 | High | Very complex. High chance of bugs. Difficult to test thoroughly. Refactoring strongly recommended. |
| 51+ | Very high | Extremely complex. Hard to test fully. Must be refactored or decomposed. |

### Function coverage (CRAP input)

Shown in `forge crap` output as **Coverage** (percentage of executable lines in the function body). Used with complexity to compute CRAP.

| Coverage | Risk level | Interpretation & recommendations |
|----------|------------|----------------------------------|
| 100% | Low | Function body fully exercised by tests. |
| 80–99% | Low–moderate | Mostly covered; inspect uncovered branches or edge paths. |
| 50–79% | Moderate–high | Significant gaps; CRAP rises quickly as complexity increases. Add targeted tests. |
| 1–49% | High | Poorly tested relative to structure; prioritize tests before adding behavior. |
| 0% | Very high | Untested function; any non-trivial complexity produces a high CRAP score. |

### CRAP score

Shown in `forge crap` output as **CRAP** per function. Combines complexity and coverage: untested complex code scores highest. Default gate: `crap_threshold = 30` (fail when any function exceeds the threshold).

| CRAP score | Risk level | Interpretation & recommendations |
|------------|------------|----------------------------------|
| ≤ 10 | Low | Healthy function; maintain current tests when changing behavior. |
| 11–30 | Moderate | Acceptable for many codebases; monitor if complexity is still rising. Default gate treats 30 as the upper bound. |
| 31–50 | High | Over the usual “CRAP” line; refactor, simplify, or improve coverage. |
| 51+ | Very high | Dangerous change-risk hotspot; refactor and test before further feature work. |

With **full coverage**, standard-formula CRAP equals cyclomatic complexity (e.g. complexity 10 → CRAP 10). Low coverage amplifies CRAP superlinearly for complex functions.

### Mutation score (code and Gherkin)

Shown in `forge mutate` / `forge mutate-gherkin` output as **Score** (`killed / total`, 0–100%). Measures whether tests detect intentional behavior changes—not line coverage. Default gate: `mutation_threshold = 80` / `gherkin_threshold = 80` (fail when score is below the threshold).

| Mutation score | Risk level | Interpretation & recommendations |
|----------------|------------|----------------------------------|
| 90–100% | Low | Strong tests; mutants are consistently detected. |
| 80–89% | Moderate | Meets the default gate; review surviving mutants for weak assertions or missing cases. |
| 60–79% | High | Tests pass despite many behavior changes; strengthen assertions and edge-case coverage. |
| 40–59% | Very high | Tests likely check implementation details or happy paths only. |
| < 40% | Critical | Tests provide little behavioral protection; treat as a testing gap, not a tuning issue. |

Gates evaluate **per file or scenario** and the **aggregate** score across mutated units—either failing is a gate failure.

### Choosing thresholds

| Config key | Direction | Typical starting point | Rollout note |
|------------|-----------|------------------------|--------------|
| `crap_threshold` | Ceiling (lower is stricter) | `30` (default) | Legacy repos may start at `50` and ratchet down (see [`consumer-ci.md`](../consumer-ci.md)). |
| `mutation_threshold` | Floor (higher is stricter) | `80` (default) | Enable on Linux CI after CRAP is stable; raise toward `90` for critical modules. |
| `gherkin_threshold` | Floor (higher is stricter) | `80` (default) | Same as mutation; applies to acceptance scenarios. |

---

## Bounded contexts

| Context | Responsibility | Integration surface |
|---------|----------------|---------------------|
| **Analysis** | CRAP scoring, DRY flagging, radon/coverage ingestion | Reads coverage data; exposes `analyze()` API and `forge crap` |
| **Code mutation** | mutmut wrapper, differential scope, multiprocessing | Invokes pytest test runner; `forge mutate` (planned) |
| **Gherkin mutation** | Parse/mutate `.feature` files, scenario hashes, run acceptance tests | behave/pytest-bdd runners; `forge mutate-gherkin` |
| **Orchestration** | Config, pipeline ordering, thresholds, exit codes, reporting | `forge check`; `[tool.forge]` config |
| **CLI / reporting** | Typer commands, Rich output, JSON serialization | stdout, exit codes, programmatic API |

Boundaries: Analysis does not mutate code. Mutation contexts do not compute CRAP. Orchestration coordinates but delegates execution.

---

## Core domain constraints

- Python 3.11+ only.
- **Consumer CI is a first-class deployment target** — `forge check` must be reliable, documented, and fast enough for PR pipelines (differential mode is essential, not optional).
- CI/pre-commit must receive non-zero exit codes when any configured gate fails.
- Differential runs must be deterministic given the same inputs and manifest state.
- Manifest saves prune entries whose keys no longer refer to live repo entities (deleted `.py` files or removed Gherkin scenarios). Entries for existing files/scenarios are retained even when outside the current git diff scope. `--full` bypasses manifest skip during scope selection only; pruning still runs on save.
- Library must be installable into other repos (editable, VCS, or PyPI) without coupling to this repo's layout.
- Library must be usable programmatically (agents call API, not only CLI).
- Self-tests must demonstrate the library eats its own dogfood (coverage, low CRAP).
- Consumer integration must not require forking this library — configuration lives in the consumer's `pyproject.toml`.

---

## External systems

| System | Why we integrate | Notes |
|--------|------------------|-------|
| **radon** | Cyclomatic complexity | Required for CRAP |
| **coverage.py** | Line/branch coverage data | Required for CRAP; pytest-cov in CI |
| **mutmut** | Python mutation testing | Differential mode is custom layer |
| **pytest** | Unit/integration test runner | Primary test runner |
| **behave / pytest-bdd** | Gherkin acceptance tests | Parser must tolerate both dialects where feasible |
| **git** | Diff for differential scope | Baseline for PR-scoped CI runs (`origin/main...HEAD`) |
| **GitHub Actions / CI** | Primary consumer deployment | Document standard job: test → coverage → `forge check` |

---

## Architecture decisions

Structural and policy decisions are recorded as ADRs. See the [ADR index](../adr/README.md) for when to write one, numbering, and the Context / Decision / Consequences template. [ADR 0001](../adr/0001-package-boundaries-and-refactor-conventions.md) covers package boundaries, refactor conventions, and exit-code mapping.

---

## Update policy

Revise CONTEXT when merged work introduces or retires nouns, moves bounded-context boundaries, or changes glossary meaning. Link or add an [ADR](../adr/README.md) when the change reflects a durable architectural decision.
