# SKYFORGE — project contract and durable work ledger

Read this first when resuming. User requests completion of the whole Dronathon
project, not only plans. Preserve all objectives when receiving steering messages.
Keep working through implementation, verification, documentation and GitHub
updates; do not end work merely after answering a cleanup/status question.

## Latest verified checkpoint: 8 November, native AirSim

### ACTIVE DEADLINE / latest steering (supersedes older checkpoints)

User said TWO HOURS LEFT at about03:17 UTC /04:17 Tunis on8 November. Treat
05:17 UTC /06:17 Tunis as the working cutoff. Priority: stable PDF-compliant
mission, security and packaging. Additional creative ideas/visual changes are
deferred. User's friend now owns the three real-image datasets; stop duplicating
that training. Archives downloaded locally and label formats documented in
docs/DATASET_TEAM_HANDOFF.md. No Roboflow credentials were requested/stored.

Latest published GitHub is1d3e5a9. New changes after that are not yet pushed.

GPU native V3 training finished (artifacts/native_v3_models). It used700/200/100
camera positions for70/20/10 split. Found some initial masks blank directly after
teleport, so old training/val labels were incomplete. Re-captured200development
views with3paused captures/pose, retained most complete paired RGB/mask. Corrected
val in data/native-v3-verified: mine45/45TP0FP; weapon37TP4FN0FP; waste89TP2FN0FP;
casualty49TP21FN2FP; hostile43TP6FN1FP atconf.35. Not blind final test or real-world
metrics. Final100test views remain uninspected/unscored. No new model training
currently running. Native training Python is C:/Users/Hamza Trabelsi/AppData/Local/
SKYFORGE/venv-training (torch2.7.1+cu128); inference separatevenv-native CUDA13.

Native run8d5d59c8:1correct virtual delivery+safe return2.75Wh. Run61600509 showed
2events but aborted at105s because scenario RPC timedout; parent killed children
and landed locally, and in-memory trace was lost. DO NOT count it as completed
mission. Run9a8edd16:1correct delivery+return3.22Wh, got stuck excluding a casualty
from one low-confidence hostile label. Added temporal person-class voting, lowered
consistent detector acceptance to.35, empty-ground/depth-presence verification,
secondary zoom-out atlowaltitude, and finite camera-worker failure recovery.
New changes need next mission. Native trace now streams JSONL for crash evidence.
Scenario driver now retries idempotent wind/prop RPC timeouts instead of aborting.

Live fault campaign on9a8edd16 proved autonomy through20soutage, event buffering
and replay, state CRC hold and duplicate-command rejection. Packet bitflip
registered auth rejection rather thanCRC (malformedJSON); campaignreportedfalse
forCRC-specific condition. Injector now flips a revision digit to preserve JSON
and explicitly hit CRC. Must repeat against next native mission. Full radio
journal/ACK restart recovery implemented and socket-tested. No encryption claim.

Native p95 stillFAILS, about300-400ms under concurrent cook/link/render load.
Do not hide this. Camera now reuses independently sampled reflex odometry rather
than two extra RPC calls. Need idle-laptop/packaged timing measurement. New tests
include pose interpolation, malformed signed controls/expiryclock, scale bbox,
radio sender restart/corruption, failed delivery audit and HTTP report isolation.
Last full Windows suite78passed before newest scenario/threshold changes.

Game C++ binary build succeeded87actions. First packaged cook omitted dynamic
BP_FlyingPawn; launch crashed. Added explicit /AirSim/Blueprints and /AirSim/Weather
cook directories (not allSUV/car assets). Second cook failed after simultaneous
mesh-authoring started a Zen server with another DDC path. ALL Unreal jobs must
run sequentially with UE-LocalDataCachePath set to LOCALAPPDATA/SKYFORGE/UnrealCache.
Use scripts/optimize_unreal_meshes.ps1, not bareUnrealEditorCmd. Native simulator
is currently CLOSED after grounded mission. No renderer is visible right now.

CURRENT RUNNING JOB: exec99177, UnrealEditor-Cmd PID158000, optimizing distance
LODs for4large coastal scans. Script initiallyneeded explicitload_module
StaticMeshEditor; nowworking on coastal_cliff_02. Logartifacts/unreal-lods.log.
CPUprogress~110s at03:54UTC. Wait/fix errors, then package -SkipBuild (successful
Gamebinaryalreadyexists), then test -Packaged launch, then full native mission
with latesttracker. Pipeline should improve when millions of distant triangles
useLODs. No need for more sceneryartwork.

Cache: D:/runtime/unreal/SKYFORGE/Intermediate was safely moved to
C:/Users/Hamza Trabelsi/AppData/Local/SKYFORGE/UnrealBuildCache/ProjectIntermediate,
with D: junction, freeing2.48GiB. C~34GiBfree D~4.8GiB atlastcheck. Docker still
stopped/deletedVHD. Dockerfile/CONTAINER_RUN.md added as UNBUILT recipe; WSLROS2
deployment is previouslytested, container is not. Don't restartDocker merely
to claim packagingdone. Real airframe plan and SECURITY.md added with limits.

Next: finishLODs -> sequentialpackageSkipBuild -> launch/flight -> full3delivery
audit -> livefaults andtiming -> frozen candidate+blindtest -> GitHub/release docs.
Existing Gazebo three-delivery baseline remains fallback, but sharedtracking
changes need regression mission. Keep reports honest; source score not victory.

- Custom Cosys-AirSim plugin source build succeeded (85 actions). Original
  procedural coastal Unreal level authored and running visibly, API 41461.
- Corrected Unreal Python Rotator positional argument mismatch: ground proxy
  had been vertical. Explicit pitch/yaw/roll keywords and BlockAll collision
  profile now used. Native drone rests on ground; lighting exposure corrected.
- Physical flight demo completed: takeoff to 8.08 m, forward/sideways travel,
  return and ground-confirmed disarm; no new collision timestamps in trace.
  Evidence: validation/native-visible-flight.json. This is not rescue success.
- Native GPU environment installed on C, CUDA ONNX inference verified. Existing
  20 development images: two-model p95 76.35 ms including startup, same counts
  as CPU. No native-scene or real-image accuracy claim. OpenCV pinned 4.13.0.92
  because new OpenCV 5 package omitted HOG needed by the shared planner import.
- Native backend negotiates classic/Cosys read-only image RPC signatures. Warm
  actual RGB+depth camera samples measured about 46-83 ms before inference.
- Native station, weather driver, independent reflex and mission launcher added.
  Station is http://127.0.0.1:8768. Exactly two existing LangGraph agents retained.
- First integrated native run took off and detected a casualty, then aborted
  after Windows file replacement sharing denial. Publication now retries/skips
  blocked live updates instead of killing flight. Drone manually returned and
  landed. Windows UDP startup ICMP reset handled. Automatic landing recovery
  added to launcher. Subsequent integrated test running; acceptance unproven.
- End-to-end timing first run about 240 ms p95: FAILS 150 ms requirement. Tightened
  camera/main/reflex publication intervals; must measure subsequent run.
- 60 unit tests passed in both original and new GPU Python environments.
- Visible simulation remains open while working. Native scene is a lightweight
  prototype using original geometry/CC0 scans, not COD quality or a copied map.
- Latest source changes still uncommitted; latest published remains 735696e.

Next: finish native integrated mission and independent truth evaluation, improve
scene-domain detection/false positives, timing, fault campaign, final deployable
package and docs/push. Keep original full backlog below; no completion claim.

### Visual direction and failed native rescue audit

User explicitly rejected the bare procedural scene and prefers original AirSim
Coastline realism. Restored classic Coastline spectator preview on 41451 and
kept it visible while authoring improved native scene headlessly. Preview uses
external physics/teleport and is not flight evidence. Do not replace it with the
flat prototype or claim that prototype meets the requested visual standard.

Native mission 6049db46 completed three virtual events and safe return at 7.23 Wh,
but independent evaluator found ZERO valid rescues (errors 9.13, 4.58, 3.12 m).
This run FAILED due to phantom casualty tracks. Measured pipeline about 182 ms
p95 also FAILS. `scripts/evaluate_native_mission.py` records truth-only evaluation
outside the agent runtime. Added visible-empty-ground track invalidation and
fresh-sighting delivery gate, 62 tests pass; new mission verification pending.

Core native launcher now cleans up Windows child process trees and attempts
ground-verified landing on agent failure. GPU two-model warm inference about
27-30 ms live; camera/main/controller intervals tightened, next run MaxFPS 60.

Downloaded 144.4 MiB of checksummed CC0 Poly Haven assets: coastal_cliff_02,
coast_line_02, coast_rocks_03, island_tree_02 and three 2K terrain material sets.
Downloaded textured clothed MakeHuman-derived human (7,679 triangles) from pinned
OpenRCsimulator commit 187182d3cf9f4c53621a5e56320d9351a47248f0, provenance and
license files local, reproducible scripts/prepare_people_assets.py. Original
asset licence CC0; repository code is not imported. All big downloaded content
ignored by Git; reproducible downloader and conversion scripts must be shipped.

Visual V2: 110,000-triangle sculpted island with flat mission plateau, ridgeline,
scanned coastal cliffs/shore, real island trees, textured clothed people in
standing/prone poses, animated water shader, inert 3D mine casing details.
Scene authoring currently runs headlessly; not yet visually inspected. Keep
custom physics profile and coordinate calibration; do not fake mission evidence.
Retrain on the final scene after visual acceptance, not on obsolete terrain.

### Current continuation checkpoint (8 November, about 03:40 Tunis)

- Visual V2 authored successfully; ground camera and aerial overview inspected.
  Clothed people look much better. Terrain still looks repetitive/bare and DOES
  NOT yet match original Coastline realism. User explicitly wants the original
  scene quality. Do not claim the visual goal is finished. Coastline scenic
  preview restored again; it is visible on 41451. Native offscreen process
  13840 was stopped after offline captures to release memory.
- Captured 250 actual native RGB/instance-mask pairs: 180 train, 40 development
  val, 30 reserved test, data/native/manifest.json. Verified a training person's
  visible segmentation box against the image. Test images not inspected.
  Current split is 72/16/12, not the PDF's 70/20/10; fix a subsequent training
  version before final acceptance. Never silently relabel already-trained
  images into validation for a candidate that has seen them.
- CPU fine-tuning both networks runs in WSL PID313, exec62529. Log:
  artifacts/native-training.log. About epoch13/25 PRIMARY at checkpoint. Output
  is artifacts/native_models, leaving models/ baseline unchanged. Run tag
  -native-v2. It starts from the Gazebo model checkpoints. Secondary follows.
- Native GPU training environment setup runs exec36963, log
  artifacts/native-training-setup.log. C:/Users/Hamza Trabelsi/AppData/Local/
  SKYFORGE/venv-training. Official torch2.7.1+cu128 wheel is 3.27GB; CUDA12.8
  isolated from CUDA13 ONNX environment. Do not start competing duplicate
  training jobs; stop/finish CPU job before actually switching to GPU.
- 64 Windows unit tests pass, including denied file replacement, independent
  false-delivery audit and visible-ground negative evidence. Linux full suite
  is running exec47283. README/native guide/notices now disclose failed native
  rescues and >150ms pipeline. Stale Gazebo observer image is replaced with an
  explicit native-window placeholder when native mission starts.
- Added scripts/capture_native_dataset.py (offline ONLY, pause/teleport + masks),
  scripts/prepare_people_assets.py, cinematic downloader, shader authoring,
  native setup/run/evaluation scripts. Dataset truth stays out of runtime.
- Training script supports --dataset, --tag, --finetune, --output, --batch;
  evaluator supports --models, --dataset, --device and --split. Keep val tuning
  separate from final held-out evaluation and record final model hashes.
- Native station 8768 is stopped after completed run. New native run must launch
  the visible custom simulator on41461 first, then scripts.run_native_mission
  with --models artifacts/native_models only after both candidates are ready.
- Remaining: finish native scene realism, model/mission validation, timing,
  meaningful outage/bitflip campaign, true payload/contact semantics, final
  package/ROS2 deployment/pitch and real hardware calibration limitations.

Next GitHub milestone should include all new source, ledger, native setup guide,
asset manifests and failed/successful evidence summaries. Big downloaded assets,
generated Unreal projects, training data/runs and secrets stay ignored. Friend
can reproduce asset downloads; do not commit the 150MB tree OBJ.

## User decisions and scope

- ENSIT Dronathon 3.0, Mission SKYFORGE. Official specification: `dronathon.pdf`;
  requirements extracted in `docs/official-requirements.md`.
- We own the complete project: AI, both deterministic LangGraph agents,
  perception, physics, control, simulation, communication, security, server,
  dashboard, documentation, demo and packaging. A friend may supply alternatives
  later; compare against the same tests rather than replacing blindly.
- Laptop only: Ryzen 5 7535HS, 16 GB RAM, RTX 2050 4 GB plus AMD integrated GPU.
  The home RTX 5060 computer will not be used.
- Work predominantly on D:. GitHub is private:
  https://github.com/drakedeveloper/dronathon . Push tested changes to main.
  Current published commit at ledger creation: `735696e`.
- Visual target: the user's Call of Duty reference, with detailed weathered
  buildings, layered debris, believable people, lighting and atmosphere.
  Build an original free coastal rescue environment; do not assume a game map
  or commercial Fab asset is available. Army Base Island listing was inaccessible;
  license, price and compatibility remain unverified. No such asset installed.
- AirSim/Unreal is the requested realistic presentation direction. Gazebo is the
  integrated autonomous regression backend today. Keep this distinction explicit.
- SITL is optional: integrate if it improves reliable firmware realism without
  diverting from completion. User mentioning SITL is not an instruction to abandon
  the broader project. ArduPilot binary is already installed but not integrated.
- User delegates airframe choice: cost-conscious, documented research/rescue
  quadrotor. Chosen direction is X500-class, with a medical payload. No actual
  team hardware specifications were supplied. A documented reference is not a
  measured match to an unknown physical drone.
- Research primary papers and useful GitHub projects. Implement ideas with
  measured evidence; don't borrow a paper's performance numbers as our results.

## Mandatory architecture and mission

Humanitarian autonomous coastal exploration; detect litter, passive mine/weapon
hazards and injured people; avoid hostile units/zones and obstacles; urgency first,
travel time second; energy-feasible medical delivery and safe autonomous return.
Two agents only: PerceptionAgent and PlannerAgent using shared DroneState.
No LLM calls in the real-time loop. Reflex <50 ms; deliberation <=100 ms;
capture-to-actuation <=150 ms p95. Compact versioned/sequenced JSON <1 KB;
declared event ring and replay/resync. Survive radio outages, updated goals,
weather and obstacles. Technical documentation, code, deployable 3D scene,
unattended demo and pitch. Pi/board deployment is optional bonus. No weapons
or hazardous payloads; hostile units are avoidance zones.

The PDF says the jury supplies primary detector/world/station, but the user
received only these datasets and says implementation is free; implement what is
needed instead of waiting:

- https://www.kaggle.com/datasets/ugorjiir/gun-detection
- https://universe.roboflow.com/mine-dyzns/detection-miwbi/browse
- https://zenodo.org/records/21965497

## Full creative backlog

All 25 suggestions are retained with honest implementation/validation status in
`docs/INNOVATION_MATRIX.md`. User authorizes useful implementations, not empty
feature claims. Preserve: living tactical map; active second-chance perception;
energy-aware routes; radio-shadow memory; future collision prediction;
explainable brain; safe medical delivery; weather adaptation; fault recovery;
uncertainty/frontier exploration; independent safety shield; trajectory rollouts;
time-varying declared urgency; doubt/caution zones; safe corridors; bandwidth
budget; black box and interactive replay; command firewall; chaos tests;
deadline guardian; camera footprint/resolution; persistent person IDs;
delivery bubble/alternate sites; observed-area report; randomized scenario tests.

Other user ideas: toroidal/quiet propellers and airframe shape, protective/medical
pod geometry, physics edge cases, bit flips, IoT and general security. Do not
claim silence or efficiency from a cosmetic rotor change. Quantify mass, inertia,
drag, thrust headroom, camera clearance and collision footprint of any variation.

## Current verified evidence

- D-backed WSL Ubuntu 24.04, ROS2 Jazzy, Gazebo Harmonic. Native Windows AirSim
  Coastline downloaded/extracted. Unreal Engine 5.8.1 and MSVC build tools exist.
- Gazebo uses AMD D3D12 on this laptop; NVIDIA WSL GLX crashed. Native AirSim
  uses RTX 2050. Keep one 3D renderer active during performance tests.
- Deterministic two-node LangGraph, learned two-detector ONNX inference, depth
  localization, geometric A*, triage, conservative energy budget, separate
  classical reflex, radio CRC/HMAC/replay, receiver checkpoint persistence and
  local ground station are implemented.
- 53 tests pass on Windows and Linux at latest full run. Tests do not establish
  full competition compliance. Timing still misses the end-to-end requirement.
- Missions c5da6412 and 55b6ec39 delivered all 3 virtual supplies and returned
  with 5.48/5.80 Wh from 15 Wh. Geometric evaluation: zero hazard entries/static
  collision segments. Moving contacts are not certified. Source summaries in
  `validation/`. These are declared-scenario demonstrations, not unseen-world
  robustness proof.
- Mission 701e18bd added shield, evidence explanations and depth-checked observed
  ground map. Latest live snapshot: 3 virtual deliveries, base landing, 5.87 Wh;
  76.2% of the declared flat-ground grid observed with depth/resolution checks.
  This is not semantic completeness or a safe-area certificate.
- AirSim visible physics flight: ~8 m climb, forward/sideways motion, return and
  ground-confirmed descent, no reported collision. `-Scenic` is a separate
  external-physics teleport preview, not flight validation. Full rescue AI is
  not yet integrated into AirSim.
- Physical drop benchmark: 18 Gazebo cases vs RK4 under the same drag law,
  numerical consistency only. Mission deliveries remain virtual.
- Vision trained on 70 synthetic images, development validation on 20. Current
  primary weapon recall is weak; no fresh final holdout completed. Seed33 was
  inspected, so is not blind. Input384 reduced speed cost but hurt casualty
  detection; do not select it globally. Mixed-resolution code is experimental.
- Radio socket outage/replay/corruption and station restart tests pass. One live
  outage proved autonomy/reconnection but no buffered events occurred; a later
  live test aborted on a now-fixed snapshot race. Complete live fault campaign
  still needed. HMAC is not encryption; CRC is not ECC hardware protection.

## Hardware realism requirements before final acceptance

Create a source-backed machine-readable airframe profile and mass budget:
frame, motors, props, flight controller, sensors, battery, medical payload and
mounts. Compute total mass, CG, inertia/parallel-axis contributions, rotor
locations/spin order, thrust/torque constants, response lag, drag, battery
voltage/capacity/usable energy and sensor noise. Enforce consistency among the
simulator, planner and documentation. Keep assumed and measured values distinct.

PX4's X500 source was retrieved under `artifacts/hardware-research/`: main body
mass2.0 kg, diagonal inertia approx[0.02167,0.02167,0.04] kg m², each rotor
mass0.01608 kg. Motor coefficient8.54858e-6 and time constants0.0125/0.025 s.
These are published simulator parameters, not measured airframe truth. Original
SKYFORGE prototype used1.52 kg; do not claim a hardware match before reconciling.
Primary source: https://github.com/PX4/PX4-gazebo-models/tree/main/models/x500_base

Do not silently enlarge the battery to hide planning failures. The current
15 Wh scenario budget is separate from any future full hardware battery capacity.
Validate hover RPM/thrust headroom, tracking/braking, wind response, energy
consistency, payload effects and delivery. Hardware matching ultimately needs
measurements; datasheets alone cannot prove it.

## Storage and operational constraints

User deleted Docker's data disk after explicit authorization: verified C60.55 GB
free / D11.05 GB, Docker data VHDX absent. Do not restart Docker and recreate its
disk unless necessary. Docker app remains installed. Other projects/games intact.
Previous deletion actions were blocked by automatic approval review; don't retry
those actions through another tool. The user ran the supplied deletion command.

WSL shutdown crashes generated repeated multi-GB Windows dumps despite ulimit.
Temporary shared-WSL kernel core_pattern is now `|/bin/false`, with original saved
at `/opt/skyforge/artifacts/core-pattern.original`. Script:
`scripts/wsl_core_capture.sh`, `--restore` to restore. This affects all WSL guests
until restored/restarted; no files were deleted by this setting.

Ground station http://127.0.0.1:8766, radio8765. Keys remain outside git. Runtime,
datasets, crashes, caches and installed simulator binaries are excluded from git.
`start-mission.ps1 -Gui` now leaves Gazebo open after mission completion;
close viewer / Ctrl+C to stop its owned simulator/controller. `follow_drone.sh`
sets /gui/move_to and /gui/follow to x3. Avoid duplicate mission partitions.

## Active work at this checkpoint

### Latest implementation checkpoint (8 November, about02:20–02:25 Tunis)

Unreal plugin archive downloaded, upstream SHA256 verified, expanded3.30GiB.
`prepare_unreal_project.py` created the native project at
`runtime/unreal/SKYFORGE/SKYFORGE.uproject`. Source compilation is running in
exec31766 (older exec89234 was interrupted when switching off UBA detouring).
Latest observed progress47/85 actions; errors not observed, upstream warnings
exist. MSVC14.44.35207, SDK22621, one compiler action at a time. Build script
`scripts/build_unreal.ps1`, supports optional-Rebuild. UE5.8always reports UBA
executor but-NoUBA disables detouring, confirmed `[NoUba]` in action output.
Compiler PCH2.5GB and intermediates consume space; latest D~4.5GiB,C~50GiB.
Do not delete build outputs or restart Docker. Read build log before restarting.

Reference profile generated: `configs/airframes/x500-research.json`, pinned PX4
commit and input hashes. Loaded mass2.254307692kg (2kg aggregate body,4rotors,
150g kits,40g mount); CGz=-9.2mm; diagonal inertia~[.02732,.02776,.04504]kgm²;
max thrust34.194N, T/W1.547, hover~7678RPM. Prop diameter0.28m and4S5Ah battery
are DESIGN assumptions, not verified purchased parts.15Wh mission allowance is
separate from74Wh electrical capacity. Do not claim measured hardware matching.
`apply_unreal_airframe.py` generated custom AirLib header and patched our local
SimpleFlight factory. Rotor coefficients converted to AirSim nondimensional
C_T/C_P. Main profile limits are recorded in `runtime/unreal/SKYFORGE/airframe-build.json`.
`Vehicle.from_reference()` and planner vehicle injection are implemented.

Original geometry generated by `generate_unreal_geometry.py` into ignored runtime:
island terrain6944triangles, rescue-person proxy4352, arched roof448, palm920.
`build_unreal_scene.py` authors the full free original level via Unreal Python;
it has only passed syntax checking, NOT been executed inside Unreal yet. It
imports CC0 scans and generated meshes, creates harbour/hangars/ruin/tower/tents,
places role props and saves annotation/evaluator manifest. Must run/fix/inspect
after native source build completes. Change PlayerStart location fromz30 toz0
before execution so the native ground coordinate origin matches the scenario.

`configs/scenes/coastal-rescue.json` separates mission inputs from evaluator
truth. AI must consume ONLY mission subsection. Native settings are in
`configs/airsim-native-settings.json`, API41461, camera512x384/depth256x192,
IMU/GPS/baro/mag/lidar explicitly enabled. Classic Coastline uses41451.

Native `skyforge/airsim_backend.py` has no Gazebo imports: separate camera,
navigation and command RPC connections; explicit NED->ENU and FRD->FLU;
bounded velocity commands, aligned RGB/depth and odometry interpolation. Focused
tests pass. Read-only sensor probe succeeded against running classic Coastline:
640x480 RGB/depth, pENU[0,0,90], quaternionENU yaw90deg,269ms first probe.
This is NOT mission integration. Full native controller/runtime/server path
still needs implementation. Existing runtime/controller import Gazebo messages.

User asked to keep AirSim visible: classic Coastline scenic mode is currently
open on41451 and positioned at90m by `airsim_scenic.py` (exec49996finished).
It is EXTERNAL-PHYSICS spectator mode and must never be used as flight evidence.
Close it when ready to test native project to avoid two renderers on4GB GPU.
Gazebo mission701e18bd finished with3virtual deliveries, base landing5.87Wh,
76.2% depth-checked ground coverage. Gazebo launcher/GUI were stopped by SIGINT
to PID4800 before native compilation. WSL station may still run PID1164.

`PROJECT_LEDGER.md` is explicitly requested by user as the durable record for
all scope, ideas and work. Update it at milestones; include it in next GitHub
push. Latest published GitHub remains735696e; newer airframe/native scene work
is still uncommitted. Full suite53passed before these changes; new focused
airframe/backend/physics/planning21tests passed. Need full tests after integration.

### Original next-step list (superseded details above)

1. Finish free custom Unreal/AirSim environment and full mission integration,
   preserving tested Gazebo baseline. Cosys-AirSim3.5.0 Windows plugin download
   runs in exec71905 via `scripts/setup_unreal_plugin.ps1`. Upstream SHA256 pinned.
   MUST create `scripts/prepare_unreal_project.py` before download completes.
   Engine is5.8.1 while released plugin binary is5.8.2: rebuild source with local
   MSVC/SDK rather than faking binary compatibility. Installed engine D:\Epic
   Games\UE_5.8. Compiler instances include VS2022Community and BuildTools.
2. Implement source-backed hardware profile and validate both physics backends.
3. Complete creative backlog items with tests, then integrate one at a time.
4. Fresh scene-domain data/holdout, improve primary weapon detection, validate
   full timing under final renderer and AI load.
5. Repeat mission/fault/scenario campaign; independent drop/contact/coverage
   evaluation, final deployable package and pitch/demo documentation.
6. Push tested milestones to GitHub and update this ledger and innovation matrix.

Do not declare the project complete while these acceptance gaps remain. Do not
stop work merely because the user leaves; continue authorized implementation.
