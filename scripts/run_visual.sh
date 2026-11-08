set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export GZ_SIM_RESOURCE_PATH=/mnt/d/dronathon/sim/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/skyforge/plugins${GZ_SIM_SYSTEM_PLUGIN_PATH:+:$GZ_SIM_SYSTEM_PLUGIN_PATH}
cd /mnt/d/dronathon
python -m skyforge.scene
export QT_QPA_PLATFORM=xcb
exec gz sim -r -v 2 /mnt/d/dronathon/sim/generated/coast.sdf
