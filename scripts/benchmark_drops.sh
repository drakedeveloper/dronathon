set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
cd /mnt/d/dronathon
python scripts/benchmark_drops.py
