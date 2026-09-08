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
pip install agentic-test-forge==1.1.0
```

From Git (fallback):

```bash
pip install "agentic-test-forge @ git+https://github.com/cheezd/agentic-test-forge.git@v1.1.0"
```

## Version pinning

Pin an exact semver in CI and pre-commit so gate behavior stays reproducible across runner images and developer machines.

| Surface | Pin | Bump when |
|---------|-----|-----------|
| GitHub Actions / CI | `pip install agentic-test-forge==1.1.0` | A new forge release changes thresholds, exit codes, or gate semantics you rely on |
| Pre-commit | `rev: v1.1.0` on the hook repo + `pip install agentic-test-forge==1.1.0` in docs/setup | Same as CI — align hook `rev` with the PyPI version you install |
| Local dev | `pip install agentic-test-forge==1.1.0` or editable producer install | Optional: float latest patch (`==1.1.*`) only if you accept drift |

**When to bump:** After a tagged forge release (`v1.0.1`, `v1.1.0`, …), update pins in the consumer repo in the same PR (or a follow-up) once you have validated the new version against your thresholds. Patch releases are usually drop-in; minor/major releases may need threshold or gate config review.

**Dependabot:** Add `agentic-test-forge` to pip dependency updates (or Renovate). Review release notes before merging auto-bumps — ratchet thresholds and staged gates may need adjustment. Pre-commit hook `rev` is a separate ecosystem; bump it when you bump the PyPI pin.

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
gherkin_test_cmd = "python -m behave"  # not bare `behave` — often missing from PATH

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
          pip install agentic-test-forge==1.1.0

      - name: Run tests with coverage
        run: pytest --cov=src --cov-report=xml

      - name: Run forge quality gate
        run: forge check --json forge-report.json

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
3. **Week 3:** enable `mutation` on Linux CI or WSL (keep `false` on Windows pre-commit)
4. **Week 4+:** enable `gherkin` once `python -m behave` (or pytest-bdd) is already green

Use advisory thresholds initially (`crap_threshold = 50`) and ratchet down over time. See [score interpretation](domain/CONTEXT.md#score-interpretation) for what CRAP and mutation values mean.

## Django and monorepo appendix

Validated on the external pilot [compliance-llm-analysis-platform](https://github.com/cheezd/compliance-llm-analysis-platform) ([#43](https://github.com/cheezd/compliance-llm-analysis-platform/issues/43)). Pattern: **repo-root `[tool.forge]`**, run forge from the **application CWD** (e.g. `apps/backend`), scope application packages only.

### Layout

| Piece | Example (compliance-llm) |
|-------|---------------------------|
| Monorepo app CWD | `apps/backend` |
| Repo-root config | `pyproject.toml` at repository root |
| Application paths | `paths = ["analysis"]` (relative to CWD, not pyproject directory) |
| Settings / wiring | Outside `paths` (e.g. `django_project/`) |

`load_config()` walks up from the current working directory to find repo-root `pyproject.toml`. `paths` entries resolve relative to **CWD** — invoke `forge` from the directory that contains your Django app tree. `forge check` with no `--path` uses those config paths. Repeat `--path` to override (`forge check --path dashboards --path ghdash`).

### Repo-root `[tool.forge]` (pilot)

```toml
[tool.forge]
paths = ["analysis"]
crap_threshold = 50
mutation_threshold = 80
mutation_base_ref = "main"
mutation_test_cmd = "pytest --nomigrations --reuse-db"  # audit only; see mutation note
manifest_dir = ".forge"

[tool.forge.gates]
crap = true
dry = true
mutation = false   # Linux CI or WSL only (mutmut)
gherkin = false
```

**Staged gates (pilot):** CRAP + DRY on locally (including Windows); mutation off until Linux CI or WSL. **`crap_threshold = 50`** is acceptable for legacy code — ratchet toward `30` after hotspots are addressed.

### Coverage and verification

Django tests with `coverage.py` (not pytest-cov required for the pilot path):

```bash
cd apps/backend
pip install agentic-test-forge==1.1.0 coverage
coverage run --source=analysis manage.py test tests --verbosity=0
forge check --coverage-file .coverage
```

Use the same `source` scope as `[tool.forge].paths` so CRAP scores align with collected coverage. For multi-package Django trees (repeated `models.py` / `views.py` names), set:

```toml
[tool.coverage.run]
source = ["dashboards", "ghdash", "health_policy", "compliance_rules"]
relative_files = true

[tool.forge]
paths = ["dashboards", "ghdash", "health_policy", "compliance_rules"]
```

CRAP matches coverage by resolved path or project-relative POSIX key. It does **not** join on basename, so two `models.py` files cannot share each other's coverage.

### Mutation (pytest-django)

Verified 2026-08-29 on Linux with `agentic-test-forge==1.1.0`, Django 5.2, mutmut 3.7, and pytest-django 4.14 ([#147](https://github.com/cheezd/agentic-test-forge/issues/147)). **Works with caveats** — enable the gate on Linux CI or WSL, not native Windows.

`mutation_test_cmd` is **audit only**. Forge writes it to `.forge/mutmut-run.toml`; the subprocess is still mutmut's pytest runner. `python manage.py test` is not a mutmut input. Use pytest-django.

Keep `mutation = false` for Windows pre-commit and for the first CRAP/DRY rollout. When Linux CI is ready, add:

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings"  # your settings module
pythonpath = ["."]
testpaths = ["tests"]
addopts = "--nomigrations"

[tool.mutmut]
source_paths = ["billing/"]  # same packages as [tool.forge].paths
pytest_add_cli_args_test_selection = ["tests/"]
pytest_add_cli_args = ["--nomigrations", "--reuse-db"]
also_copy = ["config/", "manage.py", "conftest.py"]

[tool.forge]
paths = ["billing"]
mutation_threshold = 80
mutation_base_ref = "main"
mutation_test_cmd = "pytest --nomigrations --reuse-db"

[tool.forge.gates]
mutation = true  # ubuntu-latest or WSL only
```

Install on the Linux runner:

```bash
pip install agentic-test-forge==1.1.0 pytest pytest-django django
pytest -q
forge mutate --full --threshold 80
# or, with the gate enabled:
forge check
```

Caveats:

- mutmut needs Unix `fork()`. Native Windows exits **2**. Prefer `ubuntu-latest`; local Windows developers use WSL on the Linux filesystem (not `/mnt/c`). See [Windows and WSL mutation](#windows-and-wsl-mutation).
- Start with a **narrow slice** (one app package), not the full suite.
- A kill rate below `mutation_threshold` is a **gate failure** (`exit 1`), not a tool error. Survivors mean the pytest-django tests did not catch those mutants.
- `also_copy` must include settings, `manage.py`, and `conftest.py` so mutmut's worktree can load Django.

## Gherkin appendix

Enable the Gherkin gate only after acceptance tests already pass. The in-repo example is [`pilot/`](../pilot/README.md) (behave + Examples-table mutation).

### Config

```toml
[tool.forge]
gherkin_paths = ["features"]
gherkin_threshold = 80
gherkin_base_ref = "main"
gherkin_test_cmd = "python -m behave"
gherkin_runner = "behave"  # behave | pytest

[tool.forge.gates]
gherkin = true
```

Use `python -m behave`, not bare `behave`. The default `[tool.forge]` value is still `behave`; that fails with `Acceptance test command not found` when the script is not on `PATH` (common on Windows venvs and some CI images). `python -m behave` uses the same interpreter as `forge`.

Omitted `--features-path` / `--path` on `forge mutate-gherkin` uses `gherkin_paths`. Repeat `--path` to override.

### Commands

Cheap preflight (no Django, no mutation), then smoke the suite, then mutate. Dogfood CI does the same from `pilot/`:

```bash
# After drafting or promoting .feature files:
forge gherkin lint --path features/
forge gherkin inventory --path features/ --json inventory.json
forge gherkin validate-steps --path features/

python -m behave features/
forge mutate-gherkin --full --threshold 80
# or, with the gate enabled:
forge check
```

| Command | When | Exit `1` when |
|---------|------|----------------|
| `forge gherkin lint` | Before human sign-off on drafts; again on `features/` | Missing/empty Examples, duplicate names, or `--require-tags` with no tags |
| `forge gherkin inventory` | Sign-off packet / PR notes | Never (listing only). `--base main` limits to changed `.feature` files |
| `forge gherkin validate-steps` | After promoting specs, before a full behave run | A feature step has no matching `@given`/`@when`/`@then`/`@step` pattern under `features/steps/` (or `--steps-path`) |

`lint --flag-implementation-leakage` warns on class/module-like step text (does not fail unless you treat warnings as errors in a wrapper). Inventory JSON schema version is `1` (`schema_version` field): `filepath`, `name`, `scenario_id`, `tags`, `has_examples`, `start_line`, `end_line`, `kind`.

Gherkin mutation edits Examples table cells in changed `.feature` files, runs `gherkin_test_cmd` per mutant, and records results in `.forge/gherkin-manifest.json`. It does **not** need mutmut and **does** run on native Windows.

For pytest-bdd, set `gherkin_runner = "pytest"` and point `gherkin_test_cmd` at your pytest invocation.

## Windows and WSL mutation

Verified on the in-repo pilot (2026-05-28): Gherkin 100% (17/17) on native Windows; code mutation 100% (2/2) in WSL Ubuntu 24.04.

| Gate | Where to run | Why |
|------|--------------|-----|
| Code mutation (`forge mutate`) | **WSL Ubuntu** or `ubuntu-latest` | mutmut needs Unix `fork()` and is unreliable on `/mnt/c` |
| Gherkin mutation (`forge mutate-gherkin`) | **Native Windows** or WSL | subprocess + behave; no mutmut |

Keep `mutation = false` in Windows pre-commit. If the mutation gate is enabled on native Windows, `forge check` exits **2** with a clear error — it does not crash.

### WSL layout (do not run mutmut on `/mnt/c`)

`scripts/sync-wsl-pilot.ps1` rsyncs the repo to `~/agentic-test-forge` inside Ubuntu-24.04 so mutmut runs on the Linux filesystem. From the producer repo root in PowerShell:

```powershell
.\scripts\setup-wsl-pilot.ps1   # one-time: distro, venv, editable install
.\scripts\sync-wsl-pilot.ps1    # after Windows edits, before mutmut
.\scripts\pilot-gherkin.ps1     # native Windows Gherkin
.\scripts\pilot-mutmut-wsl.ps1  # WSL code mutation
```

Consumer repos can copy that pattern: sync off `/mnt/c`, install forge in a Linux venv, run `forge mutate` there. GitHub Actions should use `ubuntu-latest` for the mutation job (see [GitHub Actions example](#github-actions-example)); local Windows developers use WSL or skip the gate.

## Pre-commit hook

Optional local gate before commit. The hook runs `forge check` and reads the same
`[tool.forge]` / `[tool.forge.gates]` config as CI — no duplicate parsing.

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/cheezd/agentic-test-forge
    rev: v1.1.0
    hooks:
      - id: forge-check
        # Optional overrides (omit --path to use [tool.forge].paths):
        # args: [--path, src/, --coverage-file, .coverage]
```

Install hooks:

```bash
pip install pre-commit agentic-test-forge==1.1.0
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

Keep `mutation = false` in `[tool.forge.gates]` for local pre-commit on Windows.
See [Windows and WSL mutation](#windows-and-wsl-mutation). If mutation is enabled
on Windows, `forge check` exits **2** with a clear error — it does not crash.

Exit codes match [CI exit codes](#exit-codes) (0 pass, 1 gate failure, 2 tool error).

## Windows console and Rich output

`forge` uses [Rich](https://github.com/Textualize/rich) for status symbols (pass/fail markers, tables). **PowerShell** and some CI log captures use a legacy code page; redirected logs may show `` (U+FFFD) instead of the intended glyph. The gate result and exit code are still correct — treat mojibake as a display issue, not a failed check.

**Local mitigation (optional):**

```powershell
chcp 65001
$OutputEncoding = [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8
```

Use a UTF-8 terminal (Windows Terminal, VS Code integrated terminal with UTF-8) when reading forge output interactively. In CI, prefer interpreting exit codes and JSON reports (`--json`) over parsing Unicode symbols from archived logs.

We document this first; a `--no-color` / plain-text mode is not required for v1.1 unless pilot friction demands it.

## DRY analysis (`forge dry`)

Semantic DRY (v1.2, [ADR 0002](adr/0002-semantic-dry-detection.md)) reports **structural duplicate candidates** using normalized AST fingerprints and Jaccard similarity. Findings are **advisory** — exit code `0` even when duplicates are reported.

Config keys (optional):

```toml
[tool.forge]
dry_threshold = 0.82   # Jaccard minimum (default 0.82)
dry_min_lines = 4        # skip functions shorter than this
dry_min_nodes = 20       # skip normalized subtrees smaller than this
```

Local analysis without full `forge check`:

```bash
forge dry
forge dry --path src/ --path other_pkg/
forge dry --path src/ --threshold 0.9 --json dry-report.json
```

Omitted `--path` uses `[tool.forge].paths`. Repeat `--path` to override.

JSON findings include `similarity_score`, `start_line`, `end_line`, and `node_count` in addition to v1 fields.

## Exit codes

Defined by `ForgeExitCode` in `agentic_test_forge.cli.exit_codes`. Package layout and status/exit mapping policy: [ADR 0001](adr/0001-package-boundaries-and-refactor-conventions.md#exit-codes-and-report-status).

| Code | Enum | Meaning |
|------|------|---------|
| `0` | `SUCCESS` | All enabled blocking gates passed |
| `1` | `GATE_FAILURE` | Threshold failure in CRAP, mutation, or Gherkin gate; `gherkin lint` / `validate-steps` errors |
| `2` | `TOOL_ERROR` | Tool/precondition error (missing `.coverage`, git error, mutmut unavailable) |

DRY findings are **advisory** — they appear in the combined report but do not fail `forge check`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Coverage data not found` | Run `pytest --cov=...` before `forge check` or the pre-commit hook |
| `mutmut does not support native Windows` | Use `ubuntu-latest` or WSL; see [Windows and WSL mutation](#windows-and-wsl-mutation) |
| `Acceptance test command not found: behave` | Set `gherkin_test_cmd = "python -m behave"` |
| `git diff failed` | Ensure `fetch-depth: 0` in checkout |
| Gate blocks every PR on legacy code | Raise thresholds temporarily; enable one gate at a time |
