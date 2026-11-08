# Physics, research, assumptions and experiments

This document separates published ideas, equations implemented by this project, and evidence still needed. The mission is humanitarian. It is a simulation prototype, not a certified aircraft or a clinically validated triage system. The equations live in `skyforge/physics.py`; Gazebo integrates the rigid body and rotor dynamics. Research PDFs are cached for local reading in `artifacts/papers/` with checksums; they are not redistributed in the code handoff.

## Simulator decision

[Shah et al., AirSim (2017)](https://arxiv.org/abs/1705.05065) describes Unreal-based visual/physical simulation with modular sensing/control. We inspected its paper and binary guidance. [Microsoft's project page](https://www.microsoft.com/en-us/research/project/aerial-informatics-robotics-platform/) says the original research project is archived. [AirSim binary guidance](https://microsoft.github.io/AirSim/use_precompiled/) warns about GPU demands in large environments. This does not make AirSim unusable: it remains an optional richer rendering backend when the RTX 5060 machine is available. Gazebo is selected for the current tested control/ROS path and custom scene work, not claimed to win every fidelity comparison.

An attractive render does not establish aerodynamic accuracy. For every backend we need explicit mass/inertia, rotor thrust/response, collision geometry, sensor calibration, wind and battery models. The adapter boundary uses local ENU metres and calibrated camera geometry; AirSim's NED interfaces would require an explicit tested axis/sign conversion.

## Rigid-body/rotor baseline

[Lee, Leok and McClamroch (2010)](https://arxiv.org/abs/1003.2005) motivates a geometric treatment of position, velocity and attitude on SE(3). We use Gazebo's existing multicopter velocity/attitude controller rather than claiming to reproduce every theorem or implement that paper verbatim. Our outer loop adds bounded position tracking and safety constraints.

Baseline X3 parameters used for calculations: total mass 1.52 kg (1.50 kg body plus rotor-link masses), four rotors, thrust constant `8.54858e-6 N/(rad/s)^2`, maximum rotor speed 800 rad/s, nominal rotor radius 0.10 m, gravity 9.80665 m/s². The mesh and controller constants come from the pinned Gazebo X3 example. Radius is a simplified effective-disk assumption; verify mesh/propeller dimensions before using it as an experimentally identified aerodynamic radius.

Implemented checks:

```text
T_total = N * k_T * omega²
omega_hover = sqrt(m*g/(N*k_T))
maximum level-thrust margin = T_max/(m*g) - 1
tilted vertical margin = T_max*cos(tilt)/(m*g) - 1
```

These expose overloading or unrealistic motor limits before the mission. A decorative guard/pod mesh does not automatically alter the force model. The present medical-pod visual is a concept skin inside the declared baseline mass budget, not evidence of a lower-CG or efficiency improvement. Any changed airframe variant must update mass, inertia, drag area and collision geometry, then rerun the same tests. Dropped payload mass is not yet removed from the baseline vehicle in the virtual-delivery integration gate.

## Wind and drag

[Faessler, Franchi and Scaramuzza (2018)](https://arxiv.org/abs/1712.02402) studies rotor-drag-aware tracking and coefficient identification. Its model explicitly assumes no wind; applying a relative-air-velocity wind term here is our model extension, not an experimental result established by that paper.

Our C++ `WindDrag.cc` computes world-frame relative air velocity and quadratic **body** drag each physics step:

```text
v_air = v_ground - wind
F_body = -0.5 * rho * CdA * |v_air| * v_air
```

It applies the force through Gazebo and publishes the exact configured wind for the declared simulated wind-sensor channel. Current defaults `rho=1.225 kg/m³`, `CdA=0.045 m²` are engineering assumptions to identify, not wind-tunnel measurements. Wind changes smoothly with deterministic gusts and a change of prevailing direction. This is not CFD, spatial turbulence, detailed rotor wake, ground effect or vortex-ring-state modeling. The existing motor plugin also has its own drag terms; do not fit the combined response while pretending it is body drag alone.

Experiment: fixed-position hover in calm/constant/gusting wind, compare P-only versus PI outer position control, measure RMS/max horizontal error and recovery time over equal time windows and seeds. Inspect tilt and saturation. If compensation cannot hold within the tested envelope, reduce flight speed/wind envelope or return safely; do not hide failures by slowing the simulation clock.

## Energy and safe return

[Zeng, Xu and Zhang (2019)](https://arxiv.org/abs/1804.02238), equation (6), motivates the profile/induced/parasitic horizontal propulsion model. We inspected the equation and parameter definitions in the paper, including the fact that induced power decreases with forward speed over part of the range. Our baseline coefficients are not its aircraft's measurements.

`Vehicle.power_w` implements those component shapes, adds declared electronics consumption and positive climb work, and grants no regenerative descent credit. Hover induced velocity follows ideal momentum theory using the assumed combined disk area and a declared efficiency. Battery integrates **simulation** time in Wh; pausing does not consume flight energy. It is not a voltage/sag/temperature/aging model.

Route estimates account for headwind/crosswind feasibility and an airspeed limit, rather than dividing by a clipped negative ground speed. Nominal wind plus eight perturbation directions form a sampled uncertainty envelope. This is not a formal worst-case bound over every 3D/time-varying wind field. The route-energy calculation includes safe ascent/return geometry, delivery dwell, reserve and model margin. Energy-infeasible casualties score zero. A temporary blocked route causes hold/replan, not an infinite threshold that automatically ends an otherwise healthy mission.

Experiment: compare constant-reserve and dynamic-reserve policies on the same scene/wind/targets; report delivered urgent cases, return success, remaining Wh and prediction error. Calibrate power parameters or explicitly label them as scenario constants. Never claim a real battery endurance improvement from this synthetic model alone.

## Trajectories, braking and uncertainty

[Burke, Chapman and Shames (2020)](https://arxiv.org/abs/2008.00595) studies scalable minimum-snap trajectories. [Zhou et al. (2019)](https://arxiv.org/abs/1907.01531) demonstrates kinodynamic search with trajectory optimization. These motivate smoothness and dynamic feasibility; this hackathon baseline uses bounded A* segments, a quintic rest-to-rest helper, speed/acceleration/jerk limiting and segment collision checks. It is not a reimplementation or performance match to either full system. Unchecked splines can cut obstacle corners, so every shortcut is checked.

Local stopping margin:

```text
d_stop = speed * response_latency + speed²/(2*a_brake) + k_sigma * position_sigma
```

Add the physical footprint and obstacle uncertainty separately; avoid inflating already-surface lidar points as if they were obstacle centers. Dynamic obstacle closure speed and actual measured deceleration must be included in the final envelope. The current scanner is horizontal and does not prove arbitrary 3D obstacle avoidance. Tall obstacles are represented in the declared map; unknown overhangs need extra vertical sensing.

Experiment: braking from several initial speeds toward a stationary barrier, then a moving barrier; compare predicted stopping distance with observed clearance and identify worst deviation. Validate starts near boundaries, targets inside exclusion zones, blocked base routes, diagonal grid corners and route smoothing. No local avoidance guarantee is borrowed from a paper whose assumptions we do not satisfy.

## Payload release calculation

[Rodriguez et al., autonomous ballistic airdrop](https://link.springer.com/article/10.1007/s10514-020-09902-3) provides a primary example of wind-aware delivery planning. Our implementation is an independent point-mass RK4 predictor with gravity, constant horizontal wind and quadratic drag, including initial horizontal velocity. It interpolates the ground crossing rather than rounding to a timestep.

```text
dp/dt = v
dv/dt = [0,0,-g] - rho*CdA/(2*m) * |v-wind| * (v-wind)
release_xy = target_xy - predicted_landing_offset_xy
```

No rotor downwash, parachute, bouncing or uncertain vertical wind is modeled. Default mass/area are explicit function arguments. Unit tests verify symmetry, no-wind horizontal drift, finite horizons and timestep restrictions. Physical Gazebo release must be compared to this predictor before using a correction as claimed delivery accuracy. A virtual-hover completion is labeled as such in current logs; it is not a measured ballistic landing.

Experiment: paired uncorrected/corrected drops at multiple heights/winds; independently measure landing error and ground-contact time, with mean/p95/max and sample counts. Use conservative release height near people and require a verified stable hover; exclude any dangerous payload.

## Toroidal propellers and airframe ideas

[MIT Lincoln Laboratory's toroidal-propeller work](https://www.ll.mit.edu/partner-us/available-technologies/toroidal-propeller-0) reports quieter prototypes and comparable thrust at similar power in its tests. It does not establish a silent aircraft or universal efficiency gain. Our current simulator has no aeroacoustic solver or acoustic measurement model; changing a rotor's appearance cannot demonstrate noise reduction.

Candidate airframe experiments: low-CG medical pod, protective perimeter/rotor guards, camera clearance, compact versus longer arm spacing, and a toroidal-inspired visual design. Each has a tradeoff: extra mass, drag, inertia, disk clearance, wake interference or collision footprint. Retain rotor guards as collision geometry if claiming protection; acknowledge that physical contact may still trigger the competition collision penalty. Compare variants with the same mission/energy/controller and report only measured results. Acoustic claims remain a future validation item unless genuine data/modeling is supplied.

## Security and numerical edge cases

Security complements physics: impossible sensor values, stale data or corrupted commands must not become thrust. Unit tests cover invalid/NaN/Inf vectors, infeasible winds, nonpositive parameters, quaternion normalization, energy exhaustion, packet-size bounds, single-bit packet corruption, forged MACs, event gaps and replay. CRC detects accidental corruption; HMAC authenticates integrity. The current loopback link is not encrypted and does not claim confidentiality against a compromised host. Keys stay out of the repository.

We simulate an internal command-state bit flip after its checksum is sealed and check it before use. This demonstrates detection within our model, not radiation hardness, ECC memory or protection from arbitrary hardware failures. Add slow sensor plausibility/monotonicity checks and a bounded safe response; acknowledge perception errors can still be plausible and authenticated.

## What is measured so far

The physical smoke flight climbed, translated and descended with rendered sensor output. Unit tests cover the implemented equations. Bootstrap forest/HOG vision is trained on actual rendered RGB/annotation pairs and has development validation metrics; its photographic-domain performance and fresh final test remain outstanding. The first mission made one virtual delivery and revealed a return-planning issue. Those findings are useful debugging evidence, not a successful final competition run.

Required final evidence: repeated autonomous missions, explicit collision/zone/delivery checks, wind/tracking and energy ablations, physical-drop comparison if enabled, radio outage/replay/fault scenarios, fresh held-out vision metrics, and full measured timing under the final rendering/AI load. We will not call the system perfect or borrow a paper's numerical results as our own.
