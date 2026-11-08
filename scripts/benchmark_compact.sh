set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
cd /mnt/d/dronathon
/opt/skyforge/training-venv/bin/python scripts/export_compact_models.py
python scripts/evaluate_vision.py --backend onnx --size 384
