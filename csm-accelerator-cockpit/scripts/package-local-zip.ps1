$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RepoRoot = Split-Path -Parent $Root
$Version = "5.4"
$StandardPackageName = "csm-accelerator-cockpit-v$Version-local.zip"
$StandardRootName = "csm-accelerator-cockpit-v$Version"
$GlobalSkillsPackageName = "csm-accelerator-cockpit-v$Version-with-global-skills.zip"
$GlobalSkillsRootName = "csm-accelerator-cockpit-v$Version-with-global-skills"
$DefaultDownloadsDir = Join-Path $RepoRoot "pages\csm-cockpit\downloads"
$PlaygroundDownloadsDir = "C:\Users\Adeon\OneDrive\Documents\Playground\pages\csm-cockpit\downloads"
$DownloadsDir = if (Test-Path (Split-Path -Parent $PlaygroundDownloadsDir)) { $PlaygroundDownloadsDir } else { $DefaultDownloadsDir }
$StagingRoot = Join-Path $RepoRoot ".codex-temp\csm-cockpit-package"

$SkillPairs = @(
    @{
        Source = "C:\Users\Adeon\.codex\skills\alteryx-workflow-builder"
        Target = Join-Path $Root "tooling\alteryx_workflow_builder"
    },
    @{
        Source = "C:\Users\Adeon\.codex\skills\alteryx-beautification"
        Target = Join-Path $Root "tooling\alteryx-beautification"
    }
)

foreach ($pair in $SkillPairs) {
    if (Test-Path -LiteralPath $pair.Source) {
        if (Test-Path -LiteralPath $pair.Target) {
            Remove-Item -LiteralPath $pair.Target -Recurse -Force
        }
        New-Item -ItemType Directory -Force -Path $pair.Target | Out-Null
        robocopy $pair.Source $pair.Target /E /XD "__pycache__" ".git" /XF "*.pyc" "*.pyo" | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "robocopy failed while syncing $($pair.Source) with exit code $LASTEXITCODE"
        }
    } else {
        Write-Warning "Global skill source not found; packaging existing bundled copy: $($pair.Source)"
    }
}

function Copy-AppToStaging {
    param(
        [string]$StagingApp,
        [bool]$IncludeGlobalSkillsInstaller
    )

    New-Item -ItemType Directory -Force -Path $StagingApp | Out-Null
    Get-ChildItem -LiteralPath $Root -Force | ForEach-Object {
        if ($_.Name -in @(".venv", ".runtime", "__pycache__")) {
            return
        }
        if (!$IncludeGlobalSkillsInstaller -and $_.Name -eq "Install Or Update Codex Alteryx Skills.bat") {
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
        if ($_.PSIsContainer -and $_.Name -eq "scripts") {
            New-Item -ItemType Directory -Force -Path (Join-Path $StagingApp "scripts") | Out-Null
            robocopy $_.FullName (Join-Path $StagingApp "scripts") /E /XD "__pycache__" /XF "*.pyc" "*.pyo" | Out-Null
            if ($LASTEXITCODE -gt 7) {
                throw "robocopy failed for scripts with exit code $LASTEXITCODE"
            }
            if (!$IncludeGlobalSkillsInstaller) {
                Remove-Item -LiteralPath (Join-Path $StagingApp "scripts\install-codex-alteryx-skills.ps1") -Force -ErrorAction SilentlyContinue
            }
            return
        }
        Copy-Item -LiteralPath $_.FullName -Destination $StagingApp -Recurse -Force
    }

    $runsDir = Join-Path $StagingApp "csm_cockpit\runs"
    if (Test-Path $runsDir) {
        Get-ChildItem -LiteralPath $runsDir -Force | Where-Object { $_.Name -ne ".gitkeep" } | Remove-Item -Recurse -Force
    }
}

function New-CockpitZip {
    param(
        [string]$PackageName,
        [string]$PackageRootName,
        [bool]$IncludeGlobalSkillsInstaller
    )

    $StagingApp = Join-Path $StagingRoot $PackageRootName
    $ZipPath = Join-Path $DownloadsDir $PackageName
    if (Test-Path $StagingApp) {
        Remove-Item -LiteralPath $StagingApp -Recurse -Force
    }
    Copy-AppToStaging -StagingApp $StagingApp -IncludeGlobalSkillsInstaller $IncludeGlobalSkillsInstaller
    if (Test-Path $ZipPath) {
        Remove-Item -LiteralPath $ZipPath -Force
    }
    Compress-Archive -Path $StagingApp -DestinationPath $ZipPath -Force
    Write-Host "Created $ZipPath"
}

if (Test-Path $StagingRoot) {
    Remove-Item -LiteralPath $StagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $StagingRoot, $DownloadsDir | Out-Null

New-CockpitZip -PackageName $StandardPackageName -PackageRootName $StandardRootName -IncludeGlobalSkillsInstaller $false
New-CockpitZip -PackageName $GlobalSkillsPackageName -PackageRootName $GlobalSkillsRootName -IncludeGlobalSkillsInstaller $true
