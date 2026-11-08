# Innovation decisions

The suggestions are a design backlog, not a claim that 25 features are finished.
Core mission reliability, latency and the AirSim migration take priority over
adding untested behaviours. Keep exactly two LangGraph agents; supervisors and
communication remain deterministic modules.

| Idea | Current implementation / limit |
|---|---|
| 1. Living tactical map | Live tracks, hazard circles, routes, lidar points; depth-checked observed-ground grid added. No full 3D occupancy map. |
| 2. Second-chance detection | Repeated-frame association exists; deliberate viewpoint changes pending. |
| 3. Energy-aware rescue | Wind feasibility, slow cruise/vertical/delivery/landing budget, dynamic reserve; one three-delivery safe-return run recorded. |
| 4. Radio shadow memory | Buffer/replay implemented; spatial connectivity learning pending. |
| 5. Future collision prediction | Lidar braking exists; moving-object tracking and TTC prediction pending. |
| 6. Explainable brain | Reason codes, candidate energy/urgency evidence and deterministic human-readable explanations. |
| 7. Smart delivery | Camera-confirmed tracks, stable hover and hazard checks; virtual delivery only. Physical pack release pending. |
| 8. Storm adaptation | Body drag/gust model, wind-aware energy and visibility-based speed cap; no verified storm/visibility adaptation yet. |
| 9. Self-healing | Stale-command hold, camera-stale hold, CRC/HMAC validation; launcher stops on failed simulator/controller. Automatic restart is not implemented. |
| 10. Uncertainty exploration | Directed distress-beacon search and sweep objectives; calibrated uncertainty/frontier scoring pending. |
| 11. Safety shield | Independent finite/bounds/segment/reserve validation added after planner, with safe outward recovery. Not a formal CBF proof. |
| 12. Ghost flights | Numerical energy/drop predictors exist; multi-route dynamic rollouts pending. |
| 13. Golden minute | Urgency is declared distress metadata; time-dependent medical updates pending. No severity inferred from clothing. |
| 14. Doubt engine | Conservative low-confidence hazard mapping; confidence calibration and explicit temporary-zone lifecycle pending. |
| 15. Safe corridor | Inflated 2D routes and independent segment checks; no certified 3D corridor. |
| 16. Bandwidth | Compact authenticated JSON, events before routine refresh; no CoAP/OSCORE or arbitrary priority reordering of contiguous events. |
| 17. Black box/replay | Structured traces/decisions/radio journal; interactive timeline pending. |
| 18. Command firewall | Authentication, monotonic revision, bounds and route shield. Explicit ground goals still respect reserve and hazards. |
| 19. Chaos monkey | Packet/state bit flips, replay and outage injectors; broader sensor delay/freeze campaigns pending. |
| 20. Deadline guardian | Separate reflex process and timing reports; input-size experiments rejected when casualty accuracy degraded. Deadline compliance still unproven. |
| 21. Camera footprint | Survey altitude and braking speed cap derived from FOV; observed-ground resolution check added. Not adaptive altitude optimisation. |
| 22. Persistent person IDs | Spatial multi-frame association, stable track IDs, served-target suppression. Re-identification beyond this scene needs validation. |
| 23. Delivery bubble | Hazard rejection and hover gate; alternate drop-site search pending. |
| 24. Search certificate | Actual depth-consistent ground observations exported; not semantic detection completeness. |
| 25. Scenario evolution | Seeded training scenes and independent evaluator; randomized unattended mission campaign pending. |

## Simulator distinction

Gazebo currently runs the integrated rescue AI/control/communication mission.
AirSim Coastline has native API/camera/physics flight checks and visible demo
scripts. `-Scenic` explicitly selects an external-physics spectator view; it is
not an autonomous flight. Native AirSim movement is demonstrated separately.
The full rescue mission has not yet migrated to AirSim. The proposed Army Base
Island listing could not be inspected (access denied); price, license, size and
engine compatibility are not verified. No such asset has been purchased or
downloaded. Original scene screenshots are not evidence that it is installed.
