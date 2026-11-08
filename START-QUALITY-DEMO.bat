@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-skyforge.ps1" -Reset -Observer -VisualQuality Balanced
pause
