# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
- Install: `pip install agentic-test-forge==1.0.0`
- Mutation testing requires Linux or WSL (mutmut does not run natively on Windows)

[1.0.0]: https://github.com/cheezd/agentic-test-forge/releases/tag/v1.0.0
