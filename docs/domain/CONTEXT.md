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
| **CRAP score** | Change Risk Anti-Patterns score per function/module: `complexity × (1 - coverage)² + complexity` (standard formula) or simplified variant `complexity + (1 - coverage)³` as configured. | Cyclomatic complexity alone |
| **CRAP threshold** | Maximum allowed CRAP score before flagging (default TBD, prompt suggests 6). | Coverage percentage threshold |
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

## Update policy

Revise CONTEXT when merged work introduces or retires nouns, moves bounded-context boundaries, or changes glossary meaning (link ADR when added).
