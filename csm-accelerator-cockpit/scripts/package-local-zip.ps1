$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $Root
$PackageName = "csm-accelerator-cockpit-v5.1-local.zip"
$PackageRootName = "csm-accelerator-cockpit-v5.1"
$DefaultDownloadsDir = Join-Path $RepoRoot "pages\csm-cockpit\downloads"
$PlaygroundDownloadsDir = "C:\Users\Adeon\OneDrive\Documents\Playground\pages\csm-cockpit\downloads"
$DownloadsDir = if (Test-Path (Split-Path -Parent $PlaygroundDownloadsDir)) { $PlaygroundDownloadsDir } else { $DefaultDownloadsDir }
$StagingRoot = Join-Path $RepoRoot ".codex-temp\csm-cockpit-package"
$StagingApp = Join-Path $StagingRoot $PackageRootName
$ZipPath = Join-Path $DownloadsDir $PackageName

if (Test-Path $StagingRoot) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StagingApp, $DownloadsDir | Out-Null

$excludeDirs = @(".venv", ".runtime", "__pycache__")
$excludeFiles = @("*.pyc")

Get-ChildItem -LiteralPath $Root -Force | ForEach-Object {
    if ($excludeDirs -contains $_.Name) {
        return
    }
    if ($_.PSIsContainer -and $_.Name -eq "csm_cockpit") {
        New-Item -ItemType Directory -Force -Path (Join-Path $StagingApp "csm_cockpit") | Out-Null
        robocopy $_.FullName (Join-Path $StagingApp "csm_cockpit") /E /XD "__pycache__" /XF "*.pyc" | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "robocopy failed for csm_cockpit with exit code $LASTEXITCODE"
        }
        return
    }
    Copy-Item -LiteralPath $_.FullName -Destination $StagingApp -Recurse -Force
}

$runsDir = Join-Path $StagingApp "csm_cockpit\runs"
if (Test-Path $runsDir) {
    Get-ChildItem -LiteralPath $runsDir -Force | Where-Object { $_.Name -ne ".gitkeep" } | Remove-Item -Recurse -Force
}

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $StagingRoot $PackageRootName) -DestinationPath $ZipPath -Force
Write-Host "Created $ZipPath"
