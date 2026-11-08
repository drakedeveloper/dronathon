set -eo pipefail
export SKYFORGE_RENDERER=software
source /mnt/d/dronathon/scripts/env_wsl.sh
cd /mnt/d/dronathon
export QT_QPA_PLATFORM=xcb
python scripts/render_preview.py
