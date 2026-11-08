#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8 LC_ALL=C.UTF-8
. /etc/os-release
test "$VERSION_ID" = 24.04
apt-get update -qq
apt-get install --no-install-recommends -y ca-certificates curl gnupg python3-venv git mesa-utils g++ pkg-config python3-opencv
# Official ROS signing key; APT verifies package repository signatures.
curl -fsSL --max-time 60 https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
printf '%s\n' 'deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main' > /etc/apt/sources.list.d/ros2.list
apt-get update -qq
apt-get install --no-install-recommends -y ros-jazzy-ros-base ros-jazzy-ros-gz ros-jazzy-cv-bridge ros-jazzy-tf2-ros python3-numpy python3-yaml python3-pytest
mkdir -p /opt/skyforge /opt/skyforge/artifacts
python3 -m venv --system-site-packages /opt/skyforge/venv
/opt/skyforge/venv/bin/python -m pip install --no-cache-dir --disable-pip-version-check langgraph==1.2.20 jsonschema rich onnxruntime==1.31.1 msgpack==1.2.4
cat > /opt/skyforge/env.sh <<'EOF'
#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source /opt/skyforge/venv/bin/activate
export ROS_DOMAIN_ID=30
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME="${SKYFORGE_GPU:-NVIDIA}"
export SKYFORGE_ROOT=/mnt/d/dronathon
export PYTHONPATH="$SKYFORGE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
EOF
chmod +x /opt/skyforge/env.sh
apt-get clean
dpkg-query -W 'ros-jazzy-*' > /opt/skyforge/artifacts/ros-packages.tsv
/opt/skyforge/venv/bin/python -m pip freeze > /opt/skyforge/artifacts/python-lock.txt
echo 'Provisioning finished. source /opt/skyforge/env.sh'
