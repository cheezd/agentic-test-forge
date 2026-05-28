#Requires -Version 5.1
<#
.SYNOPSIS
  Run full mutation pilot: gherkin on Windows + mutmut in WSL.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Gherkin mutation (native Windows) ==="
& (Join-Path $ScriptDir "pilot-gherkin.ps1")

Write-Host ""
Write-Host "=== Code mutation (WSL / mutmut) ==="
& (Join-Path $ScriptDir "pilot-mutmut-wsl.ps1")

Write-Host ""
Write-Host "Pilot complete: both mutation paths exercised."
