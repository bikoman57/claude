<#
.SYNOPSIS
    Register Windows Scheduled Tasks for pre-market and post-market runs.
.DESCRIPTION
    Creates two scheduled tasks under \FinAgents\:
      - FinAgents-PreMarket:  Daily at 2:00 PM Israel time (= 7:00 AM ET)
      - FinAgents-PostMarket: Daily at 11:30 PM Israel time (= 4:30 PM ET)
    Times are Israel local time targeting US Eastern market hours.
    NOTE: DST transitions (US/Israel shift on different dates) can cause
    ~1 hour drift a few weeks per year. Adjust if needed.
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
# Times are Israel local time, targeting US Eastern market hours.
# Winter (both standard): IST=UTC+2, EST=UTC-5 → +7h offset
# Summer (both DST):      IDT=UTC+3, EDT=UTC-4 → +7h offset
# Transition weeks may drift ±1h when US/Israel DST dates differ.
$tasks = @(
    @{
        Name        = "FinAgents-PreMarket"
        Session     = "pre-market"
        Hour        = 14
        Minute      = 0
        Description = "Pre-market financial analysis (2:00 PM Israel = 7:00 AM ET)"
    },
    @{
        Name        = "FinAgents-PostMarket"
        Session     = "post-market"
        Hour        = 23
        Minute      = 30
        Description = "Post-market financial analysis (11:30 PM Israel = 4:30 PM ET)"
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

    # Trigger: Daily at specified time
    $trigger = New-ScheduledTaskTrigger `
        -Weekly `
        -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday,Saturday,Sunday `
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

    Write-Host "  Created: $($task.Name) at $($task.Hour):$("{0:D2}" -f $task.Minute) (daily)"
}

Write-Host ""
Write-Host "Tasks registered successfully."
Write-Host ""
Write-Host "Verify with:"
Write-Host "  Get-ScheduledTask -TaskPath '$TaskFolder'"
Write-Host ""
Write-Host "Test a run manually with:"
Write-Host "  Start-ScheduledTask -TaskPath '$TaskFolder' -TaskName 'FinAgents-PreMarket'"
