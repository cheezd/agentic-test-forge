# Gherkin Authoring For Agents

Rules for AI agents writing `.feature` files in consumer repositories monitored by **agentic-test-forge**. Pair with lifecycle prompts in [Django Building and Testing Guides](https://github.com/cheezd/Django-Building-and-Testing-Guides) (`09-gherkin-acceptance-specification-prompt.md`, `10-gherkin-step-definitions-and-forge-integration.md`).

## Purpose

Gherkin is the **acceptance contract**: human-readable, implementation-agnostic, executable end-to-end. Forge validates that contract with **Gherkin mutation** (`forge mutate-gherkin`): it mutates Examples table cells and expects acceptance tests to fail when behavior should change.

## Forge Parser Behavior

| Concept | Forge behavior |
|---------|----------------|
| Scenario ID | `{filepath}::{scenario name}` (e.g. `features/billing/invoice.feature::Create invoice`) |
| Mutation scope | Changed `.feature` files (git diff vs `gherkin_base_ref`) + scenarios with **Examples** tables |
| Plain `Scenario:` | Parsed but **not** mutation-tested (no Examples to mutate) |
| Manifest | `.forge/gherkin-manifest.json` — content hash per scenario; skip unchanged on differential runs |
| Runners | `behave` (runs `--name {scenario}`) or `pytest` (runs whole feature file) |

**Authoring rule:** prefer **Scenario Outline + Examples** for any behavior with inputs, outputs, or data variations.

## Agent Rules

1. **No production code** during spec authoring — only `.feature` files and review artifacts.
2. **Ubiquitous language** — terms from `docs/domain/CONTEXT.md`; no internal module/class names in steps.
3. **Externally visible behavior** — HTTP status, response body fields, persisted state, user-visible messages.
4. **Traceability** — every ticket acceptance criterion maps to at least one scenario.
5. **Reuse step phrases** — identical wording across scenarios so step definitions stay DRY.
6. **Tag with ticket ID** — e.g. `@GH-42` for scope filtering and audit.
7. **Examples must matter** — table cells drive assertions; forge mutates these cells.

## Recommended Feature Shape

```gherkin
@GH-42
Feature: Invoice creation

  Scenario Outline: Create invoice with valid amount
    Given an authenticated user with billing access
    When they request an invoice for <amount>
    Then the response status is <status>
    And the invoice total is <amount>

    Examples:
      | amount | status |
      | 10.00  | 201    |
      | 0.01   | 201    |
      | 0      | 400    |
```

## What Forge Mutates

For each cell in an Examples table, forge generates candidates:

- **Strings:** empty, suffix `_mutated`, boolean toggle
- **Numbers:** ±1, zero

Acceptance tests **kill** the mutant when they fail (non-zero exit). Surviving mutants indicate weak specs or step definitions that ignore table parameters.

## Layout Conventions

```text
features/
├── acceptance/{bounded_context}/{behavior}.feature
├── steps/{context}_steps.py
└── environment.py          # behave-django setup
```

Draft specs before sign-off: `workspace/{ticket}/acceptance/draft/`.

## Configuration

```toml
[tool.forge]
gherkin_paths = ["features"]
gherkin_runner = "behave"
gherkin_test_cmd = "behave"
gherkin_threshold = 80
gherkin_base_ref = "main"

[tool.forge.gates]
gherkin = false   # enable after acceptance tests are green
```

## Verification Sequence

```bash
behave features/
forge mutate-gherkin --path features/ --base main --threshold 80
forge check --path src/ --features-path features/
```

## Anti-Patterns

| Anti-pattern | Why it fails forge discipline |
|--------------|-------------------------------|
| Plain Scenario only, no Examples | Skipped by Gherkin mutation scope |
| Steps reference Python class names | Breaks ATDD; couples spec to implementation |
| Examples with decorative unused columns | Mutation may not affect assertions |
| Duplicate scenario names in one file | Ambiguous scenario IDs |
| Skipping human sign-off | Spec drift; weak acceptance contract |

## Reference Implementation

See the in-repo pilot: `pilot/features/sample.feature`, `pilot/features/steps/calculator_steps.py`, and `pilot/README.md`.

## Related Docs

- [Consumer CI](consumer-ci.md) — GitHub Actions, Django monorepo, staged gates
- [Domain CONTEXT](domain/CONTEXT.md) — score interpretation, glossary
- [Django guides — acceptance spec prompt](https://github.com/cheezd/Django-Building-and-Testing-Guides/blob/main/tests/guides/09-gherkin-acceptance-specification-prompt.md)
