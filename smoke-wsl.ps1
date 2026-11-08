$ErrorActionPreference = 'Stop'
wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/run_gazebo_smoke.sh
if ($LASTEXITCODE -ne 0) { throw 'Gazebo smoke test failed; inspect artifacts/gazebo-smoke/.' }
