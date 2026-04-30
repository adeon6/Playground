@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\install-codex-alteryx-skills.ps1"
echo.
pause
