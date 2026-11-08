#!/usr/bin/env bash
# Temporary shared-WSL kernel setting; prevents multi-GB Windows crash captures.
# Does not delete any files. Restore after debugging with --restore.
set -euo pipefail
backup=/opt/skyforge/artifacts/core-pattern.original
mkdir -p /opt/skyforge/artifacts
if [ "${1:-}" = --restore ]; then
  test -f "$backup"
  cat "$backup" > /proc/sys/kernel/core_pattern
else
  if [ ! -f "$backup" ]; then cat /proc/sys/kernel/core_pattern > "$backup"; fi
  printf '%s\n' '|/bin/false' > /proc/sys/kernel/core_pattern
fi
printf 'Active shared-WSL core capture policy: '
cat /proc/sys/kernel/core_pattern
