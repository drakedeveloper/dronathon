# Dronathon 3.0 preparation

**Teammates: start with [FRIEND_QUICKSTART.md](docs/FRIEND_QUICKSTART.md).** It
covers cloning, portable tests, WSL/Gazebo provisioning, models and known gaps.
Current implementation includes both AI agents and detectors. This is an
in-progress prototype; the notes below include historical setup milestones.

**Latest measured run:** three virtual deliveries, autonomous return with
5.48 Wh from 15 Wh, zero geometric hazard entries/static collisions, and
171 simulated seconds. Timing still exceeds the 150 ms requirement. See
[evidence and limits](validation/README.md).

Prepared 7 November 2026 in `D:\dronathon`. **The official specification has now arrived:** see [official requirements](docs/official-requirements.md). The earlier research notes and competition plan are pre-brief preparation; the PDF takes precedence. This installed baseline does not yet satisfy the full competition architecture.

## Current status ? 8 November

The tested Gazebo baseline has completed three virtual deliveries and a return.
Native AirSim integration is active development. Read [PROJECT_LEDGER.md](PROJECT_LEDGER.md)
for the durable task record and [native setup and limitations](docs/NATIVE_AIRSIM.md).

- Custom Cosys-AirSim plugin compiled for Unreal 5.8.1; native physical flight
  and ground-confirmed landing verified with a 2.254 kg reference airframe.
- Native agents/controller/radio/station run together. The first complete run
  returned but delivered at false detections: zero independently valid rescues.
- Native timing about 182 ms p95 still exceeds the 150 ms requirement. GPU
  inference works; scene-specific models and timing fixes are under evaluation.
- Original Coastline remains the visual reference. Custom scene includes CC0
  scans and textured clothed people; it still needs visual refinement.
- 63 portable unit tests pass. Final native mission, fault campaign, blind
  evaluation, physical release and deployment package are not complete.

No readiness percentage is a substitute for these acceptance results.

## Project plan

Use [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) for the architecture and acceptance gates.
[AI_HANDOFF.md](docs/AI_HANDOFF.md) and `contracts/` define the boundary for any
alternative implementation your friend later supplies. We currently implement
all parts. [RESEARCH.md](docs/RESEARCH.md) records primary sources and open questions.

A separate WSL distro named `Dronathon` is being installed on D:; consult [WSL_SETUP.md](docs/WSL_SETUP.md) for its latest verified status. The ROS/Gazebo omission described in the original baseline section below is historical; the setup report takes precedence.

## Ready now

- Isolated Python 3.13 environment on D: with NumPy, SciPy, Matplotlib, OpenCV contrib (ArUco), pymavlink, MAVSDK, serial, YAML and pytest.
- Official ArduCopter 4.7.2 software-in-the-loop (SITL) executable on D:, running through existing Ubuntu 24.04 WSL2.
- Windows-to-WSL MAVLink heartbeat verified on localhost:5760. Vision marker generation/detection verified. Seven coverage planner tests passed; `pip check` passed.
- Offline environment and vision checks, an illustrative search planner, VS Code interpreter selection, and a full dependency lock file.

## Run from PowerShell

```powershell
cd D:\dronathon
powershell -NoProfile -ExecutionPolicy Bypass -File .\check.ps1
.\.venv\Scripts\python.exe scripts/plan_search.py --width 100 --height 80 --spacing 10
```

Run the simulator in one terminal (leave open; Ctrl+C stops it):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\dronathon\start-sitl.ps1
```

Read its heartbeat in another terminal:

```powershell
cd D:\dronathon
.\.venv\Scripts\python.exe scripts/telemetry.py
```

No activation is necessary when using the explicit Python path. ExecutionPolicy Bypass here applies only to that launched PowerShell process; it does not change your machine policy. Telemetry is read-only. The sweep planner exports JSON and PNG into `artifacts/`; it does not upload missions or avoid obstacles.

## Scope and storage

The Python environment and SITL tools take about 550 MiB. Downloads used no pip cache. About 15.8 GiB remained on D: after installation, before subsequent small logs/artifacts. C: contains your pre-existing Python/WSL installations; WSL can still grow its existing virtual disk on C:.

ROS, Gazebo, PX4, QGroundControl and PyTorch/YOLO are **not installed** by this setup. Public material did not establish the required platform. Choose the organizer's required stack when the cahier des charges arrives. The installed SITL has internal flight dynamics but no 3D world or camera imagery. ArUco verification is not survivor detection. MAVSDK was import-checked; its flight-control API was not exercised.

`node-modules-sizes.json` contains the inventory of about 5 GB of project dependencies found on D:. Automatic approval review blocked the deletion command with “blocked by policy”; **no node_modules were deleted**. Source code and lock files remain intact.

## Reproduce

Use an installed Python 3.13 to create `.venv`, then install `requirements.lock.txt` with `--no-cache-dir`. `requirements.in` lists direct dependencies. `scripts/install_sitl.sh` restores the two SITL files and verifies the recorded SHA256 hashes. This requires internet. Installed tools and smoke checks work offline.

```powershell
py -3.13 -m venv D:\dronathon\.venv
D:\dronathon\.venv\Scripts\python.exe -m pip install --no-cache-dir -r D:\dronathon\requirements.lock.txt
wsl -d Ubuntu -- bash /mnt/d/dronathon/scripts/install_sitl.sh
```

Do not use this simulation defaults file on a physical vehicle. Hardware configuration, camera calibration and flight behavior remain to be validated against the actual competition equipment and rules.
