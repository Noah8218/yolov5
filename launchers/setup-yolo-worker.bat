@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%ensure-yolo-environment.ps1" -InstallIfMissing
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo YOLO worker setup failed with exit code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
