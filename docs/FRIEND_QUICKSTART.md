# Run and review SKYFORGE

This is a working prototype with known gaps, not a finished competition entry.
Use `docs/official-requirements.md` and the supplied PDF for the challenge.

## Fast source/model review on Windows

```powershell
git clone https://github.com/drakedeveloper/dronathon.git D:\dronathon
cd D:\dronathon
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy opencv-python onnxruntime langgraph pytest jsonschema msgpack
.\.venv\Scripts\python.exe -m pytest tests -q
```

The repository is private; your GitHub account needs access. Python3.12 or3.13
works for the portable tests. ROS/Gazebo modules require the WSL environment below.
Trained models are included. Full training datasets and installed runtimes are
excluded. `models/README.md` explains the limited validation domain.

## Full simulation — Windows + WSL2 Ubuntu24.04

Keep the checkout at **D:\dronathon** for the existing launch scripts. A different
location requires adjusting `/mnt/d/dronathon` in scripts. Use a WSL2 Ubuntu24.04
distro called `Dronathon`, or replace `-d Dronathon` in the PowerShell launchers
with the name of your Ubuntu24.04 distro (`wsl -l -v`). Provision it as root:

```powershell
wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/provision_wsl.sh
wsl -d Dronathon -u root -- bash /mnt/d/dronathon/scripts/build_physics.sh
powershell -NoProfile -ExecutionPolicy Bypass -File .\check-wsl.ps1
```

The ROS2/Gazebo installation downloads several GB. The repository does NOT include
the author's WSL disk. Keys are generated locally under `/opt/skyforge/radio.key`;
never copy someone else's key into the repository.

Run each in its own PowerShell terminal:

```powershell
.\start-station.ps1
```

```powershell
.\start-mission.ps1
```

Open http://127.0.0.1:8766 . `start-mission.ps1 -Gui` adds the Gazebo viewer. Stop
the mission with Ctrl+C. Run only one mission at a time. On this laptop AMD D3D12
works and NVIDIA/WSL GLX crashes; on your machine set `$env:SKYFORGE_GPU='NVIDIA'`
before launching if appropriate. `scripts/run_software_mission.sh` is a slow
diagnostic fallback and does not satisfy the real-time requirement.

The X3 mesh and selected CC0 scene assets are bundled. Scene generation is local.
Full source paths: `skyforge/`, `station/`, `sim/plugins/`, `tests/`, `contracts/`.

## Current evidence and open work

Latest measured mission6c012085: two virtual deliveries, autonomous return with
2.93Wh, no hazard entries/static collisions in the geometric checker. Dynamic
contacts are not certified. A prior run delivered3 supplies but exhausted energy
and emergency landed short of base; the planner budget was corrected afterward.

Main unresolved requirements: repeated full mission success, all3casualties with
safe return under the chosen battery, weapon recall, new unseen-scene validation,
capture-to-actuation150ms p95, actual supply release and independent landing
evaluation, fault/replay demo, and more realistic art. JSON radio integrity and
real-socket outage/replay tests exist. The radio is loopback and not encrypted.

Primary512/secondary512 is the active neural path. 384variants are experimental:
they run faster, but the secondary model loses casualties in development
validation. They are not selected by default. No LLM is called in the control loop.

## Optional Unreal visual environment

```powershell
.\setup-airsim.ps1 -Extract
.\start-airsim.ps1
.\.venv\Scripts\python.exe -m scripts.inspect_airsim
```

This downloads the official~884MiB Windows Coastline scene (~2.4GiB extracted).
It is excluded from git. Native API/camera and bounded velocity climb/descent
work, but the rescue mission is not integrated into AirSim. Do not run both
renderers during timing tests. The packaged takeoff API timed out in local
testing; the smoke test uses explicit velocity commands. Full Unreal Editor is
not required for this binary.
