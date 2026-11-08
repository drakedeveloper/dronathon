FROM ros:jazzy-ros-base-noble
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8 LC_ALL=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    python3-venv python3-opencv python3-numpy python3-yaml python3-pytest g++ pkg-config \
    mesa-utils libegl1 libgl1-mesa-dri ros-jazzy-ros-gz ros-jazzy-cv-bridge ros-jazzy-tf2-ros \
    && curl -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable noble main' > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends gz-harmonic \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv --system-site-packages /opt/skyforge/venv \
    && /opt/skyforge/venv/bin/pip install --no-cache-dir numpy==1.26.4 langgraph==1.2.20 jsonschema rich onnxruntime==1.31.1 msgpack==1.2.4
WORKDIR /mnt/d/dronathon
COPY . .
RUN mkdir -p /opt/skyforge/plugins /opt/skyforge/artifacts \
    && printf '%s\n' 'source /opt/ros/jazzy/setup.bash' 'source /opt/skyforge/venv/bin/activate' \
       'export SKYFORGE_ROOT=/mnt/d/dronathon' 'export PYTHONPATH=/mnt/d/dronathon' \
       'export ROS_DOMAIN_ID=30' 'export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST' > /opt/skyforge/env.sh \
    && bash scripts/build_physics.sh
ENV SKYFORGE_RENDERER=software QT_QPA_PLATFORM=offscreen SKYFORGE_VISION=onnx
EXPOSE 8766
ENTRYPOINT ["bash","scripts/container_entrypoint.sh"]
