# Pilot harness (Epic #130)

Minimal consumer-style project for end-to-end validation of **code mutation (mutmut)** and **Gherkin mutation** on a Windows dev box.

| Gate | Where to run | Why |
|------|--------------|-----|
| Code mutation (`forge mutate`) | **WSL Ubuntu** | mutmut requires Unix `fork()` |
| Gherkin mutation (`forge mutate-gherkin`) | **Native Windows** (or WSL) | subprocess + behave; no mutmut |

## One-time setup

### 1. WSL (for mutmut)

From repo root in PowerShell (requires Ubuntu 24.04 WSL — installed via `wsl --install Ubuntu-24.04`):

```powershell
.\scripts\setup-wsl-pilot.ps1
```

### 2. Windows venv (for gherkin + CRAP)

```powershell
cd pilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e "..[dev]"
pip install -e ".[dev]"
pip install behave
```

## Run pilot checks

From repo root:

```powershell
# Sync Windows edits to WSL native copy (required before mutmut)
.\scripts\sync-wsl-pilot.ps1

# Gherkin mutation — native Windows
.\scripts\pilot-gherkin.ps1

# Code mutation — WSL (mutmut)
.\scripts\pilot-mutmut-wsl.ps1

# Both gates
.\scripts\pilot-all.ps1
```

**Verified 2026-05-28:** gherkin 100% (17/17) on Windows; code mutation 100% (2/2) in WSL.

## Linux CI (GitHub Actions)

Dogfood mutation gates run on `ubuntu-latest` via `.github/workflows/ci.yml`:

| Job | Command (from `pilot/`) |
|-----|-------------------------|
| `forge-mutate-pilot` | `pytest --cov=src/pilot_app tests/` then `forge mutate --path src/pilot_app --full` |
| `forge-mutate-gherkin-pilot` | `python -m behave features/` then `forge mutate-gherkin --path features --full` |

Install uses editable forge + pilot (`pip install -e ".[dev]"` and `pip install -e "./pilot[dev]"`) until the mutmut fixes ship in PyPI `1.1.0`.

Local Linux smoke:

```bash
cd pilot
pip install -e "..[dev]" -e ".[dev]"
pytest --cov=src/pilot_app tests/
forge mutate --path src/pilot_app --full --threshold 80
python -m behave features/
forge mutate-gherkin --path features --full --threshold 80
```

## Manual commands

From `pilot/` on **Windows** (gherkin):

```powershell
$env:PYTHONPATH = "src"
behave features/
forge mutate-gherkin --path features --full --threshold 80
```

From `pilot/` in **WSL** (mutmut):

```bash
source ../.venv-wsl/bin/activate
pip install -e "..[dev]" -e ".[dev]"
pytest --cov=src/pilot_app tests/
forge mutate --path src/pilot_app --full --threshold 80
```

## Layout

```
pilot/
  src/pilot_app/     # small Python module (mutmut target)
  tests/             # pytest (mutmut test command)
  features/          # .feature + behave steps (gherkin target)
  pyproject.toml     # [tool.forge] with mutation + gherkin gates enabled
```
