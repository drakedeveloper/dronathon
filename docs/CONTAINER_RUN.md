# ROS2/Gazebo container recipe

The Dockerfile targets Ubuntu24.04, ROS2 Jazzy and Gazebo Harmonic using official
ROS/Gazebo package repositories. It preserves the tested Gazebo implementation.
The native Windows Unreal simulator is a separate packaged application.

The container image has NOT been built or acceptance-tested on this laptop:
Docker's data disk was removed at the user's request to recover space. Do not
claim a successful container deployment from the existence of this recipe.
The same ROS2/Gazebo stack was installed and run in the D-backed WSL distro.

On a Linux machine with Docker and adequate free space:

```bash
docker build -t skyforge:local .
docker run --rm --network host --shm-size=1g skyforge:local
```

The dashboard binds loopback port8766. Host networking here is for Linux only;
do not expose the unauthenticated simulator or dashboard on a public interface.
Software rendering is selected for a portable headless starting point and has
not met the competition latency budget. Configure a tested GPU path for final
performance measurements. Docker Desktop host networking requires its separate
supported configuration; the command is not promised to work unchanged there.

For the already-provisioned laptop, the tested fallback launcher is:

```powershell
.\start-mission.ps1 -Gui
```

The native AirSim release uses scripts/start_native_airsim.ps1 and
scripts.run_native_mission. See NATIVE_AIRSIM.md and RELEASE_DEMO.md.
