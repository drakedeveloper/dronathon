@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_cinematic_preview.ps1"
if errorlevel 1 pause
