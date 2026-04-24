[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectFolder,
    [string]$ProjectName,
    [switch]$Resume,
    [switch]$AllowDocxIntake,
    [ValidateSet("01_discovery", "02_guided_capture", "03_accelerator_sop", "04_workflow_build", "05_review")]
    [string]$StopAfterStage,
    [ValidateSet("01_discovery", "02_guided_capture", "03_accelerator_sop", "04_workflow_build", "05_review")]
    [string]$ForceStage
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-NowIso {
    (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Write-JsonFile {
    param(
        [string]$Path,
        [object]$Data
    )
    $json = $Data | ConvertTo-Json -Depth 20
    Set-Content -LiteralPath $Path -Value $json -Encoding UTF8
}

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Resolve-ArtifactPath {
    param(
        [string]$Root,
        [string]$RelativePath
    )
    Join-Path $Root $RelativePath
}

function Test-NonEmptyFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    return (Get-Item -LiteralPath $Path).Length -gt 0
}

function Test-TranscriptReady {
    param([string]$Path)
    if (-not (Test-NonEmptyFile -Path $Path)) {
        return $false
    }
    $text = Get-Content -LiteralPath $Path -Raw
    if ($text -match "Paste the consultant-client discovery transcript here\.") {
        return $false
    }
    return $true
}

function Test-ContentPattern {
    param(
        [string]$Path,
        [string[]]$Patterns
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        return $false
    }
    $text = Get-Content -LiteralPath $Path -Raw
    foreach ($pattern in $Patterns) {
        if ($text -match $pattern) {
            return $true
        }
    }
    return $false
}

function Get-WorkflowFiles {
    param(
        [string]$Root,
        [string]$Pattern
    )
    $folder = Split-Path -Path $Pattern -Parent
    $leaf = Split-Path -Path $Pattern -Leaf
    $target = Resolve-ArtifactPath -Root $Root -RelativePath $folder
    if (-not (Test-Path -LiteralPath $target)) {
        return @()
    }
    @(Get-ChildItem -LiteralPath $target -Filter $leaf -File | Sort-Object Name)
}

function Get-CodexRuntimeStatus {
    $cmd = Get-Command codex.exe -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        return [pscustomobject]@{
            available = $false
            executable = $null
            reason = "codex.exe was not found on PATH."
        }
    }

    return [pscustomobject]@{
        available = $false
        executable = $cmd.Source
        reason = "codex.exe is present but direct execution is blocked in this shell. Resolve the local runtime access issue before enabling unattended stage execution."
    }
}

function Get-StagePrompt {
    param(
        [string]$StageId,
        [string]$ProjectFolderPath,
        [pscustomobject]$Config
    )

    $packRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    $runbook = Join-Path $packRoot $Config.reference_files.runbook
    $rule = Join-Path $packRoot $Config.reference_files.operating_rule
    $interview = Join-Path $packRoot $Config.reference_files.interview_script
    $captureTemplate = Join-Path $packRoot $Config.reference_files.guided_capture_template
    $captureToSop = Join-Path $packRoot $Config.reference_files.guided_capture_to_sop_prompt
    $sopTemplate = Join-Path $packRoot $Config.reference_files.sop_template
    $buildPack = Join-Path $packRoot $Config.reference_files.workflow_build_prompt_pack

    $doc01 = Resolve-ArtifactPath -Root $ProjectFolderPath -RelativePath $Config.entry_rule.canonical_transcript_markdown
    $doc02 = Resolve-ArtifactPath -Root $ProjectFolderPath -RelativePath $Config.artifacts.guided_capture
    $doc03 = Resolve-ArtifactPath -Root $ProjectFolderPath -RelativePath $Config.artifacts.accelerator_sop
    $gapLog = Resolve-ArtifactPath -Root $ProjectFolderPath -RelativePath $Config.artifacts.gap_log
    $assessment = Resolve-ArtifactPath -Root $ProjectFolderPath -RelativePath $Config.artifacts.architecture_assessment

    switch ($StageId) {
        "02_guided_capture" {
            return @"
Continue the accelerator operating-system sequence for project folder:
$ProjectFolderPath

Use these references as the source of truth:
- Runbook: $runbook
- Operating rule: $rule
- Discovery interview script: $interview
- Guided capture template: $captureTemplate
- Skill: consultant-client-sop-extractor skill

Your task:
- Read the discovery transcript at $doc01
- Produce only the next stage artifact: $doc02
- Preserve the distinction between Confirmed, Assumed, and Unknown / To Discover
- Keep the document compact and build-oriented
- Do not generate the SOP yet

Completion requirements:
- The output file exists
- It is non-empty
- It clearly includes confirmed / assumed / unknown treatment
"@
        }
        "03_accelerator_sop" {
            return @"
Continue the accelerator operating-system sequence for project folder:
$ProjectFolderPath

Use these references as the source of truth:
- Runbook: $runbook
- Operating rule: $rule
- Guided capture to SOP prompt: $captureToSop
- SOP template: $sopTemplate

Your task:
- Read the guided capture at $doc02
- Produce only these next stage artifacts:
  - $doc03
  - $gapLog
- Make the SOP buildable for the first slice
- Surface gaps honestly instead of inventing certainty
- Do not build the workflow yet

Completion requirements:
- Both files exist
- The SOP is non-empty
- The SOP defines scope, outputs, core logic, and validation expectations
"@
        }
        "04_workflow_build" {
            return @"
Continue the accelerator operating-system sequence for project folder:
$ProjectFolderPath

Use these references as the source of truth:
- Runbook: $runbook
- Workflow build prompt pack: $buildPack
- Skill first: alteryx-workflow-builder skill

Your task:
- Read the SOP at $doc03
- Build the next implementation stage
- Produce a primary workflow under the project's workflows folder matching 00_*.yxmd
- Produce or update the architecture assessment at $assessment
- Update the gap log if implementation required new assumptions
- Validate the workflow before considering the stage complete

Completion requirements:
- A workflow file exists under workflows\00_*.yxmd
- The architecture assessment exists
- Validation has been completed
"@
        }
        "05_review" {
            return @"
Continue the accelerator operating-system sequence for project folder:
$ProjectFolderPath

Use these references as the source of truth:
- Runbook: $runbook

Your task:
- Review the generated workflow, outputs, assessment, and gap log
- Decide whether the project is demo-ready, blocked, or needs iteration
- Summarize the result in the pipeline status and project log
- Do not generate a new implementation artifact in this stage

Completion requirements:
- The pipeline status is updated
- The next action is explicit
"@
        }
        default {
            return @"
The project folder is ready at:
$ProjectFolderPath

Stage 01 is the discovery evidence intake stage. Place the consultant transcript at:
$doc01

Then rerun the sequencer.
"@
        }
    }
}

function Test-StageComplete {
    param(
        [pscustomobject]$Stage,
        [string]$ProjectRoot,
        [pscustomobject]$Config
    )

    switch ($Stage.id) {
        "01_discovery" {
            $mdPath = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.entry_rule.canonical_transcript_markdown
            return Test-TranscriptReady -Path $mdPath
        }
        "02_guided_capture" {
            $path = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.artifacts.guided_capture
            return (Test-NonEmptyFile -Path $path) -and (Test-ContentPattern -Path $path -Patterns @("Confirmed", "Assumed", "Unknown"))
        }
        "03_accelerator_sop" {
            $sop = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.artifacts.accelerator_sop
            $gap = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.artifacts.gap_log
            $hasSections = Test-ContentPattern -Path $sop -Patterns @("scope", "output", "validation")
            return (Test-NonEmptyFile -Path $sop) -and (Test-NonEmptyFile -Path $gap) -and $hasSections
        }
        "04_workflow_build" {
            $workflowFiles = Get-WorkflowFiles -Root $ProjectRoot -Pattern $Config.artifacts.workflow_glob
            $assessment = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.artifacts.architecture_assessment
            return (@($workflowFiles).Length -gt 0) -and (Test-NonEmptyFile -Path $assessment)
        }
        "05_review" {
            $statusFile = Resolve-ArtifactPath -Root $ProjectRoot -RelativePath $Config.artifacts.status_file
            return Test-NonEmptyFile -Path $statusFile
        }
        default {
            return $false
        }
    }
}

function Get-NextStage {
    param(
        [pscustomobject]$Config,
        [string]$ProjectRoot,
        [string]$ForcedStage
    )

    if ($ForcedStage) {
        return $Config.stages | Where-Object { $_.id -eq $ForcedStage } | Select-Object -First 1
    }

    foreach ($stage in $Config.stages) {
        if (-not (Test-StageComplete -Stage $stage -ProjectRoot $ProjectRoot -Config $Config)) {
            return $stage
        }
    }

    return $null
}

function Update-Status {
    param(
        [string]$StatusFile,
        [hashtable]$StatusData
    )
    Write-JsonFile -Path $StatusFile -Data ([pscustomobject]$StatusData)
}

function Append-Log {
    param(
        [string]$LogFile,
        [string]$Message
    )
    Add-Content -LiteralPath $LogFile -Value $Message
}

$sequencerRoot = Split-Path -Parent $PSCommandPath
$configPath = Join-Path $sequencerRoot "sequence_config.json"
$config = Read-JsonFile -Path $configPath
if ($null -eq $config) {
    throw "Could not read sequence config at $configPath"
}

$projectRoot = (Resolve-Path -LiteralPath $ProjectFolder).Path
if (-not $ProjectName) {
    $ProjectName = Split-Path -Leaf $projectRoot
}

foreach ($relativeDir in $config.project_structure) {
    Ensure-Directory -Path (Resolve-ArtifactPath -Root $projectRoot -RelativePath $relativeDir)
}

$statusFile = Resolve-ArtifactPath -Root $projectRoot -RelativePath $config.artifacts.status_file
$logFile = Resolve-ArtifactPath -Root $projectRoot -RelativePath $config.artifacts.log_file
$promptFile = Resolve-ArtifactPath -Root $projectRoot -RelativePath $config.artifacts.prompt_file

if (-not (Test-Path -LiteralPath $logFile)) {
    Set-Content -LiteralPath $logFile -Encoding UTF8 -Value "# Pipeline Log`r`n"
}

$runtime = Get-CodexRuntimeStatus
$currentStatus = Read-JsonFile -Path $statusFile

$nextStage = Get-NextStage -Config $config -ProjectRoot $projectRoot -ForcedStage $ForceStage

if ($null -eq $nextStage) {
    $completed = [ordered]@{
        project_name = $ProjectName
        current_stage = $null
        status = "complete"
        last_completed_stage = "05_review"
        next_expected_artifact = $null
        started_at = if ($currentStatus) { $currentStatus.started_at } else { Get-NowIso }
        updated_at = Get-NowIso
        blocker = $null
        runtime = $runtime
    }
    Update-Status -StatusFile $statusFile -StatusData $completed
    Append-Log -LogFile $logFile -Message "`r`n## $(Get-NowIso)`r`nPipeline already complete.`r`n"
    Write-Host "Pipeline already complete."
    exit 0
}

$prompt = Get-StagePrompt -StageId $nextStage.id -ProjectFolderPath $projectRoot -Config $config
Set-Content -LiteralPath $promptFile -Value $prompt -Encoding UTF8

$completedStages = @()
foreach ($stage in @($config.stages)) {
    if (Test-StageComplete -Stage $stage -ProjectRoot $projectRoot -Config $config) {
        $completedStages += $stage
    }
}
$lastCompletedStage = $null
if (@($completedStages).Length -gt 0) {
    $lastCompletedStage = ($completedStages | Select-Object -Last 1).id
}

$status = [ordered]@{
    project_name = $ProjectName
    current_stage = $nextStage.id
    status = if ($runtime.available) { "ready_to_run" } else { "blocked" }
    last_completed_stage = $lastCompletedStage
    next_expected_artifact = ($nextStage.outputs | Select-Object -First 1)
    started_at = if ($currentStatus) { $currentStatus.started_at } else { Get-NowIso }
    updated_at = Get-NowIso
    blocker = if ($runtime.available) { $null } else { $runtime.reason }
    runtime = $runtime
    prompt_file = $promptFile
}

Update-Status -StatusFile $statusFile -StatusData $status
Append-Log -LogFile $logFile -Message "`r`n## $(Get-NowIso)`r`n- Current stage: $($nextStage.id)`r`n- Runtime status: $($status.status)`r`n- Prompt written: $promptFile`r`n"

Write-Host "Current stage: $($nextStage.id)"
Write-Host "Prompt written to: $promptFile"
if (-not $runtime.available) {
    Write-Warning $runtime.reason
    exit 0
}

Write-Host "Codex runtime is available. Wire the stage execution command into this script to move from prompt generation to unattended stage execution."
