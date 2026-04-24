$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"
$PidFile = Join-Path $RuntimeDir "cockpit.pid"
$LogFile = Join-Path $RuntimeDir "uvicorn.log"
$ErrFile = Join-Path $RuntimeDir "uvicorn.err.log"
$Url = "http://127.0.0.1:8765"

$RequiredPaths = @(
    "csm_cockpit\app.py",
    "csm_cockpit\services.py",
    "csm_cockpit\templates\index.html",
    "csm_cockpit\templates\base.html",
    "csm_cockpit\static\cockpit.css",
    "sample_data\sanitized_geo_spatial_discovery.md",
    "process_pack\README.md",
    "process_pack\sequencer\sequence_config.json",
    "process_pack\03_workflow_build\sop_to_alteryx_super_prompt_pack.md"
)

function Assert-CompleteExtraction {
    $missing = @()
    foreach ($relativePath in $RequiredPaths) {
        $fullPath = Join-Path $Root $relativePath
        if (-not (Test-Path $fullPath)) {
            $missing += $relativePath
        }
    }

    if ($missing.Count -gt 0) {
        Write-Host "This app folder is incomplete. Missing required files:"
        foreach ($item in $missing) {
            Write-Host " - $item"
        }
        Write-Host ""
        Write-Host "Delete this extracted folder, re-extract the ZIP into a fresh folder, then run this launcher again."
        exit 1
    }
}

function Get-CockpitHealth {
    try {
        return Invoke-RestMethod -Uri "$Url/health" -TimeoutSec 2
    } catch {
        return $null
    }
}

function Test-CockpitForThisFolder {
    $health = Get-CockpitHealth
    if ($null -eq $health) {
        return $false
    }
    if ($health.app -ne "csm-accelerator-cockpit") {
        return $false
    }
    if ($health.app_root -ne $Root) {
        return $false
    }
    try {
        $homeResponse = Invoke-WebRequest -UseBasicParsing -Uri "$Url/" -TimeoutSec 3
        return $homeResponse.StatusCode -eq 200 -and $homeResponse.Content.Contains("CSM Accelerator Cockpit")
    } catch {
        return $false
    }
}

function Stop-StaleCockpitOnPort {
    $listeners = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -match "^python") {
            Write-Host "Stopping stale cockpit/Python server on port 8765 (PID $($process.Id))..."
            Stop-Process -Id $process.Id -Force
        }
    }
}

Set-Location $Root
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
Assert-CompleteExtraction

$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating local Python environment..."
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3 -m venv (Join-Path $Root ".venv")
    } else {
        & python -m venv (Join-Path $Root ".venv")
    }
}

Write-Host "Installing or refreshing app dependencies..."
& $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")

if (-not (Test-CockpitForThisFolder)) {
    Stop-StaleCockpitOnPort
    Write-Host "Starting CSM Accelerator Cockpit..."
    $arguments = @(
        "-m", "uvicorn",
        "csm_cockpit.app:app",
        "--host", "127.0.0.1",
        "--port", "8765"
    )
    $process = Start-Process `
        -FilePath $VenvPython `
        -ArgumentList $arguments `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $LogFile `
        -RedirectStandardError $ErrFile `
        -WindowStyle Hidden `
        -PassThru
    $process.Id | Set-Content -Path $PidFile -Encoding ASCII

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-CockpitForThisFolder) {
            $ready = $true
            break
        }
    }

    if (-not $ready) {
        Write-Host "The app did not become ready. Check:"
        Write-Host $ErrFile
        exit 1
    }
} else {
    Write-Host "Cockpit is already running."
}

Start-Process $Url
Write-Host ""
Write-Host "CSM Accelerator Cockpit is open at $Url"
Write-Host "Use 'Stop CSM Cockpit.bat' when you are done."
Write-Host ""
Read-Host "Press Enter to close this launcher window"
