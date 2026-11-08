# Native AirSim integration

Read PROJECT_LEDGER.md for the latest measured status. This integration is under
development. The original Coastline preview has richer art; the original scene
is a packaged executable, not an editable project supplied with the release.
The custom Unreal scene is separate and still needs visual improvement.

## Verified and outstanding

- Custom Cosys-AirSim 3.5.0 built from source against installed Unreal 5.8.1.
- Physical takeoff, travel, return and ground-confirmed landing verified.
- Reference profile: 2.254 kg X500-class simulator airframe with payload.
  Mass/inertia/rotor coefficients share one JSON. This is not measured hardware.
- Native camera/depth, lidar, independent reflex, two deterministic agents,
  authenticated radio and local station run together.
- First completed native mission returned safely but its three virtual
  deliveries were ALL invalid in independent location checks. This is a failed
  rescue run. Negative-evidence tracking and fresh-sighting gates were added.
- First native pipeline p95 was about 182 ms: fails the required 150 ms.
- Native-scene models are being trained separately; do not promote them without
  development evaluation and an actual mission/independent delivery audit.
- Final physical release, fault campaign, native packaging and hardware
  calibration are outstanding. SITL is not the active flight controller.

## Local commands

These assume the installed Unreal engine, Visual Studio compiler and original
Python environment. Initial plugin expansion/build requires substantial free
space. Downloaded assets/generated Unreal content are excluded from Git.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_unreal_plugin.ps1
.\.venv\Scripts\python.exe -m scripts.create_reference_airframe
.\.venv\Scripts\python.exe -m scripts.apply_unreal_airframe
powershell -ExecutionPolicy Bypass -File scripts/build_unreal.ps1
.\.venv\Scripts\python.exe -m scripts.fetch_cinematic_assets
.\.venv\Scripts\python.exe -m scripts.prepare_people_assets
.\.venv\Scripts\python.exe -m scripts.generate_unreal_geometry
.\.venv\Scripts\python.exe -c "from pathlib import Path; from scripts.convert_scene_assets import convert; [convert(Path('sim/assets')/n/(n+'.gltf')) for n in ('coastal_cliff_02','coast_line_02','coast_rocks_03','island_tree_02')]"
powershell -ExecutionPolicy Bypass -File scripts/author_unreal_scene.ps1
powershell -ExecutionPolicy Bypass -File scripts/setup_native_runtime.ps1
powershell -ExecutionPolicy Bypass -File scripts/start_native_airsim.ps1
& "$env:LOCALAPPDATA\SKYFORGE\venv-native\Scripts\python.exe" -m scripts.run_native_mission --device cuda
```

Station: http://127.0.0.1:8768. Simulator API: loopback 41461. Classic Coastline
uses 41451; its spectator mode has external physics and is never mission proof.
The native launcher refuses that mode. Do not compare timing while two
renderers or a training job are competing for the laptop.

Offline dataset generation teleports a paused simulator and reads instance
annotations. It must never run concurrently with flight agents. The runtime
reads only the mission subsection of the scenario, never entity annotations.

Audit a completed native run with:

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_native_mission artifacts/native_missions/MISSION_ID
```

This audits virtual delivery geometry; it does not establish physical package
contact or a clinically correct triage decision.
