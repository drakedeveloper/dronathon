#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/tools"
cd "$ROOT/tools"
curl --fail --location --max-time 120 https://firmware.ardupilot.org/Copter/stable/SITL_x86_64_linux_gnu/arducopter -o arducopter.download
echo 'caed35e4cb796ec06cac40b09566a18251771486b1cbac5e2bf16b7a5ed5045d  arducopter.download' | sha256sum --check
mv arducopter.download arducopter
curl --fail --location --max-time 60 https://raw.githubusercontent.com/ArduPilot/ardupilot/fb773567896014da007bca58358704d4a0d8516f/Tools/autotest/default_params/copter.parm -o copter.parm.download
echo '5e01345b45d1c6190b28bece5638bbdd4cf1cce35e05bbbf480ab24d2b51aa0e  copter.parm.download' | sha256sum --check
mv copter.parm.download copter.parm
chmod +x arducopter
# If stable advances, checksum failure is intentional: review and pin a new version.
