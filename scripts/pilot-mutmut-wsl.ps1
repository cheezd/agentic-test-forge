#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Distro = "Ubuntu-24.04"

& (Join-Path $ScriptDir "sync-wsl-pilot.ps1")

$RunScript = @"
set -euo pipefail
if [ ! -d ~/forge-venv ]; then
  python3 -m venv ~/forge-venv
  source ~/forge-venv/bin/activate
  pip install -U pip wheel
  pip install -e ~/agentic-test-forge
  pip install -e ~/agentic-test-forge/pilot
else
  source ~/forge-venv/bin/activate
  pip install -e ~/agentic-test-forge -q
  pip install -e ~/agentic-test-forge/pilot -q
fi
cd ~/agentic-test-forge/pilot
rm -rf mutants .mutmut-cache
pytest --cov=src/pilot_app tests/ -q
forge mutate --path src/pilot_app --full --threshold 80
"@

Write-Host "Running forge mutate (mutmut) in WSL native copy ($Distro)..."
wsl -d $Distro -- bash -lc $RunScript
