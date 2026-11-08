#!/usr/bin/env bash
set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
export GZ_PARTITION=skyforge-smoke
cd /mnt/d/dronathon
python scripts/smoke_gazebo.py
