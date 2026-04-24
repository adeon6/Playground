$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"
$PidFile = Join-Path $RuntimeDir "cockpit.pid"
$LogFile = Join-Path $RuntimeDir "uvicorn.log"
$ErrFile = Join-Path $RuntimeDir "uvicorn.err.log"
$Url = "http://127.0.0.1:8765"

function Test-Cockpit {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "$Url/health" -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Set-Location $Root
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

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

if (-not (Test-Cockpit)) {
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
        if (Test-Cockpit) {
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

