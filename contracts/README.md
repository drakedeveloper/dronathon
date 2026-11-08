# Shared integration contract v1

These are **team-designed internal interfaces**, not exact formats supplied by the jury. The brief only specifies detector class/confidence/bounding-box output and communication limits. Adapt the station-facing serializer if an official protocol arrives. Schemas/examples are immediately usable integration fixtures, not implemented mission behavior.

## Ownership

Friend owns `skyforge_ai`: both detectors, PerceptionAgent, PlannerAgent and LangGraph. We own sensor/model/world interfaces, classical flight control, runtime scheduling, final safety validation, energy accounting, communication, evaluation and packaging. No model/network calls in the reflex loop. Only runtime commits the physical commands and delivery completion events. Planner proposes paths; runtime may reject them and request replan.

## Conventions

- Metres, seconds, radians, m/s, Wh; battery capacity/remaining are Wh, not an ambiguous percentage.
- World is local ENU: x east, y north, z up. Body: x forward, y left, z up. Optical camera: x right, y down, z forward. Quaternions are **xyzw**, normalized. The simulator adapter performs any convention changes exactly once.
- `t_sim_ns` is simulation time from mission start. Use monotonic **wall** time for performance measurement. Never subtract a simulation timestamp from a wall timestamp.
- Bounding boxes: `[x_min,y_min,x_max,y_max]`, continuous **original-image pixels**, upper bounds exclusive; `0 <= x_min < x_max <= width` and similarly for y. Source image origin top-left. No normalized coordinates or letterboxed input coordinates at this boundary.
- Detection class strings are fixed in `detections-v1.schema.json`; primary/secondary model class IDs must be remapped explicitly.
- Depth is float32 metres, aligned with RGB, optical-axis Z unless `depth_kind` explicitly says `radial_range`. Invalid depth is non-finite or nonpositive. Calibration contains `fx,fy,cx,cy`, image dimensions and a 4x4 `T_world_camera` for the **capture time**, including gimbal pose. The adapter must validate actual sensor encoding rather than assume it.
- No universal medical urgency label or exclusion radius is supplied in the brief. Make them configuration with `source` provenance; replace our scenario values if the jury specifies them.

## Runtime-to-AI snapshot

One complete, read-only Python dictionary (arrays may be native objects/shared-memory handles):

| Key | Shape/meaning |
|---|---|
| `v`, `mission_id`, `snapshot_seq` | Protocol version 1, stable mission ID, monotonically increasing snapshot counter |
| `t_sim_ns`, `capture_wall_ns`, `sensor_health` | Sim timestamp, host monotonic capture timestamp, freshness/validity flags |
| `position_enu_m`, `orientation_xyzw`, `velocity_enu_mps` | Length 3/4/3 arrays from configured navigation sensors |
| `battery_wh`, `energy_capacity_wh` | Finite nonnegative values from runtime energy accountant |
| `energy_model` | Versioned coefficients, configured reserve/margin, hover/delivery cost and wind-aware route estimator parameters |
| `base_enu_m`, `supply_count` | Base coordinate and available integer payload count |
| `wind_enu_mps`, `wind_uncertainty_mps` | Measured/configured wind plus stated uncertainty |
| `radio_connected`, `goal_revision`, `goal_update` | Link state and latest pending objective; revisions increase monotonically |
| `map_revision`, `map` | Known occupancy grid: `origin_enu_m`, `resolution_m`, `width`, `height`, `cells` (unknown=-1, free=0, blocked=100), permitted altitude envelope |
| `obstacles` | Observed static/dynamic obstacles: ID, bounds/shape, position, velocity estimate, last_seen and uncertainty; no hidden target positions |
| `detections` | Latest validated DetectionBatch; distinguish unavailable/failed inference from an empty successful batch |
| `camera` | Intrinsics, `T_world_camera`, synchronized depth or lookup handle, `depth_kind`, frame ID |
| `urgency_observations` | Only authorized target-associated scenario cues/ground-station metadata and their source; do not expose hidden scene labels |
| `events` | Bounded recent event list: `goal_update`, `delivery_completed`, `delivery_rejected`, radio transitions, runtime safety overrides |
| `previous_mission_state` | AI-maintained phase, tracks, coverage and served IDs, bounded or referenced by revision |

Sensor and world APIs will be adapted to this boundary; we do not give the AI a handle to the scene supervisor. Map construction must declare whether prior obstacle maps are permitted or sensed. Unknown occupancy does not silently mean safe.

## AI-to-runtime decision

See schema and `examples/decision.json`. Add required `v` and `map_revision` to the method outline in the handoff. Decision is an immutable proposal tagged with input snapshot/map/goal revisions. Reject stale or inconsistent proposals; the runtime owns the authoritative mission phase after safety overrides. Normal control may use a sufficiently fresh cached path only if the supervisor still validates it.

`request_delivery` is null or `{request_id,target_track_id}`. Repeating one request ID must not decrement supplies twice. Runtime returns `delivery_completed` only after the configured stable-hover, location, altitude, target confidence and safety conditions are met. A ground-station acknowledgement and a delivery request are not proof of successful delivery.

## Processes and timing

Simulator bridge/controller advances with physics and never waits for AI. Use a bounded latest-frame buffer and bounded latest-decision channel. Heavy inference/graph code lives in an independently scheduled worker; avoid sharing the Python GIL with the reflex loop. Use `multiprocessing`/shared memory where supported, or ROS image transport with bounded queues. Implement the simplest functioning path first; profile before adding zero-copy complexity. Explicitly detect worker failure and timestamp expiration.

Vision arrays and full path JSON are internal messages; the station's <1 KB limit does not require squeezing camera frames or full DroneState into one packet. On the station wire, use UTF-8 byte length with compact serialization and an internal maximum of **999 bytes** as a conservative interpretation of '<1 Ko'.

## Validation

`scripts/validate_contracts.py` validates the example schemas, bounding-box geometry, model source/class consistency, and finite numeric values. Run it before integration and include these fixtures with the AI handoff. Passing these checks validates the data boundary only, not detection quality, flight safety or timing.
