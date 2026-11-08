param([switch]$Gui)
$ErrorActionPreference = 'Stop'
if ($Gui) { wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/run_mission.sh --gui }
else { wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/run_mission.sh }
