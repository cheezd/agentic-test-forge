#Requires -Version 5.1
<#
.SYNOPSIS
  Sync repo to WSL native filesystem for mutmut (fork) runs.

.DESCRIPTION
  mutmut is reliable when the project lives on the Linux filesystem, not /mnt/c.
  This script rsyncs the repo to ~/agentic-test-forge inside WSL.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Distro = "Ubuntu-24.04"
$WslRepoPath = "/mnt/" + ($RepoRoot.Path.Substring(0, 1).ToLower()) + ($RepoRoot.Path.Substring(2) -replace "\\", "/")

$SyncScript = @"
set -euo pipefail
mkdir -p ~/agentic-test-forge
rsync -a --delete \
  --exclude '.venv/' \
  --exclude '.venv-wsl/' \
  --exclude 'pilot/.venv/' \
  --exclude '**/__pycache__/' \
  --exclude '**/.pytest_cache/' \
  --exclude '**/mutants/' \
  --exclude '**/.mutmut-cache/' \
  --exclude '**/.forge/' \
  '$WslRepoPath/' ~/agentic-test-forge/
echo 'Synced to ~/agentic-test-forge'
"@

wsl -d $Distro -- bash -lc $SyncScript
