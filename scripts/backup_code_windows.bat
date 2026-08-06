@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT_WIN=%%~fI"

for /f "usebackq delims=" %%I in (`wsl.exe wslpath "%REPO_ROOT_WIN%"`) do set "REPO_ROOT_WSL=%%I"

if not defined REPO_ROOT_WSL (
  echo Failed to resolve repository path for WSL.
  exit /b 1
)

wsl.exe bash -lc "cd \"%REPO_ROOT_WSL%\" && ./scripts/backup_code.sh"
exit /b %ERRORLEVEL%
