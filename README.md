# agentic-test-forge

Python quality enforcement for AI-generated and legacy codebases. Implements Uncle Bob Martin's workflow: **CRAP analysis**, **mutation testing**, and **Gherkin scenario mutation**, optimized for agentic development and CI gates.

## Status

**Phase 6 (polish)** — complete on `main` (PR #24).

| Command | Status |
|---------|--------|
| `forge crap` | Available |
| `forge mutate` | Available (Linux/WSL; mutmut does not run natively on Windows) |
| `forge mutate-gherkin` | Available |
| `forge check` | Available (includes optional advisory DRY scan) |

## Install

```bash
pip install -e ".[dev]"
```

Consumer repos can install from VCS until PyPI publish:

```bash
pip install "agentic-test-forge @ git+https://github.com/cheezd/agentic-test-forge.git"
```

## Usage

```bash
forge --help
forge crap --path src/ --threshold 30
forge mutate --path src/ --base main --threshold 80
forge mutate-gherkin --path features/ --base main --threshold 80
forge check --path src/ --features-path features/
```

Run tests with coverage, then the full quality gate:

```bash
pytest --cov=src
forge check --path src/ --json report.json
```

Differential mutation uses git diff against `--base` (default `main`) and skips unchanged files tracked in `.forge/mutation-manifest.json`. Use `--full` to ignore the manifest.

Gherkin mutation mutates Examples table cells in changed `.feature` scenarios, runs the configured acceptance test command, and tracks results in `.forge/gherkin-manifest.json`.

Thresholds are gate cutoffs, not comparable scales: `crap_threshold` is a **maximum** CRAP score per function; `mutation_threshold` and `gherkin_threshold` are **minimum** mutation kill rates (0–100%). See [score interpretation](docs/domain/CONTEXT.md#score-interpretation) for what the numbers mean.

Configure per-project thresholds in `pyproject.toml`:

```toml
[tool.forge]
paths = ["src"]
crap_threshold = 30
crap_formula = "standard"  # standard | simplified
manifest_dir = ".forge"
mutation_threshold = 80
mutation_base_ref = "main"
mutation_test_cmd = "pytest"
gherkin_threshold = 80
gherkin_base_ref = "main"
gherkin_test_cmd = "behave"
gherkin_runner = "behave"  # behave | pytest
gherkin_paths = ["features"]

[tool.forge.gates]
crap = true
mutation = false
gherkin = false
dry = true         # advisory — does not fail forge check
```

Optional override: `forge.toml` in the project root (merged over `pyproject.toml`).

Consumer CI integration: see [`docs/consumer-ci.md`](docs/consumer-ci.md).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## Domain language

See [`docs/domain/CONTEXT.md`](docs/domain/CONTEXT.md).

## Architecture decisions

Package layout, dependency direction, and refactor conventions: [`docs/adr/0001-package-boundaries-and-refactor-conventions.md`](docs/adr/0001-package-boundaries-and-refactor-conventions.md).

## Roadmap

1. Foundation & CLI shell — done
2. CRAP analyzer (radon + coverage.py) — done
3. Differential code mutation (mutmut) — done
4. Gherkin mutation — done
5. Quality gate orchestrator (`forge check`) — done
6. DRY flagging, consumer CI guide, polish — done
