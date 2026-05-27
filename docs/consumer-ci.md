# Consumer CI Integration Guide

Install `agentic-test-forge` into a Python consumer repository and run `forge check` as a merge gate after unit tests and coverage collection.

## Prerequisites

- Python 3.11+
- `pytest` with `pytest-cov` (or equivalent coverage workflow)
- Git history available in CI (for differential mutation scope)
- Linux runners for code mutation (`mutmut` does not run natively on Windows)

## Install

From PyPI:

```bash
pip install agentic-test-forge==1.0.0
```

From Git (fallback):

```bash
pip install "agentic-test-forge @ git+https://github.com/cheezd/agentic-test-forge.git@v1.0.0"
```

For local development:

```bash
pip install -e /path/to/agentic-test-forge
```

## Configure the consumer repo

Add to `pyproject.toml`:

```toml
[tool.forge]
paths = ["src/my_package"]
crap_threshold = 30
mutation_threshold = 80
mutation_base_ref = "main"
mutation_test_cmd = "pytest"
gherkin_paths = ["features"]
gherkin_test_cmd = "behave"

[tool.forge.gates]
crap = true
mutation = false   # enable on Linux runners when ready
gherkin = false    # enable when behave/pytest-bdd is configured
dry = true         # advisory duplication scan
```

## GitHub Actions example

```yaml
name: Quality

on:
  pull_request:
  push:
    branches: [main]

jobs:
  forge-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install agentic-test-forge==1.0.0

      - name: Run tests with coverage
        run: pytest --cov=src --cov-report=xml

      - name: Run forge quality gate
        run: forge check --path src/ --json forge-report.json

      - name: Upload forge report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: forge-report
          path: forge-report.json
```

## Staged rollout

For legacy repositories, enable gates incrementally:

1. **Week 1:** `crap = true` only — fix high-CRAP hotspots
2. **Week 2:** add `dry = true` — refactor obvious duplication
3. **Week 3+:** enable `mutation` on Linux CI; then `gherkin` when BDD tests exist

Use advisory thresholds initially (`crap_threshold = 50`) and ratchet down over time. See [score interpretation](domain/CONTEXT.md#score-interpretation) for what CRAP and mutation values mean.

## Pre-commit hook

Optional local gate before commit. The hook runs `forge check` and reads the same
`[tool.forge]` / `[tool.forge.gates]` config as CI — no duplicate parsing.

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/cheezd/agentic-test-forge
    rev: v1.0.0
    hooks:
      - id: forge-check
        # Optional overrides (defaults match forge check):
        # args: [--path, src/, --coverage-file, .coverage]
```

Install hooks:

```bash
pip install pre-commit agentic-test-forge==1.0.0
pre-commit install
```

Run manually (same as CI smoke):

```bash
pre-commit run forge-check --all-files
```

### Coverage prerequisite

The CRAP gate needs a `.coverage` file from your test run (same as CI). Typical
local workflow — run tests with coverage, then commit (hook runs on staged Python
files):

```bash
pytest --cov=src
pre-commit run forge-check --all-files
```

Or chain a local hook before `forge-check`:

```yaml
  - repo: local
    hooks:
      - id: pytest-cov
        name: pytest with coverage
        entry: pytest --cov=src --cov-report=
        language: system
        pass_filenames: false
        always_run: true
```

### Windows and mutation

Keep `mutation = false` in `[tool.forge.gates]` for local pre-commit on Windows
(mutmut does not run natively). Use Linux CI for mutation gates. If mutation is
enabled on Windows, `forge check` exits **2** with a clear error — it does not crash.

Exit codes match [CI exit codes](#exit-codes) (0 pass, 1 gate failure, 2 tool error).

## Exit codes

Defined by `ForgeExitCode` in `agentic_test_forge.cli.exit_codes`. Package layout and status/exit mapping policy: [ADR 0001](adr/0001-package-boundaries-and-refactor-conventions.md#exit-codes-and-report-status).

| Code | Enum | Meaning |
|------|------|---------|
| `0` | `SUCCESS` | All enabled blocking gates passed |
| `1` | `GATE_FAILURE` | Threshold failure in CRAP, mutation, or Gherkin gate |
| `2` | `TOOL_ERROR` | Tool/precondition error (missing `.coverage`, git error, mutmut unavailable) |

DRY findings are **advisory** — they appear in the combined report but do not fail `forge check`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Coverage data not found` | Run `pytest --cov=...` before `forge check` or the pre-commit hook |
| `mutmut does not support native Windows` | Use `ubuntu-latest` runners for mutation |
| `git diff failed` | Ensure `fetch-depth: 0` in checkout |
| Gate blocks every PR on legacy code | Raise thresholds temporarily; enable one gate at a time |
