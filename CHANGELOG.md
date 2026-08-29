# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- Consumer docs: pytest-django + mutmut recipe (works with caveats on Linux/WSL; `mutation_test_cmd` remains audit-only) ([#147](https://github.com/cheezd/agentic-test-forge/issues/147))

## [1.1.0] - 2026-08-29

PyPI release of work already on `main` since `v1.0.0`. Consumers can pin `==1.1.0` instead of a git ref.

### Fixed

- mutmut 3.5 runner compatibility ([#132](https://github.com/cheezd/agentic-test-forge/issues/132))
- `forge check` / `crap` / `mutate` / `mutate-gherkin` honor `[tool.forge].paths` and `gherkin_paths` when `--path` / `--features-path` are omitted; repeat `--path` to override ([#145](https://github.com/cheezd/agentic-test-forge/issues/145))
- CRAP coverage matching uses resolved paths and project-relative POSIX keys (`relative_files = true`); no basename guessing ([#143](https://github.com/cheezd/agentic-test-forge/pull/143), [#146](https://github.com/cheezd/agentic-test-forge/issues/146))

### Added

- Dogfood CI jobs for code and Gherkin mutation on the in-repo `pilot/` harness ([#133](https://github.com/cheezd/agentic-test-forge/issues/133))
- Consumer docs: [Gherkin appendix](docs/consumer-ci.md#gherkin-appendix) and [Windows / WSL mutation](docs/consumer-ci.md#windows-and-wsl-mutation)

### Deferred

- External BDD consumer pilot ([#134](https://github.com/cheezd/agentic-test-forge/issues/134)) — not a release gate
- pytest-django + mutmut spike ([#147](https://github.com/cheezd/agentic-test-forge/issues/147)) — keep `mutation = false` on Django until that spike lands

### Notes

- Install: `pip install agentic-test-forge==1.1.0`
- Code mutation still requires Linux or WSL (mutmut does not run natively on Windows)
- Producer CI `forge-check` continues to install the last published PyPI pin until this tag is live

[1.1.0]: https://github.com/cheezd/agentic-test-forge/releases/tag/v1.1.0

## [1.0.0] - 2026-05-27

First public release on PyPI. v1.0 library scope (Phases 1–6) is complete on `main`.

### Added

- `forge crap` — CRAP analysis (radon + coverage.py)
- `forge mutate` — differential code mutation (mutmut; Linux/WSL)
- `forge mutate-gherkin` — Gherkin Examples-table mutation
- `forge check` — orchestrated quality gate with configurable thresholds
- Advisory DRY duplication scan (non-blocking)
- `[tool.forge]` configuration in consumer `pyproject.toml`
- Consumer CI integration guide (`docs/consumer-ci.md`)
- Domain language reference (`docs/domain/CONTEXT.md`)

### Notes

- Classifier: **Beta** (`Development Status :: 4 - Beta`)
- License: **LGPL-3.0-or-later** (see `LICENSE`)
- Install: `pip install agentic-test-forge==1.0.0`
- Mutation testing requires Linux or WSL (mutmut does not run natively on Windows)

[1.0.0]: https://github.com/cheezd/agentic-test-forge/releases/tag/v1.0.0
