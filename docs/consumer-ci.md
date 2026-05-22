# Consumer CI Integration Guide

Install `agentic-test-forge` into a Python consumer repository and run `forge check` as a merge gate after unit tests and coverage collection.

## Prerequisites

- Python 3.11+
- `pytest` with `pytest-cov` (or equivalent coverage workflow)
- Git history available in CI (for differential mutation scope)
- Linux runners for code mutation (`mutmut` does not run natively on Windows)

## Install

Until PyPI publish, pin from Git:

```bash
pip install "agentic-test-forge @ git+https://github.com/cheezd/agentic-test-forge.git@main"
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
          pip install "agentic-test-forge @ git+https://github.com/cheezd/agentic-test-forge.git@main"

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

Use advisory thresholds initially (`crap_threshold = 50`) and ratchet down over time.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All enabled blocking gates passed |
| `1` | Threshold failure in CRAP, mutation, or Gherkin gate |
| `2` | Tool/precondition error (missing `.coverage`, git error, mutmut unavailable) |

DRY findings are **advisory** — they appear in the combined report but do not fail `forge check`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Coverage data not found` | Run `pytest --cov=...` before `forge check` |
| `mutmut does not support native Windows` | Use `ubuntu-latest` runners for mutation |
| `git diff failed` | Ensure `fetch-depth: 0` in checkout |
| Gate blocks every PR on legacy code | Raise thresholds temporarily; enable one gate at a time |
