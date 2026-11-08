# SKYFORGE: instructions for the AI teammate

## Start here

We have approximately 12 hours from competition kickoff. You own **all AI**: both vision modules, PerceptionAgent, PlannerAgent, and deterministic LangGraph orchestration. We own the simulator/world, sensor adapter, physical flight controller, safety supervisor, communication, energy model, integration and presentation. Deliver working interfaces early, then improve models. Do not wait for a final model before sending runnable code.

Read `../dronathon.pdf` and `PROJECT_PLAN.md`. Written specification says the jury supplies the primary detector, but the organizer has supplied only the three dataset URLs and says implementation is free. Therefore provisionally build a primary detector too; if a jury model arrives, replace only that adapter. This discrepancy remains a clarification item, not a reason to stop.

Required agent names: **PerceptionAgent**, **PlannerAgent**. Required orchestrator: **LangGraph**, deterministic Python nodes, no LLM calls in the mission loop. Hostile units are exclusion zones only; the payload and mission are humanitarian.

## First deliverables and deadlines

All times are relative to the original 12-hour kickoff; they are checkpoints, not a reset of the event clock.

| Due | Send us |
|---|---|
| Within first hour | Importable `skyforge_ai` package, public method signatures below, deterministic mock outputs, `requirements-ai.txt`; begin dataset access checks immediately |
| By H2 | Graph with medical priority, battery feasibility and goal updates; first trained/inference baseline or a precise blocker; primary dataset audit |
| By H4 | Both detector adapters, initial synthetic-data secondary model, full graph that passes shared fixtures |
| By H6 | Integrated models/agents on our camera stream, no file-path assumptions or downloads at startup |
| By H8 | Frozen weights, chosen thresholds, validation report, inference timings and failure cases |
| H8-H12 | Fix integration failures and repeat demo trials; no model/framework changes without a demonstrated benefit |

These are targets. Alert us at once if any checkpoint slips. A random-output or ground-truth adapter may unblock development, but must be named `mock` and never counted as learned vision in the final results.

## Required package boundary

Use Python 3.12 on Ubuntu 24.04 for final integration. Keep modules simulator-independent: do not import Gazebo, Webots or ROS into core AI. Use relative package paths and an explicit `models_dir`. A Windows development environment is fine if the package also runs on Linux.

```text
skyforge_ai/
  __init__.py
  detector.py          # PrimaryDetector and SecondaryDetector
  perception.py        # PerceptionAgent, projection and observation fusion
  planner.py           # PlannerAgent, triage and routes
  graph.py             # MissionAI, compiled LangGraph
  models/              # best-primary.pt/.onnx, best-secondary.pt/.onnx
  configs/             # class mappings, thresholds and training config
  tests/
requirements-ai.txt
MODEL_CARD.md
```

Proposed API; agree any change with us before renaming it:

```python
class VisionSystem:
    def __init__(self, models_dir: str, device: str = "cpu"): ...
    def infer(self, image_bgr, frame_meta: dict) -> dict: ...

class MissionAI:
    def __init__(self, config: dict): ...  # compile the graph once
    def reset(self, mission_id: str) -> None: ...
    def step(self, snapshot: dict) -> dict: ...
```

`image_bgr`: contiguous uint8 HxWx3 BGR array. Never treat BGR as RGB silently. `frame_meta`: `frame_id`, `t_sim_ns`, `camera_id`, `image_size_wh`. `infer` returns a DetectionBatch matching `../contracts/detections-v1.schema.json` in **original camera pixels**, after reversing any resize/letterbox. Empty detection list is valid. Exceptions must be explicit; do not return fake successful empty detections on model failure.

`snapshot`: owned and supplied by our runtime. It includes pose/quaternion and velocity in local ENU; sensor timestamp/health; `battery_wh`, `energy_capacity_wh`, `energy_model`; base location; observed map/obstacles and map revision; wind estimate; radio state; pending goal revision; supply count; latest detection batch; camera intrinsics; synchronized depth and `T_world_camera`; and the previous mission state. Arrays are local objects/shared memory, not base64 JSON. Our interface adapter will supply a sampled depth lookup or frame handle without coupling your code to the simulator.

`step` returns a proposal: `snapshot_seq`, `goal_revision`, `phase`, `target_track_id` (nullable), `waypoints_enu_m`, `return_path_enu_m`, `request_delivery`, `decision_code`, and `decision_details`. See `../contracts/examples/decision.json`. It must not mutate physical pose, battery, wind, radio state or supply count. It must not send motor commands, network traffic, or perform blocking disk I/O. We validate and execute the proposal; final safety overrides remain outside the graph.

Maintain perception tracks and mission memory inside the AI instance/shared DroneState. Every proposal must explain its decision, including rejected casualties and energy feasibility. Output consistent numeric units; never use degrees where radians are expected.

## Vision: two modules, one format

**PrimaryDetector**: canonical classes `waste`, `mine`, `weapon`. Keep optional waste subtype metadata. **SecondaryDetector**: canonical classes `injured_person`, `hostile_unit`. Their combined output feeds PerceptionAgent. A single internally shared network is acceptable only if the two module interfaces and their metrics remain explicit and this interpretation is accepted by the jury.

Initial recommendation: two small pretrained YOLO11n detection models, fine-tuned separately. This is a practical baseline, not a mandatory architecture or a claim it is the newest model. Use one known-good version of Ultralytics; record its exact version before handing off. Do not switch among architectures during integration. Training belongs on your GPU/available machine; our RTX 2050 must also render the simulator and is not an unlimited training resource.

1. Audit dataset formats, class IDs, licenses and corrupt files before training.
2. Create `data-primary.yaml` with a fixed canonical map. Do not assume the mine/weapon datasets already use the same class numbers or even the same annotation format.
3. Produce a first transfer-learning checkpoint quickly. Example starting budget: 10-20 epochs, 640-pixel input, batch adapted to GPU memory. These are initial experiments; use validation to choose the checkpoint. If memory fails, reduce batch before image size; smaller images can erase distant targets.
4. For secondary vision, use **our simulator-generated dataset**, not only COCO person detection. Begin with 400-800 diverse labeled images for pipeline proof, expand toward 2,000-4,000 if time/rendering/storage allow. These counts are project targets, not PDF requirements.
5. Save negative/empty scenes, occlusions, different camera poses, scales, lighting, backgrounds and visibility. Avoid shortcuts such as one uniquely colored floor per class. Split whole scene/layout seeds first; keep neighboring frames and augmentations of one original in the same split.
6. Follow the requested 70/20/10 split where we create a new dataset; preserve any official held-out evaluation set. Document the linked Zenodo dataset's conflicting published split and do not silently overwrite it.
7. Send original weights plus an ONNX export and a small inference wrapper. Prefer batch=1 and a known input size. Document whether NMS is inside the export, output tensor layout, channel order, scaling and padding reversal. Test exported and original outputs on the same images.

The ordinary COCO model does not natively detect `mine`, `weapon`, `injured_person` or `hostile_unit`. Detecting a generic person is a useful baseline but does not prove the required classes. A hostile label is the assigned visible role in the synthetic scenario, never inferred from demographic appearance. If the role has no observable visual cue, report that limitation rather than guessing.

Do not infer medical severity from a bounding box or posture alone. Use jury-provided urgency metadata or an explicitly agreed observable scenario cue; keep `urgency_source` and an unknown state. If we choose synthetic urgency values because no rule is supplied, label this as our documented scenario assumption.

## Dataset links and specific traps

- https://www.kaggle.com/datasets/ugorjiir/gun-detection — metadata reports roughly 278 MB compressed. Check image/label layout, content license and access; obtain any login on your own account, never send API secrets in code.
- https://universe.roboflow.com/mine-dyzns/detection-miwbi — mine-related link from organizer. Exact classes/export permissions have not been verified; check in the browser immediately. If export is blocked, request an authorized export/version rather than spending hours on it.
- https://zenodo.org/records/21965497 — marine-litter data. The original `Data.rar` is 297,515,800 bytes; augmented archive is 906,775,797 bytes. Choose the original archive first to avoid unnecessary duplicate storage. Its labels are normalized **YOLO segmentation polygons**, not bounding-box rows. Convert each valid polygon to min/max bounds if training a detector, preserve class identity, and manually verify overlays. It has seven material categories; map all seven to `waste` if using the three-class primary detector. Keep a reversible source-class manifest.

Real photographs and rendered objects differ. Evaluate the primary model on our rendered camera too; fine-tune on additional labeled synthetic hazard examples if needed. Good held-out Kaggle results alone do not establish simulation performance. Do not use unlabeled images with visible required objects as negative examples; audit missing annotations when merging the three datasets.

## PerceptionAgent

Fuse both modules, preserve source and timestamps, reject malformed/stale/out-of-bounds boxes, apply confidence thresholds tuned on validation, and track repeated observations to avoid duplicate rescues. Keep uncertainty and `last_seen`; a missed frame is not evidence that an established hazard disappeared. Confirm casualty tracks across observations before delivery; tentative hazards should trigger conservative avoidance immediately.

Project detections using synchronized camera pose, intrinsics and depth. In optical coordinates, with **Z depth** (not radial range):

```text
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
P_world = T_world_camera @ [X, Y, Z, 1]
```

Use a robust valid-depth patch consistent with the object; do not blindly sample background at the box center. If depth is radial range, normalize the camera ray first. Reject invalid/occluded depth. Ground-plane ray intersection is a documented flat-ground fallback only. Camera optical axes are x right/y down/z forward; world axes x east/y north/z up. Verify known points with our calibration fixture before trusting target coordinates. Ground-truth label/position access is for data generation/evaluation only, not runtime detections.

## PlannerAgent

- Begin with bounded A* over a 2D occupancy grid at a verified safe flight altitude; include height clearance, inflated obstacles and dangerous-zone geometry. If that altitude cannot avoid scene obstacles, add altitude bands/3D planning; do not claim 2D coverage solves arbitrary 3D scenes.
- Prevent diagonal corner cutting and validate every smoothed segment against inflated occupancy. A blocked or failed search returns an explicit failure, never a straight-line route through an obstacle. Budget the search, cache by map/goal revision and update when the map or objective changes.
- Fixed-height coverage sweep is our first exploration pattern, clipped to the actual reachable safe region. Revisit missed strips rather than counting traversed ground distance as camera coverage.
- Triage first excludes rescued, unsafe, unlocalized, unreachable or energy-infeasible casualties. Rank feasible casualties by urgency first, then estimated safe travel time, then stable track ID. A possible scalar score is `urgency_rank + 0.49/(1+travel_time/t_ref)`, with integer urgency classes; proximity cannot overturn one urgency level. Jury scoring rules replace this proposed formula.
- A rescue is feasible only if energy covers **outbound + hover/delivery + return + uncertainty margin + reserve**. Use the shared calibrated energy model and a collision-free return path, not straight-line distance alone. Recompute feasibility after wind/map/goal changes.
- Latch RETOUR_BASE under its energy threshold; do not let a subsequent ordinary goal update resume rescue. No thrashing between equal-priority targets; stabilize tie-breaks while allowing a newly discovered higher-urgency feasible casualty to preempt.
- Delivery is a request containing a confirmed target ID; our runtime checks proximity, speed, supplies, fresh localization and safety before emitting `delivery_completed`. Mark a casualty served only after that event, not when you issue the request.

## LangGraph

Compile a finite per-cycle graph once: `START -> PerceptionAgent -> PlannerAgent -> END`. Helper functions inside these nodes are fine. Run `step` on fresh bounded state snapshots; do not put the entire mission into an unbounded graph loop. A graph iteration is one decision cycle, not one mission. No cloud/LLM calls, synchronous remote tracing, or model loading inside `step`. Do not grow an unbounded list reducer for mission logs; emit bounded event records to our logger.

Required mission states: INIT, EXPLORER, DETECTER, TRIAGE, NAVIGUER, LIVRER, RETOUR_BASE, POSE. Unknown/stale observations can trigger a hover/rescan without pretending a delivery succeeded. Respect low battery, radio autonomy and new goal revisions supplied by runtime. An old graph result cannot overwrite a newer goal or map revision.

## Acceptance tests before sending final AI

1. Critical casualty farther away outranks nearby mild casualty when both are feasible.
2. Infeasible critical casualty is skipped with a logged reason; safe return remains possible.
3. Repeated detections of one casualty do not cause repeat delivery.
4. Goal revision changes invalidate old proposals; low battery still forces return.
5. Mine/hostile exclusion geometry blocks a route; moving obstacle produces stop/replan rather than collision.
6. Empty, corrupted or stale detection batches cause explicit safe behavior.
7. Synthetic annotation identities and target ground truth are inaccessible to runtime AI.
8. ONNX and original model agree closely on held-out images; confidence thresholds and NMS settings are recorded.
9. Full graph has measured p50/p95/max duration under simulator load. The <=100 ms decision requirement includes PerceptionAgent/PlannerAgent work; separately report inference and capture-to-command latency. No promise of compliance from nominal FPS alone.

Report per-class precision/recall, AP50 and mAP50-95, confusion matrix, missed-casualty examples, false alarms, sample counts and grouped test split. Internal targets: injured-person recall >=0.90 on held-out simulated scenes and a first inference p95 budget <=35 ms **per combined frame pipeline if achievable**. These are targets to measure, not invented official thresholds. Show speed/recall tradeoffs at 416/512/640 only if needed; do not quote vendor GPU timings as our laptop timings.

Final handoff: code, exact dependencies, both weights and export files, class/threshold config, small sample input/output fixtures, dataset/source manifest and licenses, metrics, timing results, model limitations, and one command that runs inference offline. Retain the most recent integrated checkpoint as a fallback.
