set -eo pipefail
export SKYFORGE_RENDERER=software
export SKYFORGE_VISION=onnx
source /mnt/d/dronathon/scripts/env_wsl.sh
export QT_QPA_PLATFORM=xcb
cd /mnt/d/dronathon
python scripts/run_mission.py
