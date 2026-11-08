# Visual target and simulator decision

The user's Black Ops III reference is the visual target: convincing scale,
weathered architecture, layered rubble, atmosphere, articulated people and
cinematic lighting. The current Gazebo map is below that target. A fresh render
exists in `artifacts/coast-preview.jpg`; it is a technical environment preview.

## Immediate Unreal route

Use Microsoft's official **Windows v1.8.1 AirSim Coastline** packaged scene first.
The verified release asset is 926,675,941 bytes (~884 MiB). This avoids installing
the full Unreal editor. `setup-airsim.ps1 -Extract` resumes the download, checks
length, records a local SHA256, checks archive CRCs and extracts only under D:.
The upstream release has no signed checksum; the local hash is provenance, not
proof of upstream authenticity. Source: https://github.com/microsoft/AirSim/releases/tag/v1.8.1-windows

`start-airsim.ps1` uses a project-specific settings file and loopback API, with
720p laptop / 1080p home profiles. `scripts/inspect_airsim.py` is a read-only
connection/image probe. It does not arm or fly the drone. The custom synchronous
RPC client avoids the old Python package's Tornado dependency; it requires a
real simulator smoke test before relying on it.

Coastline is a ready-made visual starting point, not a finished rescue map.
Do not claim the competition mission works in AirSim until camera geometry,
physics, collisions, sensor timing, navigation and delivery are integrated and
tested there. Do not assume packaged environments contain editable project
sources or arbitrary casualty character assets.

## Custom cinematic environment

Cosys-AirSim v3.5.0 has a precompiled plugin for **Unreal 5.8.2**, with exact
toolchain requirements in its release. Its ready-to-run demo is Blocks, so
downloading that demo does not meet this visual target. A custom UE project
needs editor storage, licensed environment/character assets, collision setup,
camera calibration and packaging time. Inspect free space on the RTX 5060 PC
before choosing this heavier route. Source:
https://github.com/Cosys-Lab/Cosys-AirSim/releases/tag/5.8-v3.5.0

Build an original damaged coastal settlement with a rescue corridor, harbour,
distress beacons and weather. Smoke should affect optical observability and
trigger sensor-confidence changes; cosmetic particles alone are not a physics
model. Keep fire and combat as environmental references; the mission is
humanitarian reconnaissance, avoidance and supply delivery.

## Local test backend

Gazebo remains the currently integrated physics backend. NVIDIA D3D12 GLX
context creation crashed on this laptop. AMD D3D12 successfully rendered an
actual scene; the project shell now defaults to AMD, with `SKYFORGE_GPU` override.
Software rendering is a diagnostic fallback and missed the timing requirement.
No global GPU driver or WSL configuration was changed.

The small Poly Haven CC0 scan/texture pack has a per-file source/checksum
manifest under `sim/assets/manifest.json`. Its visuals are separate from coarse
collision geometry. The original detector training images were retained;
additional richer scenes require separate training/validation data.
