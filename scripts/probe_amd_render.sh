set -eo pipefail
export SKYFORGE_GPU=AMD
source /mnt/d/dronathon/scripts/env_wsl.sh
export QT_QPA_PLATFORM=xcb
cd /mnt/d/dronathon
glxinfo -B > artifacts/amd-renderer.txt
python scripts/render_preview.py
