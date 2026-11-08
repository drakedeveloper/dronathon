#!/usr/bin/env bash
set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
cd /mnt/d/dronathon
python scripts/check_wsl.py
python scripts/validate_contracts.py
python -m pytest -q tests
glxinfo -B > artifacts/wsl-gpu.txt
gz sim --versions
