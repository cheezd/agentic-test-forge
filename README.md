# agentic-test-forge

Python quality enforcement for AI-generated and legacy codebases. Implements Uncle Bob Martin's workflow: **CRAP analysis**, **mutation testing**, and **Gherkin scenario mutation**, optimized for agentic development and CI gates.

## Status

**Phase 1 (foundation)** — CLI shell, config loader, and project skeleton. Feature commands are stubs until later phases.

| Command | Status |
|---------|--------|
| `forge crap` | Phase 2 |
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
```

Configure per-project thresholds in `pyproject.toml`:

```toml
[tool.forge]
paths = ["src"]
crap_threshold = 30
crap_formula = "standard"  # standard | simplified
manifest_dir = ".forge"

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

1. Foundation & CLI shell *(current)*
2. CRAP analyzer (radon + coverage.py)
3. Differential code mutation (mutmut)
4. Gherkin mutation
5. Quality gate orchestrator (`forge check`)
6. DRY flagging, consumer CI guide, polish
