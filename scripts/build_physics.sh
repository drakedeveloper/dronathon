set -eo pipefail
source /mnt/d/dronathon/scripts/env_wsl.sh
mkdir -p /opt/skyforge/plugins
export PKG_CONFIG_PATH="$(find /opt/ros/jazzy/opt -type d -name pkgconfig | paste -sd: -)${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
g++ -std=c++17 -O2 -shared -fPIC /mnt/d/dronathon/sim/plugins/WindDrag.cc -o /opt/skyforge/plugins/libSkyforgeWind.new.so $(pkg-config --cflags --libs gz-sim8 gz-transport13 gz-msgs10 gz-plugin2)
# Atomic replacement leaves any running simulator's loaded library intact.
mv /opt/skyforge/plugins/libSkyforgeWind.new.so /opt/skyforge/plugins/libSkyforgeWind.so
echo 'Built SkyforgeWind physics plugin'
