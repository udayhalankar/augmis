# Code Backup Routine

This project now includes a code-only backup routine that creates `.zip` archives and excludes generated or bulky folders such as:

- `frontend/node_modules`
- `frontend/.next`
- `.git`
- `.venv`
- `backend/index_store`
- `datasource`
- `.backups`

## Files

- [scripts/code_backup.py](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/code_backup.py)
- [scripts/backup_code.sh](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/backup_code.sh)
- [scripts/backup_code_windows.bat](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/backup_code_windows.bat)
- [scripts/install_backup_task.ps1](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/install_backup_task.ps1)
- [scripts/remove_backup_task.ps1](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/remove_backup_task.ps1)
- [scripts/install_backup_cron.sh](/mnt/d/Infomentica_POCs/Infomentica_DSS_Enterprise/scripts/install_backup_cron.sh)

## What it does

Each run:

1. Creates a timestamped ZIP file in `D:\Backups\Infomentica_Backup`
2. Includes project code and config files from this repository
3. Excludes generated folders and previous backups
4. Keeps the latest 10 backups
5. Also keeps the first backup created on each day

## Run Manually

```bash
./scripts/backup_code.sh
```

## Enable Automatic Backups With Windows Task Scheduler

Default schedule: every 60 minutes

Open PowerShell and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_backup_task.ps1
```

Custom schedule example: every 30 minutes

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_backup_task.ps1 -IntervalMinutes 30
```

Remove the scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\remove_backup_task.ps1
```

What this does:

- creates a Windows scheduled task named `Infomentica_Code_Backup`
- runs the existing backup logic through `wsl.exe`
- writes task output to `D:\Backups\Infomentica_Backup\backup.log`

## Legacy Linux Cron Option

This is still available, but it depends on WSL cron being installed and running.

```bash
chmod +x scripts/backup_code.sh scripts/install_backup_cron.sh
./scripts/install_backup_cron.sh
```

Custom schedule example: every 30 minutes

```bash
./scripts/install_backup_cron.sh "*/30 * * * *"
```

## Backup Output

Backups are written here:

```text
D:\Backups\Infomentica_Backup
```

Example file name:

```text
code_backup_2026-06-05_14-30-00.zip
```

## Notes

- The routine uses Python standard library only, so no extra package install is needed.
- The backup selection and retention logic are unchanged. Only the scheduler layer has been switched to Windows Task Scheduler.
- No application source files are modified by the scheduled task. It only creates ZIP backups and prunes older ZIPs inside `D:\Backups\Infomentica_Backup`.
