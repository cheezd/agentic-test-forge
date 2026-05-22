# agentic-test-forge

Python quality enforcement for AI-generated and legacy codebases. Implements Uncle Bob Martin's workflow: **CRAP analysis**, **mutation testing**, and **Gherkin scenario mutation**, optimized for agentic development and CI gates.

## Status

**Phase 3 (code mutation)** — differential mutmut wrapper in progress on `issue-10-phase-3-code-mutation`.

| Command | Status |
|---------|--------|
| `forge crap` | Available |
| `forge mutate` | Available (Linux/WSL; mutmut does not run natively on Windows) |
| `forge check` | Phase 5 |
| `forge mutate-gherkin` | Phase 4 |

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
```

Run tests with coverage before CRAP analysis:

```bash
pytest --cov=src
forge crap --path src/ --threshold 30 --json crap-report.json
```

Differential mutation uses git diff against `--base` (default `main`) and skips unchanged files tracked in `.forge/mutation-manifest.json`. Use `--full` to ignore the manifest.

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

[tool.forge.gates]
crap = true
mutation = false
gherkin = false
```

Optional override: `forge.toml` in the project root (merged over `pyproject.toml`).

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## Domain language

See [`docs/domain/CONTEXT.md`](docs/domain/CONTEXT.md).

## Roadmap

1. Foundation & CLI shell — done
2. CRAP analyzer (radon + coverage.py) — done
3. Differential code mutation (mutmut) — in progress
4. Gherkin mutation
5. Quality gate orchestrator (`forge check`)
6. DRY flagging, consumer CI guide, polish
