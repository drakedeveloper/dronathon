# Verified runtime setup

Dedicated WSL2 distribution: **Dronathon**, Ubuntu 24.04.5. Its Linux filesystem is `D:\dronathon\runtime\ubuntu\ext4.vhdx`; the official Ubuntu image SHA256 was checked against Microsoft's distribution manifest. Existing Ubuntu was retained.

Installed and checked: ROS2 Jazzy, Gazebo Harmonic 8.15.0, Python 3.12.3, OpenCV 4.6.0 with cv_bridge, NumPy 1.26.4, LangGraph 1.2.20, ONNX Runtime 1.31.1 (CPU provider, not CUDA). Native Gazebo transport Python bindings are available. A small optimized C++ body-wind/drag plugin was compiled with installed Gazebo headers.

GPU: project-scoped `GALLIUM_DRIVER=d3d12` and `MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA` produced hardware-accelerated OpenGL on RTX 2050; the initial default had used llvmpipe. Qt GUI startup required `QT_QPA_PLATFORM=xcb` to avoid a driver/GLX startup crash; it subsequently ran. These findings do not guarantee every scene/driver combination is stable.

Verified smoke test: 264 rendered camera frames, 659 odometry samples, climb from 0.053 to 1.281 m, horizontal translation about 0.91 m, descent to 0.055 m. The fixed smoke camera is not an onboard-camera calibration. ROS publisher/subscriber exchange, cv_bridge conversion, contract validation and 31 current unit tests pass in Linux. Later tests may increase this count.

## Commands from PowerShell

```powershell
cd D:\dronathon
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-wsl.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-wsl.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-station.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-mission.ps1
```

Dashboard: http://127.0.0.1:8766 . Port 8080 was already occupied on Windows; it was left untouched. The station binds loopback. Run station and mission in separate terminals. `start-mission.ps1 -Gui` also opens Gazebo's viewer; the dashboard includes local observer/onboard camera taps. Do not run a second mission instance in the same Gazebo partition.

`watch-simulation.ps1` launches an inspection world; it does not run the rescue policy. Stop an existing inspection world before measuring mission performance to avoid duplicate rendering load. Dataset generation and smoke tests use separate Gazebo partitions. Ctrl+C in the owned launcher shuts down its child processes.

Runtime software and models are still being integrated/tested; smoke-test success is not a completed competition mission. First mission trial delivered one virtual supply and exposed a routing/return-latch issue, which was fixed. Physical payload release and independent mission acceptance remain pending at this report's creation.

The local radio key is generated under `/opt/skyforge/radio.key`, mode 0600; it is never printed or committed. Radio frames include CRC/HMAC and replay counters; these provide integrity/authentication, not transport confidentiality. Camera taps and full diagnostic state are local development channels, separate from the <1 KB radio frames.

Home machine reported by user: Windows 11, 16 GB RAM, RTX 5060 with 8 GB VRAM. Remote access/storage have not been inspected. No remote setup or GPU training performance is claimed yet.
