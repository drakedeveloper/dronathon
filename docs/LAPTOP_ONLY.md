# Laptop-only delivery decision

User confirmed8 November: home RTX5060 machine will not be used. All remaining
work targets Ryzen7535HS,16GB RAM, RTX2050 4GB and AMD integrated graphics.

Gazebo uses AMD D3D12 because actual rendered tests succeeded there. Native
Windows AirSim uses RTX2050; its Coastline API/image and bounded velocity climb/
descent were tested. Do not run both renderers concurrently during latency
acceptance. No Unreal editor/source build or further multi-gigabyte environment
downloads are planned. The packaged Coastline is a visual backend, not yet a
complete rescue mission.

Storage target: C8GB+ free for Windows operation, D10GB+ for bounded project work.
On inspection C0.91GB / D10GB free. C WSL crash dumps6.22GB (9files), npm cache
1.09GB. Duplicate D AirSim ZIP0.86GiB and Ubuntu import image0.36GiB are disposable
after successful extraction/import. Automatic approval review rejected deletion;
the user was given commands. No cleanup was performed by the agent. Never retry
blocked deletions through another shell/tool.

Latest completed mission-eb5d81bc:3 virtual deliveries, geometric checker0hazard
entries and0static collision segments, emergency landed2.8m from base with~0.07Wh.
This is NOT a successful return. Planner energy assumed2m/s cruise despite0.9m/s
control cap, and omitted descent/ascent/settling time. The next revision budgets
0.65m/s progress,0.5m/s vertical progress, landing and delivery overhead. Keep the
15Wh battery unchanged; do not inflate capacity to mask a failed budget.

Drop benchmark:18 separate Gazebo rigid-body drops, heights1/2.2/4m and winds
0/1.5/3m/s. Uncorrected mean/max error0.0226/0.0883m; RK4-corrected mean/max
0.000034/0.000141m under the SAME drag assumptions. This is numerical consistency,
not empirical accuracy. Mission supply delivery remains virtual. Results:
artifacts/drop-benchmark/results.json.
