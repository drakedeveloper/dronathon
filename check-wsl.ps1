$ErrorActionPreference = 'Stop'
wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/check_wsl.sh
if ($LASTEXITCODE -ne 0) { throw 'WSL checks failed; inspect the terminal output.' }
