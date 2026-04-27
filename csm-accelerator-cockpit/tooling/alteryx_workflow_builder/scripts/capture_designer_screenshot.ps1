param(
    [Parameter(Mandatory = $true)]
    [string]$WorkflowPath,

    [string]$OutputPath = "",

    [int]$StartupWaitSeconds = 10,

    [int]$OpenWaitSeconds = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName Microsoft.VisualBasic

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class WinApi {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
"@

function Get-DesignerProcess {
    $procs = Get-Process AlteryxGui -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
    if ($procs) {
        return $procs | Sort-Object StartTime | Select-Object -First 1
    }
    return $null
}

function Focus-Window([System.Diagnostics.Process]$Process) {
    [WinApi]::ShowWindowAsync($Process.MainWindowHandle, 3) | Out-Null
    Start-Sleep -Milliseconds 300
    [WinApi]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500
    [Microsoft.VisualBasic.Interaction]::AppActivate($Process.MainWindowTitle) | Out-Null
    Start-Sleep -Milliseconds 500
    [WinApi]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500
}

function Test-WindowForeground([System.Diagnostics.Process]$Process) {
    $fg = [WinApi]::GetForegroundWindow()
    if ($fg -eq [IntPtr]::Zero) {
        return $false
    }
    [uint32]$winPid = 0
    [void][WinApi]::GetWindowThreadProcessId($fg, [ref]$winPid)
    return ($winPid -eq [uint32]$Process.Id)
}

function Ensure-WindowFocus([System.Diagnostics.Process]$Process, [int]$Retries = 5) {
    for ($i = 0; $i -lt $Retries; $i++) {
        Focus-Window $Process
        if (Test-WindowForeground $Process) {
            return
        }
        Start-Sleep -Milliseconds 400
    }
    throw "Could not bring the requested Designer window to the foreground."
}

function Wait-ForOpenDialog([int]$TimeoutSeconds = 10) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $dialogs = Get-Process | Where-Object { $_.MainWindowTitle -like "*Open*" -and $_.MainWindowHandle -ne 0 }
        if ($dialogs) {
            return $dialogs | Select-Object -First 1
        }
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $deadline)
    throw "Open dialog did not appear."
}

function Wait-ForDesignerWindow([string]$WorkflowName, [int]$TimeoutSeconds = 15) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $procs = Get-Process AlteryxGui -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
        $match = $procs | Where-Object { $_.MainWindowTitle -like "*$WorkflowName*" } | Sort-Object StartTime -Descending | Select-Object -First 1
        if ($match) {
            return $match
        }
        Start-Sleep -Milliseconds 400
    } while ((Get-Date) -lt $deadline)
    return $null
}

function Capture-Window([IntPtr]$Handle, [string]$Path) {
    $rect = New-Object WinApi+RECT
    if (-not [WinApi]::GetWindowRect($Handle, [ref]$rect)) {
        throw "Could not get window rect."
    }

    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top
    if ($width -le 0 -or $height -le 0) {
        throw "Window bounds were invalid."
    }

    $bitmap = New-Object System.Drawing.Bitmap $width, $height
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $hdc = $graphics.GetHdc()
    try {
        $printed = [WinApi]::PrintWindow($Handle, $hdc, 0)
    } finally {
        $graphics.ReleaseHdc($hdc)
    }
    if (-not $printed) {
        $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
    }
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose()
    $bitmap.Dispose()
}

$resolvedWorkflow = (Resolve-Path $WorkflowPath).Path
if (-not $OutputPath) {
    $OutputPath = [System.IO.Path]::ChangeExtension($resolvedWorkflow, ".designer.png")
}
$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
$workflowStem = [System.IO.Path]::GetFileNameWithoutExtension($resolvedWorkflow)
$workflowName = [System.IO.Path]::GetFileName($resolvedWorkflow)

# Prefer direct launch first. This works for many .yxmd/.yxwz cases and is truer than menu automation.
$beforeIds = @(Get-Process AlteryxGui -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
if ([System.IO.Path]::GetExtension($resolvedWorkflow).ToLowerInvariant() -eq ".yxwz") {
    Start-Process -FilePath $resolvedWorkflow -Verb Edit | Out-Null
} else {
    Start-Process -FilePath "C:\Program Files\Alteryx\bin\AlteryxGui.exe" -ArgumentList ('"' + $resolvedWorkflow + '"') | Out-Null
}
Start-Sleep -Seconds $StartupWaitSeconds
$designer = Wait-ForDesignerWindow -WorkflowName $workflowName -TimeoutSeconds 8
if (-not $designer) {
    $designer = Wait-ForDesignerWindow -WorkflowName $workflowStem -TimeoutSeconds 4
}

if (-not $designer) {
    $designer = Get-DesignerProcess
    if (-not $designer) {
        $designer = Start-Process -FilePath "C:\Program Files\Alteryx\bin\AlteryxGui.exe" -PassThru
        Start-Sleep -Seconds $StartupWaitSeconds
        $designer = Get-DesignerProcess
        if (-not $designer) {
            throw "Could not find a running Alteryx Designer window after launch."
        }
    }

    Focus-Window $designer
    [System.Windows.Forms.SendKeys]::SendWait("^o")
    Start-Sleep -Seconds 2
    [System.Windows.Forms.Clipboard]::SetText($resolvedWorkflow)
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Seconds $OpenWaitSeconds
    $designer = Wait-ForDesignerWindow -WorkflowName $workflowName -TimeoutSeconds 5
    if (-not $designer) {
        $designer = Wait-ForDesignerWindow -WorkflowName $workflowStem -TimeoutSeconds 3
    }
    if (-not $designer) {
        throw "Could not confirm that Designer opened the requested workflow."
    }
}

Ensure-WindowFocus $designer
[System.Windows.Forms.SendKeys]::SendWait("^%r")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^%c")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^%t")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait("^+w")
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait("^0")
Start-Sleep -Seconds 2
Capture-Window $designer.MainWindowHandle $resolvedOutput
Write-Output "Captured $resolvedOutput"
