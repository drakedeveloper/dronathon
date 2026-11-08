set -eo pipefail
cd /mnt/d/dronathon
exec /opt/skyforge/training-venv/bin/python scripts/train_yolo.py "$@"
