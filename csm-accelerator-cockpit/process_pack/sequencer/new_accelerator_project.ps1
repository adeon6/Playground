[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectFolder
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

$root = (Resolve-Path -LiteralPath (Split-Path -Parent $ProjectFolder) -ErrorAction Stop).Path
$projectName = Split-Path -Leaf $ProjectFolder
$projectPath = Join-Path $root $projectName

Ensure-Directory -Path $projectPath
foreach ($relative in @("docs", "data\raw", "data\generated", "status", "workflows")) {
    Ensure-Directory -Path (Join-Path $projectPath $relative)
}

$transcriptPath = Join-Path $projectPath "docs\01_customer_discovery_conversation.md"
if (-not (Test-Path -LiteralPath $transcriptPath)) {
    Set-Content -LiteralPath $transcriptPath -Encoding UTF8 -Value @"
# Customer Discovery Conversation

Project:
$projectName

Paste the consultant-client discovery transcript here.
"@
}

Write-Host "Project scaffold ready at: $projectPath"
Write-Host "Transcript intake path: $transcriptPath"
