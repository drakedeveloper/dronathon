# The next actions

1. **Send your friend** `AI_HANDOFF.md`, `PROJECT_PLAN.md`, `RESEARCH.md`, `../contracts/` and `../dronathon.pdf`. All AI is theirs: the two detector modules, both agents and deterministic LangGraph. Request an importable mock/API first, not only final trained weights.
2. **We finish the runtime gate:** D-backed WSL, ROS2/Gazebo, physical hover/waypoint/landing and actual camera capture. Read `WSL_SETUP.md` for what is verified versus pending.
3. **Freeze the contract:** BGR images, original-image pixel boxes, local ENU metres, quaternion xyzw, simulation timestamps, independent wall-clock timings and revisioned decisions. Validate the supplied fixtures with `scripts/validate_contracts.py` in the Linux environment.
4. **Integrate one scored rescue:** image -> localization -> urgent feasible target -> safe route -> physical delivery -> return. Then add actual radio outage/replay and goal changes.
5. **Freeze by H8-H10**, leaving time for repeated scenarios, measured p95 timing, documentation and a live-demo rehearsal. These times are relative to the original 12-hour kickoff.

Message you can send with the handoff:

> You own all AI: primary waste/mine/weapon detector (unless a jury model arrives), secondary injured-person/hostile-unit detector trained on our synthetic simulator data, PerceptionAgent, PlannerAgent, and deterministic LangGraph. We handle Gazebo, sensors, physical flight/safety control, energy accounting, station communication and integration. Please implement the shared Python API/JSON fixtures immediately and send a runnable mock within the first hour, so we can integrate while you train. Then deliver models, agents, metrics and pinned dependencies against the same interface. No LLM calls in the mission loop. Read AI_HANDOFF.md for details and checkpoints.

The main open questions are medical-urgency input, delivery tolerance, whether jury modules/world will still arrive, and exact Docker/ROS2 deployment expectations. Do not stall independent work while awaiting answers. Do not claim annotation/ground-truth mocks as trained vision or a partial scene as a completed autonomous mission.
