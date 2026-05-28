#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Distro = "Ubuntu-24.04"
$WslRepoPath = "/mnt/" + ($RepoRoot.Path.Substring(0, 1).ToLower()) + ($RepoRoot.Path.Substring(2) -replace "\\", "/")

function Test-WslDistro {
    param([string]$Name)
    return (wsl -l -v 2>&1 | Out-String) -match [regex]::Escape($Name)
}

if (-not (Test-WslDistro $Distro)) {
    Write-Host "Installing $Distro..."
    wsl --install $Distro --no-launch
}

& (Join-Path $PSScriptRoot "sync-wsl-pilot.ps1")

$SetupScript = @"
set -euo pipefail
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip git rsync
if [ ! -d ~/forge-venv ]; then
  python3 -m venv ~/forge-venv
fi
source ~/forge-venv/bin/activate
pip install -U pip wheel
pip install -e ~/agentic-test-forge
pip install -e ~/agentic-test-forge/pilot
cd ~/agentic-test-forge/pilot
pytest --cov=src/pilot_app tests/ -q
echo 'WSL pilot setup OK (native copy at ~/agentic-test-forge)'
"@

Write-Host "Setting up WSL pilot venv at ~/forge-venv ..."
wsl -d $Distro -- bash -lc $SetupScript

Write-Host ""
Write-Host "Done. Run: .\scripts\pilot-mutmut-wsl.ps1"
