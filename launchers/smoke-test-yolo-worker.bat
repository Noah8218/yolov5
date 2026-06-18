@echo off
setlocal
if "%~1"=="" (
    echo Usage: %~nx0 IMAGE_PATH [additional PowerShell parameters]
    exit /b 2
)
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%smoke-test-yolo-worker.ps1" -ImagePath "%~1"
exit /b %ERRORLEVEL%
