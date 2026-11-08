# Release demo and acceptance gates

Use PROJECT_LEDGER.md and validation/ for measured results. Never present a
spectator camera move, a training teleport or virtual event count as a rescue.

## Before the jury

1. Close training jobs and the extra Coastline preview. Run one renderer only.
2. Start the native scene with scripts/start_native_airsim.ps1; add -Packaged
   only after the packaged build passes launch/flight checks.
3. Start scripts.run_native_mission using the native GPU Python and the frozen
   candidate model folder. The launcher refuses a wrong/spectator simulator,
   calibrates the launch frame, and starts station, weather, reflex and agents.
4. Open http://127.0.0.1:8768. The two agents are deterministic LangGraph nodes.
   The independent reflex remains a separate process.
5. Show actual camera detections, tracks, urgency/energy explanation, radio
   buffering, safety holds and return. Delivery events are virtual hover aid;
   the independent evaluator must confirm casualty locations after landing.
6. Show per-class development metrics and the exact timing scope. Any p95 above
   the PDF deadline is a failed gate, even if the video looks smooth.

## Security/resilience demonstration

Use the station buttons during an active safe simulation: outage, packet bit
flip, replay and state bit flip. Watch counters and event replay. A corruption
counter alone is not proof of safe control; inspect reflex hold cycles and the
subsequent safe return. An outage with no buffered events is not replay proof.

Messages are compact JSON, protocol version/sequence, CRC and HMAC; each radio
packet is at most999 bytes. Receiver ACK cursor and sender event journal are
persisted. Corrupted complete journal records fail closed. This authenticates
integrity; it does not encrypt traffic or certify hardware bit-flip tolerance.

## Stable fallback

The existing ROS2 Jazzy/Gazebo mission is preserved by start-mission.ps1 -Gui.
It has recorded three-delivery returns and independent geometric evidence.
Native and Gazebo have different visual/model domains; use the matching models.
Do not silently use the fallback's results as native AirSim evidence.

## Ninety-second explanation

“SKYFORGE separates perception and planning from a bounded independent flight
reflex. Detectors produce observations, never simulator labels. The planner
prioritizes feasible medical aid using wind-aware return energy. A separate
safety shield can reject a route. Signed compact event messages survive radio
loss, and a post-flight evaluator checks actual delivery geometry. We report
what passed and what remains a prototype, including virtual payload delivery
and an uncalibrated but source-backed reference airframe.”

The real-image primary detector is a teammate integration boundary. It must
share the documented class/preprocessing contract and be evaluated separately
on real images and the final scene before replacing the frozen candidate.
