# Third-party components and assets

- OpenRobotics X3 UAV, authors Carlos Aguero and Cole Biesemeyer, Fuel model
  version4, Creative Commons Attribution4.0 International. Original model and
  relevant meshes bundled under `sim/models/x3`; unrelated meshes excluded.
  Model mesh URIs adapted to local assets for reproducible startup.
  Source: https://app.gazebosim.org/OpenRobotics/fuel/models/X3%20UAV
  License: https://creativecommons.org/licenses/by/4.0/
- Poly Haven rock_face_01, concrete_road_barrier_02 and coast_sand_02: CC0.
  Source/download URLs and checksums: `sim/assets/manifest.json`.
  License: https://polyhaven.com/license . OBJ conversion adapts axes and UVs.
- Gazebo multicopter example under `sim/smoke`: upstream Gazebo gz-sim,
  Apache2.0. Source URL is recorded in research/setup documentation.
  https://github.com/gazebosim/gz-sim
- YOLO11/Ultralytics training tooling and pretrained origin: Ultralytics,
  AGPL3.0 or its commercial license. Fine-tuned weights are included for the
  hackathon. Do not assume these weights remove upstream license obligations.
  https://github.com/ultralytics/ultralytics
  https://www.ultralytics.com/license
- ROS2, Gazebo, LangGraph, ONNX Runtime, OpenCV and other dependencies retain
  their respective upstream licenses. They are installed separately.
- Microsoft AirSim binaries are downloaded separately, not bundled in git.
  Packaged environment assets have separate terms from AirSim source code.
  https://github.com/microsoft/AirSim/releases/tag/v1.8.1-windows

Project-specific source has no new general redistribution license declared
yet. This private repository is for team collaboration and competition review.
