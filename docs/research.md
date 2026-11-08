# Research log and decision evidence

Checked 7 November 2026. Only primary technical sources are used for recommendations: project maintainers, official documentation, original research and dataset owner metadata. Performance numbers, safety guarantees and installation success are not inferred from documentation. `PROJECT_PLAN.md` contains our proposed engineering design; `AI_HANDOFF.md` assigns all AI to the human teammate.

## Requirements and interpretation

`../dronathon.pdf` is the authoritative written source. It specifies two deterministic LangGraph agents, a 3D humanitarian mission, low-latency control/decisions, resilient compact JSON, dynamic energy-based return, a secondary detector trained on simulator data, and weighted evaluation. The organizer's user-reported clarification gives implementation freedom and only dataset URLs. It does not supply model weights, a world or a station. Build these provisionally and retain adapter boundaries; document the written/verbal discrepancy.

### R1. Platform compatibility and installation

- [Gazebo-maintained ROS compatibility table](https://github.com/gazebosim/docs/blob/master/common/ros_installation.md)
- [Gazebo Harmonic entry point](https://gazebosim.org/docs/harmonic/)
- [ROS Jazzy installation source](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Installation/Ubuntu-Install-Debs.rst)
- [Official ros_gz bridge source](https://raw.githubusercontent.com/gazebosim/ros_gz/jazzy/ros_gz_bridge/README.md)

Evidence: Ubuntu 24.04, Jazzy and Harmonic form a supported combination; binary ROS-base and ros_gz packages are available. The bridge supports the principal image, pose, odometry, clock and velocity-message families we need. Use explicit bridge directions to avoid command feedback loops. Native ROS docs pages sometimes returned anti-bot errors; the maintainers' raw documentation sources were readable instead.

Decision: binary installation and narrow dependencies. Do not mix Humble instructions with Jazzy paths. In particular, the ArduPilot ROS/Gazebo walkthrough below uses Humble in its commands despite Harmonic support; it should not be pasted unchanged into our Jazzy system.

### R2. Physical multicopter control versus a separate autopilot

- [Gazebo Sim 8 MulticopterVelocityControl](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1MulticopterVelocityControl.html)
- [Maintained velocity-control world example, gz-sim8](https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8/examples/worlds/multicopter_velocity_control.sdf)
- [ArduPilot ROS2/Gazebo integration guide](https://ardupilot.org/dev/docs/ros2-gazebo.html)
- [Official ArduPilot Gazebo plugin](https://github.com/ArduPilot/ardupilot_gazebo/blob/main/README.md)

Gazebo's velocity controller plus rotor models offers a smaller integration surface for our simulated mission. Its state-estimation assumptions must be disclosed. The separate ArduPilot route is legitimate but introduces additional plugin/transport/version work. Our prior SITL heartbeat success does not establish camera/world integration. Use the simpler physical backend first, then benchmark and verify control behavior rather than claiming it is inherently fastest.

### R3. LangGraph implementation

- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)

LangGraph can execute ordinary functions over shared state; language-model calls are not necessary. Compile once and use a bounded two-node per-cycle workflow. Our proposed independent flight loop, bounded state, failure handling and snapshot revision checks are design choices to satisfy the brief, not automatic guarantees provided by the library.

### R4. Synthetic camera data and label generation

- [Gazebo Sensors 8 bounding-box camera](https://gazebosim.org/api/sensors/8/boundingbox_camera.html)
- [Gazebo Sensors 8 segmentation camera](https://gazebosim.org/api/sensors/8/segmentationcamera_igngazebo.html)
- [Gazebo sensor models](https://gazebosim.org/libs/sensors/)
- [Tobin et al., original domain-randomization paper](https://arxiv.org/abs/1703.06907)

Simulator annotation sensors can support image-label generation. Availability of labels does not make an inference model trained or evaluated. Use label channels only in data/evaluation mode; remove them from mission AI. Randomized rendering is a useful motivation for varying training scenes, but that paper's task/results do not establish performance for aerial rescue or our models. Hold out entire layout/scene seeds and evaluate rendered mission views separately from photographic datasets.

### R5. Wind, frames and runtime timing

- [Gazebo WindEffects](https://gazebosim.org/api/sim/8/classgz_1_1sim_1_1systems_1_1WindEffects.html)
- [ROS REP-103 source: SI units and frame conventions](https://raw.githubusercontent.com/ros-infrastructure/rep/master/rep-0103.rst)
- [ROS real-time programming guidance](https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/Tutorials/Demos/Real-Time-Programming.rst)

WindEffects supplies a simple disturbance model. REP-103 defines body/world/optical conventions used by our contract. ROS real-time guidance identifies blocking and unpredictable work as timing hazards. Ordinary Python/WSL deployment does not by itself provide hard deadline guarantees. Our control separation and latency budgets require measurement under full load; low graph compute time alone is not capture-to-command compliance.

### R6. Small detector and deployment research

- [Official YOLO11 model documentation](https://docs.ultralytics.com/models/yolo11/)
- [Ultralytics training/validation interface](https://docs.ultralytics.com/modes/val/)
- [Ultralytics export interface](https://docs.ultralytics.com/modes/export/)
- [ONNX Runtime execution providers](https://onnxruntime.ai/docs/execution-providers/)
- [ONNX Runtime CUDA compatibility](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)

YOLO11n is an established small transfer-learning baseline with inference/export support; recommending it is not a claim that it is the newest release. The original COCO checkpoint does not implement our required custom classes. Export/preprocessing/NMS details must match the selected model and pinned library version. ONNX execution depends on installed providers and operator support; confirm actual provider use and output agreement. Vendor timings are not promises for the RTX 2050 sharing resources with rendering. Training counts, epochs and speed targets in our handoff are proposed experiments, not official rules or established results.

### R7. WSL, storage and alternate simulator investigation

- [Microsoft WSL import commands](https://learn.microsoft.com/windows/wsl/reference)
- [Official Microsoft distribution manifest](https://raw.githubusercontent.com/microsoft/WSL/master/distributions/DistributionInfo.json)
- [Microsoft WSL GUI/vGPU guidance](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)
- [Webots stable releases](https://github.com/cyberbotics/webots/releases)
- [Webots R2025a Python guide](https://raw.githubusercontent.com/cyberbotics/webots/R2025a/docs/guide/using-python.md)
- [Webots R2025a autonomous Mavic patrol sample](https://raw.githubusercontent.com/cyberbotics/webots/R2025a/projects/robots/dji/mavic/controllers/mavic2pro_patrol/mavic2pro_patrol.py)

WSL import can locate a distro's Linux filesystem on D:. GPU interfaces being present is a prerequisite, not a measured rendering result. Webots was investigated as a native Windows/D: alternative with an existing Python drone example; user preference and ROS delivery alignment led to the WSL/Gazebo choice. Keep Webots as a contingency, not a second parallel installation. Avoid old versioned Python/Webots search results when current maintained source is available.

### R8. Dataset access audit

| Dataset/source | Verified | Unresolved/action |
|---|---|---|
| [Kaggle Gun Detection](https://www.kaggle.com/datasets/ugorjiir/gun-detection), [public metadata search](https://www.kaggle.com/api/v1/datasets/list?search=ugorjiir%2Fgun-detection) | Owner/ref and ~278 MB compressed metadata | Audit actual annotation format and class coverage; no image archive fetched |
| [Roboflow project](https://universe.roboflow.com/mine-dyzns/detection-miwbi) | Organizer-provided URL only | Web fetch failed; direct request returned 403. Exact classes, versions, export permission and license remain unverified; teammate must check authorized access |
| [Zenodo record](https://zenodo.org/records/21965497), [public record API](https://zenodo.org/api/records/21965497) | Coastal marine-litter metadata, archive names/sizes/checksums and label-format information | Inspect archive examples before conversion; split conflicts with brief; rendered-scene domain gap |

Only metadata has been fetched for these three sources. Details needed for the AI teammate are in `AI_HANDOFF.md`; no model training, Roboflow access or detector quality is claimed. Zenodo's CC-BY-4.0 attribution must accompany use. Preserve source manifests/licenses for all data and model assets. Never publish credentials in the handoff or repository.

## Ranked risks and mitigations

1. **Integration before model readiness:** ship deterministic mocks and fixed contracts first; do not use mocks as final detector evidence.
2. **Rendering/control setup:** smoke-test camera + physical flight early; source builds and autopilot rewrites are outside the initial critical path.
3. **Photograph-to-render domain shift:** test camera frames from the actual scene and fine-tune synthetic samples where needed.
4. **Medical urgency observability:** explicit source/cue and unknown handling; do not fabricate medical inference.
5. **Timing with two models:** measure complete trace; drop queued stale frames, profile resolution/provider tradeoffs without concealing misses.
6. **Safety and return:** independent physical/evaluation checks, conservative route inflation and shared wind-aware energy estimator.
7. **Outage semantics:** real disconnection, bounded durable replay, explicit overflow, duplicate-safe delivery IDs.
8. **Storage and packaging:** D-backed distro, no duplicate simulator toolchains, no local training cache explosion; source/assets first, validated deployment commands next.

## Evidence still required after research

Successful GPU-rendered simulation, stable flight under tested wind, image-to-3D localization error, learned-model metrics on held-out scenes, lossless replay inside the declared envelope, repeated full-mission success, p95 latency and final offline startup. These are implementation/validation tasks, not things that research alone can establish.
