#!/usr/bin/env bash
set -eo pipefail
source /opt/skyforge/env.sh
ulimit -c 0
export GALLIUM_DRIVER=llvmpipe LIBGL_ALWAYS_SOFTWARE=1
python -m station.server &
station=$!
trap 'kill "$station" 2>/dev/null || true' EXIT
python scripts/run_mission.py "$@"
