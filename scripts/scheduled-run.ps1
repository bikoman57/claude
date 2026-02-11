<#
.SYNOPSIS
    Wrapper for pre-market and post-market scheduled runs.
.DESCRIPTION
    Called by Windows Task Scheduler. Loads environment, runs the Python
    scheduled runner, and logs output.
.PARAMETER Session
    Either "pre-market" or "post-market"
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("pre-market", "post-market")]
    [string]$Session
)

$ErrorActionPreference = "Stop"

# --- Configuration ---
$ProjectDir = "C:\Users\texcu\OneDrive\Documents\claude"
$UvExe = "C:\Users\texcu\.local\bin\uv.exe"
$LogDir = Join-Path $ProjectDir "data\logs"
$DateStr = (Get-Date).ToString("yyyy-MM-dd")
$LogFile = Join-Path $LogDir "${DateStr}_${Session}_wrapper.log"

# --- Helpers ---
function Write-Log {
    param([string]$Message)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "$timestamp $Message"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

# --- Pre-flight ---
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

Write-Log "=========================================="
Write-Log "SCHEDULED RUN: $Session"
Write-Log "Project: $ProjectDir"
Write-Log "=========================================="

# Skip weekends
$dayOfWeek = (Get-Date).DayOfWeek
if ($dayOfWeek -eq "Saturday" -or $dayOfWeek -eq "Sunday") {
    Write-Log "SKIP: Weekend ($dayOfWeek). Exiting."
    exit 0
}

# Check uv exists
if (-not (Test-Path $UvExe)) {
    Write-Log "ERROR: uv not found at $UvExe"
    exit 1
}

# Check project dir exists
if (-not (Test-Path $ProjectDir)) {
    Write-Log "ERROR: Project directory not found: $ProjectDir"
    exit 1
}

# --- Load .env file ---
$envFile = Join-Path $ProjectDir ".env"
if (Test-Path $envFile) {
    Write-Log "Loading .env file..."
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

# --- Run the scheduled Python module ---
Write-Log "Starting Python scheduled runner..."
$startTime = Get-Date
$stdoutLog = Join-Path $LogDir "${DateStr}_${Session}_stdout.log"
$stderrLog = Join-Path $LogDir "${DateStr}_${Session}_stderr.log"

try {
    $process = Start-Process -FilePath $UvExe `
        -ArgumentList "run", "python", "-m", "app.scheduler", $Session `
        -WorkingDirectory $ProjectDir `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog

    # Wait up to 90 minutes (pipeline ~2min + Claude ~60min + buffer)
    $timeoutMs = 90 * 60 * 1000
    $exited = $process.WaitForExit($timeoutMs)

    if (-not $exited) {
        Write-Log "ERROR: Process timed out after 90 minutes. Killing..."
        $process.Kill()
        exit 1
    }

    $duration = ((Get-Date) - $startTime).TotalMinutes
    Write-Log "Process exited with code $($process.ExitCode) after $([math]::Round($duration, 1)) minutes"

    if ($process.ExitCode -ne 0) {
        Write-Log "WARNING: Non-zero exit code: $($process.ExitCode)"
        if (Test-Path $stderrLog) {
            $lastLines = Get-Content $stderrLog -Tail 10
            Write-Log "Last stderr lines:"
            $lastLines | ForEach-Object { Write-Log "  $_" }
        }
    }

} catch {
    Write-Log "ERROR: Exception running scheduled task: $_"
    exit 1
}

Write-Log "=========================================="
Write-Log "SCHEDULED RUN COMPLETE"
Write-Log "=========================================="

exit $process.ExitCode
