$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe scripts/check_env.py
if ($LASTEXITCODE -ne 0) { throw 'Environment check failed' }
& .\.venv\Scripts\python.exe scripts/vision_check.py
if ($LASTEXITCODE -ne 0) { throw 'Vision check failed' }
& .\.venv\Scripts\python.exe -m pytest -q tests
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
