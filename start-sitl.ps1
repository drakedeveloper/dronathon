$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
wsl -d Ubuntu -- bash /mnt/d/dronathon/scripts/start_sitl.sh
if ($LASTEXITCODE -ne 0) { throw 'SITL failed; see terminal output.' }
