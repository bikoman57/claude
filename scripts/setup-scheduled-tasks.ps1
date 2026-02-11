<#
.SYNOPSIS
    Register Windows Scheduled Tasks for pre-market and post-market runs.
.DESCRIPTION
    Creates two scheduled tasks under \FinAgents\:
      - FinAgents-PreMarket:  Weekdays at 7:00 AM (local time)
      - FinAgents-PostMarket: Weekdays at 4:30 PM (local time)
    Must be run as Administrator.
.PARAMETER Remove
    Remove existing tasks instead of creating them.
#>
param(
    [switch]$Remove
)

$ErrorActionPreference = "Stop"

$ProjectDir = "C:\Users\texcu\OneDrive\Documents\claude"
$ScriptPath = Join-Path $ProjectDir "scripts\scheduled-run.ps1"
$TaskFolder = "\FinAgents\"

# Verify script exists
if (-not $Remove -and -not (Test-Path $ScriptPath)) {
    Write-Error "Wrapper script not found: $ScriptPath"
    exit 1
}

# --- Task definitions ---
$tasks = @(
    @{
        Name        = "FinAgents-PreMarket"
        Session     = "pre-market"
        Hour        = 7
        Minute      = 0
        Description = "Pre-market financial analysis: data pipeline + Claude AI agent analysis + Telegram"
    },
    @{
        Name        = "FinAgents-PostMarket"
        Session     = "post-market"
        Hour        = 16
        Minute      = 30
        Description = "Post-market financial analysis: data pipeline + Claude AI agent analysis + Telegram"
    }
)

if ($Remove) {
    foreach ($task in $tasks) {
        Write-Host "Removing task: $($task.Name)..."
        Unregister-ScheduledTask -TaskName $task.Name -TaskPath $TaskFolder `
            -Confirm:$false -ErrorAction SilentlyContinue
    }
    Write-Host "Tasks removed."
    exit 0
}

foreach ($task in $tasks) {
    Write-Host "Creating task: $($task.Name)..."

    # Action: PowerShell running the wrapper script
    $action = New-ScheduledTaskAction `
        -Execute "powershell.exe" `
        -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$ScriptPath`" -Session $($task.Session)" `
        -WorkingDirectory $ProjectDir

    # Trigger: Weekdays at specified time
    $trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
        -At ("{0}:{1:D2}" -f $task.Hour, $task.Minute)

    # Settings
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -DontStopOnIdleEnd `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
        -RestartCount 1 `
        -RestartInterval (New-TimeSpan -Minutes 5)

    # Principal: Run whether user is logged in or not
    $principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType S4U `
        -RunLevel Limited

    # Register the task
    Register-ScheduledTask `
        -TaskName $task.Name `
        -TaskPath $TaskFolder `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description $task.Description `
        -Force

    Write-Host "  Created: $($task.Name) at $($task.Hour):$("{0:D2}" -f $task.Minute) (weekdays)"
}

Write-Host ""
Write-Host "Tasks registered successfully."
Write-Host ""
Write-Host "Verify with:"
Write-Host "  Get-ScheduledTask -TaskPath '$TaskFolder'"
Write-Host ""
Write-Host "Test a run manually with:"
Write-Host "  Start-ScheduledTask -TaskPath '$TaskFolder' -TaskName 'FinAgents-PreMarket'"
