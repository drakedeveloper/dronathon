# Runtime check assets

`multicopter-upstream.sdf` was downloaded from the official Gazebo `gz-sim8` example:
https://raw.githubusercontent.com/gazebosim/gz-sim/gz-sim8/examples/worlds/multicopter_velocity_control.sdf

The Gazebo project is Apache-2.0: https://github.com/gazebosim/gz-sim/blob/gz-sim8/COPYING . Retain upstream attribution/license when redistributing assets. This example references Gazebo Fuel aircraft assets that may be fetched on first run; their asset licenses must also be retained before final packaging.

`scripts/smoke_gazebo.py` generates a one-UAV derivative and adds a fixed test camera. It checks rendering, physical climb/translation/descent and ROS message exchange. It is not the competition scene, an autonomous rescue mission, an onboard-camera calibration test or proof of the final real-time budget.
