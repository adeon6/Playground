param(
    [string]$TargetSkillsRoot = (Join-Path $env:USERPROFILE ".codex\skills")
)

$ErrorActionPreference = "Stop"

$ScriptRoot = $PSScriptRoot
$AppRoot = Split-Path -Parent $ScriptRoot
$ToolingRoot = Join-Path $AppRoot "tooling"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$BackupRoot = Join-Path $TargetSkillsRoot "_backups"
$ReportPath = Join-Path $TargetSkillsRoot "alteryx-skill-install-report.json"

$SkillPairs = @(
    @{
        Name = "alteryx-workflow-builder"
        Source = Join-Path $ToolingRoot "alteryx_workflow_builder"
        Target = Join-Path $TargetSkillsRoot "alteryx-workflow-builder"
    },
    @{
        Name = "alteryx-beautification"
        Source = Join-Path $ToolingRoot "alteryx-beautification"
        Target = Join-Path $TargetSkillsRoot "alteryx-beautification"
    }
)

function Copy-DirectoryFresh {
    param(
        [string]$Source,
        [string]$Target
    )
    if (!(Test-Path -LiteralPath $Source)) {
        throw "Missing source folder: $Source"
    }
    if (Test-Path -LiteralPath $Target) {
        Remove-Item -LiteralPath $Target -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Target | Out-Null
    robocopy $Source $Target /E /XD "__pycache__" ".git" /XF "*.pyc" "*.pyo" | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed from $Source to $Target with exit code $LASTEXITCODE"
    }
}

function Get-DirectoryDigest {
    param([string]$Path)
    if (!(Test-Path -LiteralPath $Path)) {
        return @{
            exists = $false
            file_count = 0
            sha256 = ""
        }
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $files = Get-ChildItem -LiteralPath $Path -Recurse -File |
        Where-Object {
            $_.FullName -notmatch "\\(__pycache__|\.pytest_cache|\.mypy_cache|\.git)\\" -and
            $_.Extension -notin @(".pyc", ".pyo")
        } |
        Sort-Object FullName
    $basePath = (Resolve-Path -LiteralPath $Path).Path.TrimEnd("\") + "\"
    $count = 0
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($basePath.Length).Replace("\", "/")
        $nameBytes = [System.Text.Encoding]::UTF8.GetBytes($relative)
        $zero = [byte[]](0)
        $content = [System.IO.File]::ReadAllBytes($file.FullName)
        [void]$sha.TransformBlock($nameBytes, 0, $nameBytes.Length, $null, 0)
        [void]$sha.TransformBlock($zero, 0, 1, $null, 0)
        [void]$sha.TransformBlock($content, 0, $content.Length, $null, 0)
        [void]$sha.TransformBlock($zero, 0, 1, $null, 0)
        $count += 1
    }
    [void]$sha.TransformFinalBlock([byte[]]::new(0), 0, 0)
    return @{
        exists = $true
        file_count = $count
        sha256 = ([BitConverter]::ToString($sha.Hash).Replace("-", "").ToLowerInvariant())
    }
}

New-Item -ItemType Directory -Force -Path $TargetSkillsRoot, $BackupRoot | Out-Null

$installed = @()
foreach ($pair in $SkillPairs) {
    if (!(Test-Path -LiteralPath $pair.Source)) {
        throw "Bundled skill source is missing: $($pair.Source)"
    }

    $backupPath = $null
    if (Test-Path -LiteralPath $pair.Target) {
        $backupPath = Join-Path $BackupRoot "$($pair.Name)-$Timestamp"
        Copy-DirectoryFresh -Source $pair.Target -Target $backupPath
    }

    Copy-DirectoryFresh -Source $pair.Source -Target $pair.Target
    $digest = Get-DirectoryDigest -Path $pair.Target
    $installed += [ordered]@{
        name = $pair.Name
        source = $pair.Source
        target = $pair.Target
        backup = $backupPath
        file_count = $digest.file_count
        sha256 = $digest.sha256
    }
}

$report = [ordered]@{
    schema_version = 1
    installed_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    target_skills_root = $TargetSkillsRoot
    package_root = $AppRoot
    installed = $installed
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
Write-Host "Installed/updated Codex Alteryx skills under: $TargetSkillsRoot"
Write-Host "Install report: $ReportPath"
