set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export GZ_PARTITION=skyforge-training
export GZ_SIM_RESOURCE_PATH=/mnt/d/dronathon/sim/models${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}
cd /mnt/d/dronathon
python scripts/generate_training.py
