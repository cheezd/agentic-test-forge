# agentic-test-forge

[![PyPI version](https://img.shields.io/pypi/v/agentic-test-forge)](https://pypi.org/project/agentic-test-forge/)

Python quality enforcement for AI-generated and legacy codebases. Implements Uncle Bob Martin's workflow: **CRAP analysis**, **mutation testing**, and **Gherkin scenario mutation**, optimized for agentic development and CI gates.

## Status

**v1.1 complete** — PyPI, dogfood CI, external pilot, pre-commit hook, and docs polish shipped ([#58](https://github.com/cheezd/agentic-test-forge/issues/58)).

| Command | Status |
|---------|--------|
| `forge crap` | Available |
| `forge mutate` | Available (Linux/WSL; mutmut does not run natively on Windows) |
| `forge mutate-gherkin` | Available |
| `forge check` | Available (includes optional advisory DRY scan) |

## Install

```bash
pip install agentic-test-forge
```

Pin a version:

```bash
pip install agentic-test-forge==1.0.0
```

For local development of this repo:

```bash
pip install -e ".[dev]"
```

Alternative (VCS install):

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

**Optional local override:** you do not need `forge.toml` for normal use — `[tool.forge]` in
`pyproject.toml` is enough (including consumer repos). If present, a `forge.toml` in the
**current working directory** is merged on top of `pyproject.toml` (useful for uncommitted
experiments, e.g. stricter thresholds on your machine). Unlike `pyproject.toml`, forge does
not search parent directories for `forge.toml`; run from the directory that contains it, or
rely on `pyproject.toml` only.

Consumer CI integration: see [`docs/consumer-ci.md`](docs/consumer-ci.md) (GitHub Actions, [version pinning](docs/consumer-ci.md#version-pinning), [Django / monorepo](docs/consumer-ci.md#django-and-monorepo-appendix), [Windows console notes](docs/consumer-ci.md#windows-console-and-rich-output)).

### Pre-commit (optional)

Run `forge check` locally before commit (respects `[tool.forge.gates]`):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/cheezd/agentic-test-forge
    rev: v1.0.0
    hooks:
      - id: forge-check
```

```bash
pip install pre-commit agentic-test-forge==1.0.0
pre-commit install
pytest --cov=src   # CRAP gate needs .coverage
pre-commit run forge-check --all-files
```

See [consumer-ci — pre-commit](docs/consumer-ci.md#pre-commit-hook) for coverage
prerequisites, Windows/mutation notes, and troubleshooting.

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

Index and when to write ADRs: [`docs/adr/README.md`](docs/adr/README.md). Package layout, dependency direction, and refactor conventions: [`docs/adr/0001-package-boundaries-and-refactor-conventions.md`](docs/adr/0001-package-boundaries-and-refactor-conventions.md).

## License

Licensed under the [GNU Lesser General Public License v3.0 or later](LICENSE) (LGPL-3.0-or-later).

**What this means in practice:**

- **Modifications to forge** must be shared under LGPL when you distribute them.
- **Using forge to check your code** — via CLI in CI, locally, or on build servers — does **not** require your application or SaaS product to become open source.
- **Importing forge as a library** in a proprietary product is generally permitted under LGPL (unlike GPL), subject to LGPL’s requirements (e.g. allowing replacement of the library).

We deliberately use **LGPL, not AGPL**, so network/SaaS deployment of your product does not trigger additional copyleft beyond the library itself. This is not legal advice; consult counsel for your specific deployment.

## Roadmap

**v1.0 (shipped)**

1. Foundation & CLI shell — done
2. CRAP analyzer (radon + coverage.py) — done
3. Differential code mutation (mutmut) — done
4. Gherkin mutation — done
5. Quality gate orchestrator (`forge check`) — done
6. DRY flagging (advisory) — done

**v1.1 (shipped — [#58](https://github.com/cheezd/agentic-test-forge/issues/58))**

- PyPI publish & GitHub Release — done ([#64](https://github.com/cheezd/agentic-test-forge/issues/64))
- Dogfood CI (`forge check` + report artifact) — done ([#70](https://github.com/cheezd/agentic-test-forge/issues/70))
- External consumer pilot (compliance-llm) — done ([#71](https://github.com/cheezd/agentic-test-forge/issues/71))
- Pre-commit hook — done ([#74](https://github.com/cheezd/agentic-test-forge/issues/74))
- Docs polish & ADR bootstrap — done ([#78](https://github.com/cheezd/agentic-test-forge/issues/78)–[#81](https://github.com/cheezd/agentic-test-forge/issues/81), [#128](https://github.com/cheezd/agentic-test-forge/pull/128))

**Beyond v1.1**

- Semantic DRY ([#122](https://github.com/cheezd/agentic-test-forge/issues/122)) — deferred to v1.2+
