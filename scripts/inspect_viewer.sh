set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export GZ_PARTITION=skyforge-mission
gz service -i -s /gui/follow
gz service -i -s /gui/move_to
