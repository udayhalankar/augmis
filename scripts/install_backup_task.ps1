param(
    [int]$IntervalMinutes = 15,
    [string]$TaskName = "Infomentica_Code_Backup"
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes must be 1 or greater."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backupDir = "D:\Backups\Infomentica_Backup"
$runnerPath = Join-Path $scriptDir "backup_code_windows.bat"
$logPath = Join-Path $backupDir "backup.log"

if (-not (Test-Path $runnerPath)) {
    throw "Backup runner not found: $runnerPath"
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

$taskCommand = "cmd.exe /c `"`"$runnerPath`"` >> `"$logPath`" 2>&1`""

$createArgs = @(
    "/Create"
    "/TN", $TaskName
    "/SC", "MINUTE"
    "/MO", $IntervalMinutes
    "/TR", $taskCommand
    "/F"
)

& schtasks.exe @createArgs | Out-Null

Write-Host "Installed Windows scheduled backup task."
Write-Host "Task Name: $TaskName"
Write-Host "Interval: Every $IntervalMinutes minute(s)"
Write-Host "Backup Folder: $backupDir"
Write-Host "Log File: $logPath"
