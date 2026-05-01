<#
.SYNOPSIS
  Run the GUI from source for development. Fetches native deps if missing.
#>
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot/../..").Path

if (-not (Test-Path (Join-Path $Root "build/vendor/orfondl.exe"))) {
    & (Join-Path $PSScriptRoot "fetch-deps.ps1") -Root $Root
}

$Venv = Join-Path $Root "build/.venv"
if (-not (Test-Path $Venv)) {
    python -m venv $Venv
}
$py = Join-Path $Venv "Scripts/python.exe"
& $py -m pip install --upgrade pip wheel | Out-Null
& $py -m pip install -r (Join-Path $Root "requirements.txt")

$env:PYTHONPATH = (Join-Path $Root "src")
& $py -m orf_transcriber
