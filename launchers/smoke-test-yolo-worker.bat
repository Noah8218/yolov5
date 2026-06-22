@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%smoke-test-yolo-worker.ps1" %*
exit /b %ERRORLEVEL%
