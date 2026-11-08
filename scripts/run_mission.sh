set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export SKYFORGE_VISION="${SKYFORGE_VISION:-onnx}"
export QT_QPA_PLATFORM=xcb
cd /mnt/d/dronathon
python scripts/run_mission.py "$@"
