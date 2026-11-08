#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/artifacts/sitl"
cd "$ROOT/artifacts/sitl"
# Simulation origin is arbitrary; this is not a real flight location/configuration.
exec "$ROOT/tools/arducopter" --model + --speedup 1 --home 36.8,10.18,50,0 --defaults "$ROOT/tools/copter.parm" --serial0 tcp:0
