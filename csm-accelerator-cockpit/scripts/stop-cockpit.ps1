$ErrorActionPreference = "SilentlyContinue"

$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root ".runtime"
$PidFile = Join-Path $RuntimeDir "cockpit.pid"

if (Test-Path $PidFile) {
    $processId = Get-Content $PidFile | Select-Object -First 1
    if ($processId) {
        Stop-Process -Id ([int]$processId) -Force
        Remove-Item $PidFile -Force
        Write-Host "Stopped CSM Accelerator Cockpit."
        exit 0
    }
}

Write-Host "No cockpit process id was found. If the browser is still open, close it or stop the Python process manually."

