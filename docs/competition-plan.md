# Turn the cahier des charges into a demonstrable result

## Immediately when it arrives

Save the original brief in `docs/`. Extract every scored requirement into a table with: weight, exact acceptance condition, owner, implementation, test evidence, and status. Establish the required drone/autopilot, ROS distribution, simulator/world, input data format, network availability, permitted pretrained models, permitted pre-existing code, payload limits, and final deliverables. The starter files must be disclosed or replaced if the rules restrict pre-event work.

Prioritize the rubric. The public rescue theme is a direction, not permission to invent requirements. If hardware is provided, record flight controller firmware, sensors, camera resolution/calibration, control interface, and how manual override works before integrating.

## Suggested technical separation

1. Perception: camera/video input -> timestamped detections with confidence, bounding boxes and evidence images. Do not label simple marker detections as survivors. A real person model must be checked on the actual aerial viewpoint, altitude, lighting and occlusion.
2. Planning: search area -> route -> target verification -> delivery decision. Keep coordinate frames, units and camera-to-ground assumptions explicit.
3. Control adapter: mission state -> organizer-approved autopilot API. Keep perception independent of ROS/MAVLink so switching transports does not require rewriting the vision pipeline.
4. Evidence: timestamped telemetry, detections, mission state, repeatable test input, and a short fallback demo recording.

The included sweep is only an obstacle-free geometric baseline. Determine track spacing from camera footprint and overlap once the camera and altitude are known. Delivery should require verified target location and the event's required release conditions; handle an unconfirmed target explicitly.

## Working sequence for an overnight event

- First 10%: parse rubric, verify organizer environment, run provided baseline and confirm end-to-end data flow.
- Next 40%: one complete scored mission with a simple reliable method. Keep measurable success/failure logs.
- Next 25%: address the largest rubric gap and test lost target, invalid input, low battery, lost link and timeouts where relevant.
- Final 25%: freeze dependencies, rehearse twice from a clean start, prepare results and a concise pitch, retain a recording in case presentation infrastructure fails.

For a team, split perception, mission/control, integration/testing, and pitch/evidence according to team size. Keep one shared configuration and one designated integration owner.

## Evidence to bring to judging

Report measured mission success across repeated trials, time to first correct target, false detections, localization error, delivery accuracy, and compute latency only where they apply to the brief. State sample count and failure cases. Prefer an honest repeatable result over an untested architecture diagram. Maintain a clear distinction between simulated results, recorded-video results and real flight validation.
