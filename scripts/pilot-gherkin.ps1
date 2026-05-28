#Requires -Version 5.1
<#
.SYNOPSIS
  Run forge mutate-gherkin on native Windows (behave + subprocess).
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PilotDir = Join-Path $RepoRoot "pilot"
$VenvPython = Join-Path $PilotDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating pilot venv..."
    Push-Location $PilotDir
    python -m venv .venv
    & .\.venv\Scripts\pip.exe install -U pip wheel
    & .\.venv\Scripts\pip.exe install -e "${RepoRoot}[dev]"
    & .\.venv\Scripts\pip.exe install -e ".[dev]"
    & .\.venv\Scripts\pip.exe install behave
    Pop-Location
}

$Forge = Join-Path $PilotDir ".venv\Scripts\forge.exe"
$Behave = Join-Path $PilotDir ".venv\Scripts\behave.exe"

Push-Location $PilotDir
$env:PYTHONPATH = "src"
Write-Host "Running behave smoke test..."
& $Behave features/
Write-Host "Running forge mutate-gherkin..."
& $Forge mutate-gherkin --path features --full --threshold 80
Pop-Location
