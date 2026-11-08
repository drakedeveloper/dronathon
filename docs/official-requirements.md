# Official specification intake - 7 November 2026

Source: `../dronathon.pdf`, all three pages read and visually reviewed. This document supersedes assumptions in the earlier research notes.

## What must be demonstrated

A fully autonomous 3D simulated humanitarian reconnaissance/support drone. Explore a coastal area, detect hazards and marine litter, locate injured people, prioritize medical aid, avoid hostile units and obstacles, deliver simulated supplies, survive radio outages, and return safely. No weapons or hazardous payloads; hostile units are exclusion zones, never targets.

## Required architecture

- LangGraph with deterministic nodes, no LLM calls in the real-time loop.
- PerceptionAgent: fuse jury/team detectors, project 2D detections into 3D positions, filter false detections, record exclusion zones.
- PlannerAgent: medical urgency first, proximity second; infeasible rescue-and-return gets zero priority; avoidance and wind-aware routes; battery-triggered return.
- Classical reflex control <50 ms; deliberative decisions <=100 ms; end-to-end <=150 ms at p95. Instrument all three separately.
- Shared DroneState: pose, velocity, battery, radio, weather, threats, casualties, goal, waypoints, logs, mission phase.
- Communication module (not an agent): compact JSON <1 KB, version and sequence number, declared ring buffer capacity, replay/resynchronization after outage. Raspberry Pi deployment is bonus only.

## Responsibilities

Jury supplies: main waste/mine/weapon detector, three datasets with specified 70/20/10 train/validation/test division, scenario, weather, ground station. Team supplies: secondary injured-person/hostile-unit detector trained on simulator-generated data, orchestrator, two agents, obstacle handling and JSON communication.

The PDF lists main detector accuracy >90%, recall and per-class mAP, with mine/weapon recall prioritized. Confirm whether the supplied model must be retrained or simply integrated/evaluated; do not spend the event rebuilding the provided module without clarification.

## Acceptance and scoring

| Requirements | Evidence |
|---|---|
| F1-F2 autonomy, exploration, mapping | Coverage without manual intervention, wind compensation |
| F3-F4 hazards/litter | Per-class recall/mAP, persisted exclusion zones |
| F5 secondary vision | Injured-person recall, matching JSON schema |
| F6-F7 triage/delivery | Logged priority decisions, correct target delivery |
| F8 avoidance/replanning | Zero collisions and zero dangerous-zone entry |
| F9-F10 communication | Messages <1 KB; autonomous continuation; logs synchronized after recovery |
| F11 return | Dynamic threshold from distance, wind, reserve and margin, checked each cycle |
| F12 bonus board | Memory/latency/synchronization measurements |

Scoring: autonomy 20%; decision intelligence 20%; navigation 15%; communication/resilience 15%; adaptability 15%; overall efficiency 15%. Penalties: collision, dangerous-zone entry, wrong delivery, failure to return. Deliver source and 3D scene deployable in Docker/ROS2, technical documentation, unattended live demo, oral presentation; board demo optional.

State flow: INIT -> EXPLORER -> DETECTER -> TRIAGE -> NAVIGUER -> LIVRER -> TRIAGE if casualties remain, else RETOUR BASE -> POSE. Battery threshold forces return, lost link switches to autonomous operation, goal_update causes immediate rerouting.

## Installed versus missing

Installed: Python 3.13 (Windows), OpenCV, NumPy/SciPy, Matplotlib, pymavlink/MAVSDK; existing Ubuntu 24.04 WSL2; ArduPilot SITL with heartbeat verified. PDF reading/rendering libraries were added to inspect the brief. Docker CLI exists; engine operation was not verified.

Missing: ROS2, a 3D simulator/world, LangGraph, secondary detector training/inference pipeline, mission architecture, resilient communication, full integration and performance validation. ArduPilot SITL alone has no rendered scene/camera data. Earlier ArUco smoke test does not satisfy F5.

Recommended stack to investigate: ROS2 Jazzy with Gazebo Harmonic under Ubuntu 24.04 WSL2, Python 3.12 native to Ubuntu for ROS integration, deterministic LangGraph, OpenCV and a small trained detector. Windows Python 3.13 remains useful for tools, but should not be treated as a ROS interpreter. Confirm compatibility with jury assets before large installations. Store new workspace and datasets on D:; existing WSL system packages still occupy the existing virtual disk location.

## Linked datasets checked

- Kaggle `ugorjiir/gun-detection`: public API identifies Gun Detection, about 278 MB archive. Detection dataset, not a ready trained inference model.
- Roboflow `mine-dyzns/detection-miwbi`: web fetch failed; exact classes, export version, license and size remain unverified.
- Zenodo record 21965497: API identifies Tunisian coastal marine litter dataset, seven classes (Cardboard, Fabric, Glass, Metal, Other, Plastic, Wood), normalized YOLO polygon segmentation labels, CC-BY-4.0. Files: `Data.rar` 297,515,800 bytes; `Augmented data.rar` 906,775,797 bytes. Only metadata fetched, no image archives downloaded.
- Zenodo description states 80/15/5 split, while competition PDF says 70/20/10. Ask which split is authoritative. Preserve jury test data untouched; prevent related original/augmented images leaking across splits. Segmentation labels must not be read as YOLO bounding-box labels without explicit conversion.

## Questions for organizers (not sent)

1. Supply simulator world, ground-station protocol and primary model: exact formats, versions, start commands and expected integration points?
2. Are Gazebo/Webots/Python alternatives fully accepted, and is ROS2 mandatory for final delivery or one of the allowed deployment options?
3. Which split applies to the linked datasets, and is the primary detector already trained?
4. How are medical urgency, hostility labels, delivery tolerance and battery/energy model provided and evaluated?
5. How are latencies timed, and are camera acquisition and detector inference included in the p95 budget?
6. Confirm byte definition for 1 KB and outage/replay/acknowledgement semantics for the station protocol.

Prioritize a complete scored mission and reliable return before the optional Raspberry Pi bonus.
