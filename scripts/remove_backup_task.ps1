param(
    [string]$TaskName = "Infomentica_Code_Backup"
)

$ErrorActionPreference = "Stop"

& schtasks.exe /Query /TN $TaskName *> $null

if ($LASTEXITCODE -eq 0) {
    & schtasks.exe /Delete /TN $TaskName /F | Out-Null
    Write-Host "Removed Windows scheduled backup task: $TaskName"
} else {
    Write-Host "No scheduled backup task found with name: $TaskName"
}
