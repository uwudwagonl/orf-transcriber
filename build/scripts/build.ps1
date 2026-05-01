<#
.SYNOPSIS
  End-to-end Windows build: fetch deps, run PyInstaller, run WiX → MSI.

.PARAMETER Version
  Product version, default 0.1.0. Embedded in MSI and ARP entry.

.PARAMETER SkipDeps
  Skip the fetch-deps step (use existing build/vendor contents).

.PARAMETER SkipMsi
  Stop after PyInstaller; useful when iterating on the app code.

.EXAMPLE
  pwsh build/scripts/build.ps1
  pwsh build/scripts/build.ps1 -Version 0.2.0
  pwsh build/scripts/build.ps1 -SkipMsi   # just produce the dist folder

.NOTES
  Prerequisites:
    - Python 3.11+ on PATH
    - WiX 5: dotnet tool install --global wix
    - WiX UI extension: wix extension add WixToolset.UI.wixext
#>

[CmdletBinding()]
param(
    [string]$Version = "0.1.0",
    [switch]$SkipDeps,
    [switch]$SkipMsi
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path "$PSScriptRoot/../..").Path
Push-Location $Root
try {
    $Build = Join-Path $Root "build"
    $Dist = Join-Path $Build "dist"
    $Work = Join-Path $Build "work"
    $Venv = Join-Path $Build ".venv"

    Write-Host "▶ Build root: $Root" -ForegroundColor Cyan
    Write-Host "▶ Version:    $Version" -ForegroundColor Cyan

    # ── 1. virtualenv ────────────────────────────────────────────────────
    if (-not (Test-Path $Venv)) {
        Write-Host "`n[1/5] Creating venv …" -ForegroundColor Green
        python -m venv $Venv
    }
    $py = Join-Path $Venv "Scripts/python.exe"
    & $py -m pip install --upgrade pip wheel | Out-Null
    & $py -m pip install -r (Join-Path $Root "requirements-build.txt")

    # ── 2. fetch native deps ────────────────────────────────────────────
    if (-not $SkipDeps) {
        Write-Host "`n[2/5] Fetching native dependencies …" -ForegroundColor Green
        & (Join-Path $PSScriptRoot "fetch-deps.ps1") -Root $Root
    } else {
        Write-Host "`n[2/5] Skipped fetch-deps (per flag)." -ForegroundColor Yellow
    }

    # ── 3. PyInstaller ──────────────────────────────────────────────────
    Write-Host "`n[3/5] Running PyInstaller …" -ForegroundColor Green
    if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
    if (Test-Path $Work) { Remove-Item -Recurse -Force $Work }

    & $py -m PyInstaller `
        (Join-Path $Build "orf-transcriber.spec") `
        --distpath $Dist `
        --workpath $Work `
        --noconfirm

    if (-not (Test-Path (Join-Path $Dist "OrfTranscriber/OrfTranscriber.exe"))) {
        throw "PyInstaller-Output unvollständig — OrfTranscriber.exe fehlt."
    }

    if ($SkipMsi) {
        Write-Host "`nFertig (ohne MSI). Output: $Dist\OrfTranscriber" -ForegroundColor Green
        return
    }

    # ── 4. WiX ──────────────────────────────────────────────────────────
    Write-Host "`n[4/5] Building MSI with WiX …" -ForegroundColor Green
    $msiOut = Join-Path $Dist "OrfTranscriber-$Version.msi"
    $env:WIX_LICENSE_RTF = (Join-Path $Build "installer/License.rtf")

    & wix build (Join-Path $Build "installer/Package.wxs") `
        -arch x64 `
        -ext WixToolset.UI.wixext `
        -bindpath "dist=$Dist" `
        -d Version=$Version `
        -out $msiOut

    if (-not (Test-Path $msiOut)) {
        throw "WiX hat keine MSI erzeugt: $msiOut"
    }

    # ── 5. summary ──────────────────────────────────────────────────────
    Write-Host "`n[5/5] Done." -ForegroundColor Green
    $msi = Get-Item $msiOut
    Write-Host ""
    Write-Host "MSI: $($msi.FullName)" -ForegroundColor Cyan
    Write-Host ("Größe: {0:N1} MB" -f ($msi.Length / 1MB))
}
finally {
    Pop-Location
}
