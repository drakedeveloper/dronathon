#!/usr/bin/env bash
source /opt/skyforge/env.sh
ulimit -c 0
# Scoped to this project shell; no global Windows/WSL graphics changes.
if [ "${SKYFORGE_RENDERER:-gpu}" = software ]; then
  export GALLIUM_DRIVER=llvmpipe
  export LIBGL_ALWAYS_SOFTWARE=1
else
  export GALLIUM_DRIVER=d3d12
  # This laptop's NVIDIA GLX context crashes in the WSL driver. AMD D3D12
  # passed an actual Gazebo RGB render. Override on a different machine.
  export MESA_D3D12_DEFAULT_ADAPTER_NAME="${SKYFORGE_GPU:-AMD}"
fi
