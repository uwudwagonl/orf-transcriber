<#
.SYNOPSIS
  Downloads orfondl.exe and FFmpeg into build/vendor so PyInstaller can
  bundle them. Idempotent: skips files that already exist.

.NOTES
  - orfondl: pulled from the latest GitHub release tagged on the repo.
  - FFmpeg: gyan.dev "essentials" build (smallest static Windows build,
    license: LGPL with non-free codecs disabled).
#>

[CmdletBinding()]
param(
    [string]$Root = (Resolve-Path "$PSScriptRoot/../..").Path
)

$ErrorActionPreference = "Stop"
$Vendor = Join-Path $Root "build/vendor"
New-Item -ItemType Directory -Force -Path $Vendor | Out-Null

$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Invoke-Download {
    param([string]$Url, [string]$Dest)
    Write-Host "  → $Url"
    Invoke-WebRequest -Uri $Url -OutFile $Dest -UseBasicParsing
}

# ── orfondl ────────────────────────────────────────────────────────────────
$orfondlExe = Join-Path $Vendor "orfondl.exe"
if (-not (Test-Path $orfondlExe)) {
    Write-Host "Resolving latest orfondl release …"
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/badlogic/orfondl/releases/latest" `
                              -Headers @{ "User-Agent" = "orf-transcriber-build" }
    $asset = $rel.assets | Where-Object { $_.name -eq "orfondl-windows-amd64.exe" } | Select-Object -First 1
    if (-not $asset) { throw "Konnte 'orfondl-windows-amd64.exe' im Release nicht finden." }
    Invoke-Download -Url $asset.browser_download_url -Dest $orfondlExe
} else {
    Write-Host "orfondl.exe schon vorhanden — übersprungen."
}

# ── FFmpeg (essentials build) ─────────────────────────────────────────────
$ffmpegExe = Join-Path $Vendor "ffmpeg.exe"
$ffprobeExe = Join-Path $Vendor "ffprobe.exe"
if (-not ((Test-Path $ffmpegExe) -and (Test-Path $ffprobeExe))) {
    Write-Host "Lade FFmpeg essentials build …"
    $zipUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    $zipDest = Join-Path $env:TEMP "ffmpeg-essentials.zip"
    Invoke-Download -Url $zipUrl -Dest $zipDest

    $extractDir = Join-Path $env:TEMP "ffmpeg-extracted"
    if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
    Expand-Archive -Path $zipDest -DestinationPath $extractDir -Force

    $found = Get-ChildItem -Path $extractDir -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
    if (-not $found) { throw "ffmpeg.exe nicht im ZIP gefunden." }
    Copy-Item -Force -Path $found.FullName -Destination $ffmpegExe

    $foundProbe = Get-ChildItem -Path $extractDir -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
    if (-not $foundProbe) { throw "ffprobe.exe nicht im ZIP gefunden." }
    Copy-Item -Force -Path $foundProbe.FullName -Destination $ffprobeExe

    Remove-Item -Recurse -Force $extractDir
    Remove-Item -Force $zipDest
} else {
    Write-Host "FFmpeg bereits vorhanden — übersprungen."
}

Write-Host ""
Write-Host "Vendor-Verzeichnis: $Vendor"
Get-ChildItem $Vendor | Format-Table Name, Length -AutoSize
